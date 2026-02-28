# lAIfe - Copilot Instructions

## Project overview

ShelfMind is a fully local-first household object registry and multimodal retrieval system. It enables structured spatial modeling and hybrid (text + metadata + vision) search.
Python 3.14, managed with **uv**.

## Running & tooling

```bash
uv run pytest                # run tests
uv run ruff check .          # lint (ruff, ALL rules enabled - see ruff.toml)
uv run pyright               # type-check (src/ and tests/ only)
uv run uvicorn shelf_mind.webapp.app:app --reload
```

Credentials live at `~/cred/shelf-mind/.env` (loaded by `load_env()` in `src/shelf_mind/params/load_env.py`).

## Style rules

- Never use em dashes (`--` or `---` or Unicode `—`). Use a hyphen `-` or rewrite the sentence.

## Testing & scratch space

- Tests live in `tests/` (mirrors `src/shelf_mind/` structure).
- `scratch_space/` holds numbered exploratory notebooks and scripts (e.g., `12_action_structure/`, `17_configurable_vectorstore/`). These are not part of the package; ruff ignores `ERA001`/`F401`/`T20` there.

## Documentation

- Docs live in `docs/` (Markdown files), handled with `mkdocs` (see `mkdocs.yml`).
- Use `docs/specs/` for specifications (e.g., `technical_architecture_specification.md`, `functional_specification.md`).
- Keep updated a `docs/features/` directory with feature descriptions, with numbered files (e.g., `01_thing_registration.md`, `02_location_management.md`).

## Linting notes

- `ruff.toml` targets Python 3.14 with `select = ["ALL"]`. Key ignores: `D203`, `D213` (docstring style), `FIX002`/`TD002`/`TD003` (TODO formatting).
- Tests additionally allow `S101` (assert), `SLF001` (private access), `PLR2004` (magic values).

## End-of-task verification

After every code change, run the full verification suite before considering the task done:

```bash
uv run pytest && uv run ruff check . && uv run pyright
```
