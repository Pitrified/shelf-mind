# Things

Things are the household objects you register in ShelfMind.
When you create a Thing, the system automatically enriches it with structured metadata (category, material, room hint, tags) and indexes it in the vector store for search.

## Concepts

- **Automatic enrichment**: A rule-based enricher analyzes the name and description to infer category, material, room hint, and tags. No LLM required.
- **Vector indexing**: A text embedding (384-dim, `all-MiniLM-L6-v2`) is generated and stored in Qdrant for semantic search.
- **Placement**: A Thing can be placed at a Location. Moving it creates a new placement record and deactivates the old one.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/things/` | Register a new thing |
| GET | `/api/v1/things/` | List things (paginated) |
| GET | `/api/v1/things/{id}` | Get a single thing |
| PATCH | `/api/v1/things/{id}` | Update a thing |
| DELETE | `/api/v1/things/{id}` | Delete a thing |
| POST | `/api/v1/things/{id}/place` | Place a thing at a location |
| GET | `/api/v1/things/{id}/placements` | Get placement history |

## Register a Thing

```bash
curl -X POST http://localhost:8000/api/v1/things/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Red spatula", "description": "Silicone spatula for cooking"}'
```

Response:

```json
{
  "id": "b2c3d4e5-...",
  "name": "Red spatula",
  "description": "Silicone spatula for cooking",
  "metadata_json": "{\"category\": \"kitchenware\", \"tags\": [\"red\", \"spatula\", \"silicone\", \"cooking\"], \"material\": \"plastic\", \"room_hint\": \"kitchen\", \"usage_context\": [\"kitchenware\", \"kitchen\"]}",
  "location_path": null,
  "created_at": "2025-01-15T10:05:00",
  "updated_at": "2025-01-15T10:05:00"
}
```

### Register and place in one call

Pass `location_id` to simultaneously create and place:

```bash
curl -X POST http://localhost:8000/api/v1/things/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Red spatula",
    "description": "Silicone spatula for cooking",
    "location_id": "<kitchen-drawer-uuid>"
  }'
```

The response will include `location_path`.

## Metadata Enrichment

The enricher analyzes name + description tokens against keyword dictionaries:

| Field | Description | Example |
|-------|-------------|---------|
| `category` | Primary category (8 categories) | `kitchenware`, `electronics`, `tools` |
| `material` | Material detection (7 materials) | `plastic`, `metal`, `wood` |
| `room_hint` | Suggested room (7 rooms) | `kitchen`, `bedroom`, `garage` |
| `tags` | Descriptive tokens (max 30) | `["red", "spatula", "silicone"]` |
| `usage_context` | Inferred usage areas | `["kitchenware", "kitchen"]` |

**Supported categories**: electronics, kitchenware, clothing, tools, furniture, stationery, toiletries, toys, general.

**Supported materials**: metal, plastic, wood, glass, ceramic, fabric, paper.

**Supported room hints**: kitchen, bedroom, bathroom, living room, garage, office, laundry.

## List Things

```bash
# Default pagination (offset=0, limit=50)
curl http://localhost:8000/api/v1/things/

# Custom pagination
curl "http://localhost:8000/api/v1/things/?offset=10&limit=20"
```

Response:

```json
{
  "items": [{"id": "...", "name": "Red spatula", ...}],
  "total": 42,
  "offset": 0,
  "limit": 50
}
```

## Get a Thing

```bash
curl http://localhost:8000/api/v1/things/<uuid>
```

Includes the current `location_path` if the thing is placed.

## Update a Thing

```bash
curl -X PATCH http://localhost:8000/api/v1/things/<uuid> \
  -H "Content-Type: application/json" \
  -d '{"name": "Blue spatula", "regenerate_metadata": true}'
```

Set `regenerate_metadata: true` to re-run the enricher after changing the name or description. The vector index is always re-generated on update.

### Update fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string or null | New name (null to keep existing) |
| `description` | string or null | New description (null to keep existing) |
| `regenerate_metadata` | boolean | Re-run metadata enrichment (default: false) |

## Delete a Thing

```bash
curl -X DELETE http://localhost:8000/api/v1/things/<uuid>
```

This also removes the thing's vectors from Qdrant. Returns `204 No Content` on success.

## Place a Thing

Move or place a thing at a location:

```bash
curl -X POST http://localhost:8000/api/v1/things/<thing-uuid>/place \
  -H "Content-Type: application/json" \
  -d '{"thing_id": "<thing-uuid>", "location_id": "<location-uuid>"}'
```

Response:

```json
{
  "id": "c3d4e5f6-...",
  "thing_id": "b2c3d4e5-...",
  "location_id": "a1b2c3d4-...",
  "placed_at": "2025-01-15T10:10:00",
  "active": true
}
```

**Behavior**: The previous active placement is automatically deactivated. Only one placement per thing is active at a time.

## Placement History

```bash
curl http://localhost:8000/api/v1/things/<uuid>/placements
```

Returns all placements (active and historical), ordered by creation time.

## Error Codes

| Code | Meaning |
|------|---------|
| 201 | Thing created |
| 204 | Thing deleted |
| 404 | Thing or location not found |
