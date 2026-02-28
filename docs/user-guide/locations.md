# Locations

Locations model the physical hierarchy of your household: rooms, shelves, drawers, boxes.
They support unlimited nesting via a materialized-path approach.

## Concepts

- **Hierarchy**: Every location can have a parent and children.  
  Example: `Home > Kitchen > Drawer` produces the path `/Home/Kitchen/Drawer`.
- **Materialized path**: Stored as a string, enables fast prefix queries (e.g. "everything under `/Home/Kitchen`").
- **Sibling uniqueness**: No two children of the same parent can share a name.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/locations/` | Create a location |
| GET | `/api/v1/locations/` | List all locations |
| GET | `/api/v1/locations/{id}` | Get a single location |
| GET | `/api/v1/locations/{id}/children` | List children |
| PATCH | `/api/v1/locations/{id}` | Rename or move a location |
| DELETE | `/api/v1/locations/{id}?force=false` | Delete a location |

## Create a Location

### Root location

```bash
curl -X POST http://localhost:8000/api/v1/locations/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Home"}'
```

Response:

```json
{
  "id": "a1b2c3d4-...",
  "name": "Home",
  "parent_id": null,
  "path": "/Home",
  "created_at": "2025-01-15T10:00:00"
}
```

### Nested location

Pass `parent_id` to create a child:

```bash
curl -X POST http://localhost:8000/api/v1/locations/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Kitchen", "parent_id": "a1b2c3d4-..."}'
```

Response path will be `/Home/Kitchen`.

### Deeper nesting

```bash
# Create a drawer inside the kitchen
curl -X POST http://localhost:8000/api/v1/locations/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Utensil Drawer", "parent_id": "<kitchen-uuid>"}'
```

Path: `/Home/Kitchen/Utensil Drawer`

## List All Locations

```bash
curl http://localhost:8000/api/v1/locations/
```

Returns all locations sorted by path.

## Get a Location

```bash
curl http://localhost:8000/api/v1/locations/<uuid>
```

## List Children

```bash
curl http://localhost:8000/api/v1/locations/<uuid>/children
```

Returns only direct children (not the full subtree).

## Rename a Location

```bash
curl -X PATCH http://localhost:8000/api/v1/locations/<uuid> \
  -H "Content-Type: application/json" \
  -d '{"name": "Pantry"}'
```

All descendant paths are updated automatically. For example, renaming `Kitchen` to `Pantry` changes `/Home/Kitchen/Utensil Drawer` to `/Home/Pantry/Utensil Drawer`.

## Move a Location

Set `move: true` and provide a `parent_id` (or `null` for root):

```bash
curl -X PATCH http://localhost:8000/api/v1/locations/<uuid> \
  -H "Content-Type: application/json" \
  -d '{"parent_id": "<new-parent-uuid>", "move": true}'
```

Descendant paths are rebuilt automatically.

## Delete a Location

```bash
curl -X DELETE http://localhost:8000/api/v1/locations/<uuid>
```

**Constraints:**

- Fails with `409 Conflict` if the location has children.
- Fails with `409 Conflict` if Things are placed here, unless `?force=true` is set.

```bash
# Force-delete (removes placements too)
curl -X DELETE "http://localhost:8000/api/v1/locations/<uuid>?force=true"
```

## Error Codes

| Code | Meaning |
|------|---------|
| 201 | Location created |
| 404 | Location (or parent) not found |
| 409 | Duplicate sibling name, has children, or has things |
