# Feature 03 - Search (Text and Vision)

## Purpose

Find registered Things using natural-language text queries or by uploading/capturing an image. Both modes use vector similarity search in Qdrant, followed by a re-ranking layer.

## UI Pages

### `/pages/search` - Text Search tab

| HTMX Endpoint | Method | Description |
|---------------|--------|-------------|
| `/pages/search/results` | POST form | Execute text query; returns `partials/search_results.html` |

**Form fields**:

| Field | Name attr | Type | Default |
|-------|-----------|------|---------|
| Query | `q` | text | required |
| Category | `category` | text | optional |
| Material | `material` | text | optional |
| Tags | `tags` | text (comma-sep) | optional |
| Location prefix | `location_filter` | text | optional |
| Max results | `limit` | number | 10 |

### `/pages/search` - Image Search tab

Two sub-modes are available at `/pages/search` (vision tab):

#### File Upload

Uses standard HTML `<form enctype="multipart/form-data">` with HTMX:

```html
<form hx-post="/pages/search/vision"
      hx-encoding="multipart/form-data"
      hx-target="#vision-results">
  <input type="file" name="image" accept="image/*">
  <input type="number" name="limit" value="10" min="1" max="100">
</form>
```

#### Camera Capture

Uses `MediaDevices.getUserMedia({ video: { facingMode: 'environment' } })` to access the device camera. Captured frame is extracted via `<canvas>` and sent with `fetch()` as `multipart/form-data` to `/pages/search/vision`.

| HTMX Endpoint | Method | Description |
|---------------|--------|-------------|
| `/pages/search/vision` | POST multipart | Run image search; returns `partials/search_results.html` |

## Search Pipeline

### Text

```
query → SentenceTransformerEmbedder.embed()
     → QdrantVectorRepository.search_text(vector, filters)
     → SearchRanker.rank(results, query_tags, location_path)
     → list[SearchResult]
```

### Vision

```
image_bytes → VisionStrategy.preprocess()
           → VisionStrategy.embed()          # image_vector[512 or 768]
           → QdrantVectorRepository.search_image(vector)
           → SearchRanker.rank(results)
           → list[SearchResult]
```

> **Note**: In Phase 1 the `VisionStrategy` is `NoOpVisionStrategy`, which returns a zero vector and produces no ranked results. Replace it with a real CLIP/ViT strategy to enable vision search. See `src/shelf_mind/infrastructure/vision/vision_strategy.py`.

## Ranking Formula

$$
\text{score} = \alpha \cdot \text{vector\_similarity} + \beta \cdot \text{metadata\_overlap} + \gamma \cdot \text{location\_bonus}
$$

Default weights (`ShelfMindConfig`): $\alpha=0.7$, $\beta=0.2$, $\gamma=0.1$.

## SearchResult Schema

```python
class SearchResult:
    thing_id: uuid.UUID
    name: str
    description: str
    category: str
    tags: list[str]
    location_path: str | None
    score: float
```

## Template Files

| File | Role |
|------|------|
| `templates/pages/search.html` | Main page with Text/Vision tabs + camera JS |
| `templates/partials/search_results.html` | Result cards (shared by both modes) |

## Camera JS Architecture

`search.html` contains self-contained inline JS:

| Function | Purpose |
|----------|---------|
| `showSearchTab(name)` | Toggle Text / Vision tabs |
| `showVisionTab(name)` | Toggle File / Camera sub-tabs |
| `previewVisionFile(input)` | Show thumbnail of selected file |
| `startCamera()` | `getUserMedia` → assign to `<video>` |
| `stopCamera()` | Stop all tracks, clear `srcObject` |
| `captureAndSearch()` | Canvas snapshot → Blob → `fetch()` POST → update `#vision-results` |

HTMX is not used for the camera path because `htmx` does not natively support `multipart/form-data` from a `Blob`. The `fetch()` call manually populates `#vision-results` and calls `htmx.process(target)` to activate any HTMX attributes in the response.

## Pitfalls

- **Vision search is no-op in Phase 1**: `NoOpVisionStrategy` generates a zero vector so results will always be empty. Swap in a CLIP strategy to enable real image search.
- **Camera permissions**: The browser will prompt for camera permission. On mobile, `facingMode: 'environment'` prefers the rear camera. HTTPS is required in production for `getUserMedia`.
- **CSRF**: The camera `fetch()` reads the CSRF token from the cookie. Ensure `SameSite` cookie settings allow this.

## Related Links

- [Thing Registration](01_thing_registration.md)
- [API reference: Search](/reference/shelf_mind/application/services/search_service/)
- [User guide: Search](/user-guide/search/)
