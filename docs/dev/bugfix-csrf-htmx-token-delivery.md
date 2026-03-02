# Bugfix: CSRF Token Delivery and Inline-Script CSP Violation

**Date:** 2026-03-02  
**Status:** Resolved  
**Affects:** All POST HTMX requests + tab toggle buttons in browser UI

---

## Symptoms (from ui-test report)

| #   | Location                         | Symptom                                         |
| --- | -------------------------------- | ----------------------------------------------- |
| 1   | `GET /pages/things`              | `POST /pages/things/list` -> 403 Forbidden      |
| 2   | `/pages/things` Browse tab       | Clicking Browse - no op                         |
| 3   | `/pages/locations` Add form      | `POST /pages/locations/create` -> 403 Forbidden |
| 4   | `/pages/search` Image Search tab | Clicking Image Search - no op                   |
| 5   | `/pages/search` Text search      | `POST /pages/search/results` -> 403 Forbidden   |

---

## Root Causes

There are **two independent but compounding bugs**.

### Bug A - CSRF token never sent (causes 403s: #1, #3, #5)

`CSRFMiddleware` in `src/shelf_mind/webapp/core/middleware.py` enforces that for every
unsafe HTTP method (POST/PUT/PATCH/DELETE), when a `session` cookie is present, the
`X-CSRF-Token` request header must equal the `csrf_token` cookie value.

`base.html` attempted to supply the header via:

```html
<body hx-headers='{"X-CSRF-Token": "{{ csrf_token | default("") }}"}'></body>
```

No route handler ever injects `csrf_token` into the template context. Jinja renders it
as an empty string. Every POST carries `X-CSRF-Token: ""` while the cookie holds a real
token - the middleware comparison fails - 403.

A first repair attempt added an inline `htmx:configRequest` listener. The logic was
correct (read cookie, inject header) but was itself silently blocked by Bug B.

### Bug B - Strict CSP blocks all inline scripts (causes no-ops: #2, #4)

`SecurityHeadersMiddleware` sends this header on all app pages:

```
Content-Security-Policy: ...; script-src 'self'; ...
```

`script-src 'self'` with **no** `'unsafe-inline'` means the browser silently drops
every `<script>...</script>` block on the page. This is explicitly asserted in
`tests/webapp/test_security.py`:

```python
assert "script-src 'self' 'unsafe-inline'" not in csp
```

Affected inline scripts before the fix:

| File                                  | Content                                           | Effect                                 |
| ------------------------------------- | ------------------------------------------------- | -------------------------------------- |
| `templates/pages/things.html`         | `showThingsTab()`                                 | onclick -> no op (Bug #2)              |
| `templates/pages/search.html`         | `showSearchTab()`, `showVisionTab()`, camera code | onclick -> no op (Bug #4)              |
| `templates/base.html` (first-attempt) | `htmx:configRequest` listener                     | CSRF header not injected, 403 persists |

---

## Fix

Move all inline JavaScript to `static/js/app.js`, a static asset served under
`/static/js/` which is permitted by `script-src 'self'`. No CSP change is needed.

### `static/js/app.js` (new file)

Contains:

1. `htmx:configRequest` listener - reads `csrf_token` cookie, injects `X-CSRF-Token`
   header on every HTMX request.
2. `showThingsTab(name)` - tab toggle for Things page.
3. `showSearchTab(name)`, `showVisionTab(name)` - tab toggles for Search page.
4. `previewVisionFile(input)` - image preview for file upload tab.
5. `startCamera()`, `stopCamera()`, `captureAndSearch()` - camera capture and search
   (manual `fetch()` also reads `csrf_token` cookie for the non-HTMX POST).

### `templates/base.html`

- Remove old `hx-headers` attribute from `<body>`.
- Remove inline `htmx:configRequest` script.
- Add `<script src="/static/js/app.js"></script>` after `htmx.min.js`.

### `templates/pages/things.html`

- Remove the `{% block scripts_extra %}` override containing `showThingsTab`.

### `templates/pages/search.html`

- Remove the `{% block scripts_extra %}` override containing all search/camera JS.

---

## Verification

```
uv run pytest && uv run ruff check . && uv run pyright  # 178 passed, 0 errors
```

Manual browser checks:

1. `GET /pages/things` -> `POST /pages/things/list` returns 200, list populates.
2. Click Browse -> pane toggles and things list is visible.
3. `POST /pages/locations/create` returns non-403, tree refreshes.
4. Click Image Search -> vision pane toggles correctly.
5. Text search query -> `POST /pages/search/results` returns 200 with results.
