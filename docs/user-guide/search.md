# Search

ShelfMind provides two search engines - **text search** and **image search** - both using vector similarity in Qdrant.

## Web UI

Navigate to **Search** in the top navbar. The page has two tabs.

### Text Search tab

1. Enter a **Search Query** (required).
2. Optionally fill in:
   - **Category Filter** - exact category match (e.g. `tools`)
   - **Material Filter** - keyword match (e.g. `metal`)
   - **Tags Filter** - comma-separated tags that must all be present (e.g. `red, sharp`)
   - **Location Filter** - path prefix (e.g. `/Home/Garage`)
   - **Max Results** - 1-100 (default 10)
3. Click **Search**.

Results appear on the right with a relevance score and tags.

### Image Search tab

You can search by image in two ways:

**Upload file**: Click "Upload File", select an image from your device, set the max results, and click **Search by Image**.

**Camera capture**:

1. Switch to the "Camera" sub-tab.
2. Click **Start Camera** - the browser will ask for permission.
3. Point the camera at the object.
4. Click **Capture & Search** - a snapshot is taken and sent to the server.
5. Click **Stop** when done.

> Image search requires the vision strategy to be configured (see [developer notes](#image-search-developer-notes) below).

## Image Search Developer Notes

The vision search pipeline is scaffolded in Phase 1 with a `NoOpVisionStrategy` that returns empty results. To enable real results you need to:

1. Implement a `VisionStrategy` subclass (e.g. CLIP or ResNet-based).
2. Register it in `Container.initialize()`.
3. Index image vectors for existing things via `ThingService`.

See [Feature 03 - Search](../features/03_search.md) for the full pipeline description.

## Text Search

Text search embeds your query with `all-MiniLM-L6-v2` (384 dimensions), searches the vector store, and then applies a re-ranking formula that combines vector similarity with metadata overlap and location proximity.

### Endpoint

```
POST /api/v1/search/text
```

### Basic query

```bash
curl -X POST http://localhost:8000/api/v1/search/text \
  -H "Content-Type: application/json" \
  -d '{"q": "spatula"}'
```

Response:

```json
{
  "results": [
    {
      "thing_id": "b2c3d4e5-...",
      "name": "Red spatula",
      "description": "Silicone spatula for cooking",
      "category": "kitchenware",
      "tags": ["red", "spatula", "silicone", "cooking"],
      "location_path": "/Home/Kitchen/Utensil Drawer",
      "score": 0.85
    }
  ],
  "total": 1,
  "query": "spatula"
}
```

### Filter by location

Restrict results to a specific location subtree using `location_filter` (path prefix match):

```bash
curl -X POST http://localhost:8000/api/v1/search/text \
  -H "Content-Type: application/json" \
  -d '{"q": "charger cable", "location_filter": "/Home/Office"}'
```

This returns only things whose `location_path` starts with `/Home/Office`.

### Limit results

```bash
curl -X POST http://localhost:8000/api/v1/search/text \
  -H "Content-Type: application/json" \
  -d '{"q": "kitchen tools", "limit": 5}'
```

Default limit is 10; range is 1 to 100.

### Request fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `q` | string | yes | - | Search query (min 1 char) |
| `location_filter` | string or null | no | null | Location path prefix |
| `limit` | integer | no | 10 | Max results (1-100) |

### How ranking works

Each result receives a combined score:

$$
\text{score} = \alpha \cdot \text{vector_similarity} + \beta \cdot \text{metadata_overlap} + \gamma \cdot \text{location_bonus}
$$

Default weights: $\alpha = 0.7$, $\beta = 0.2$, $\gamma = 0.1$.

- **Vector similarity**: Cosine similarity from Qdrant between the query embedding and the thing's text embedding.
- **Metadata overlap**: Jaccard similarity between query tokens and the thing's metadata tags.
- **Location bonus**: 1.0 if the thing's location path starts with the `location_filter`, 0.0 otherwise.

### Search tips

- **Semantic matching**: The embedding model understands synonyms. Searching "cup" will also match "mug" with reasonable similarity.
- **Use descriptions**: Things with richer descriptions produce better embeddings.
- **Location filters**: Narrow results when you know the general area ("somewhere in the kitchen").

## Image Search (Phase 2)

Image search lets you find things by uploading a photo. The image is processed by a vision strategy, embedded, and compared against stored image vectors.

### Endpoint

```
POST /api/v1/search/image
```

### Usage

```bash
curl -X POST http://localhost:8000/api/v1/search/image \
  -F "image=@photo.jpg" \
  -F "limit=5"
```

### Current status

Image search is scaffolded with a `NoOpVisionStrategy` that returns empty results. The full pipeline is:

1. **Preprocess**: Resize and normalize the image.
2. **Embed**: Generate a 512-dim image vector via a vision model.
3. **Search**: Query Qdrant's `image_vector` named vector.
4. **Rank**: Sort by vector similarity score.

!!! note
    To enable real image search, implement a `VisionStrategy` subclass (e.g. CLIP-based) and register it in the DI container. See the [Developer Guide](../dev/infrastructure.md) for details.

### Validation

- The uploaded file must have a content type starting with `image/`.
- Empty files are rejected with `400 Bad Request`.

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Invalid image file or empty upload |
| 503 | Search service unavailable (e.g. Qdrant down) |
