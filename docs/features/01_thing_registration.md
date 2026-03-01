# Feature 01 - Thing Registration and Management

## Purpose

Manage the full lifecycle of household objects (Things) - create, browse, edit, and delete - with automatic metadata enrichment and semantic vector indexing.

## UI Pages

### `/pages/things` (Register tab)

| HTMX Endpoint | Method | Description |
|---------------|--------|-------------|
| `/pages/things/create` | POST form | Register a new Thing; returns success/error message |
| `/pages/things/preview` | POST form | Live metadata preview (keyup debounce, 500 ms) |
| `/pages/things/location-options` | GET | Populate location `<select>` on load |

**Form fields**: `name` (required, 1-120 chars), `description` (optional), `location_id` (optional UUID).

**Success flow**: `create_thing()` → metadata enrichment → SQL persist → text embedding → Qdrant upsert → optional `place_thing()`.

### `/pages/things` (Browse tab)

| HTMX Endpoint | Method | Description |
|---------------|--------|-------------|
| `/pages/things/list` | POST form | Paginated list; accepts `q` (name filter), `offset`, `limit` |
| `/pages/things/{id}/detail` | GET | Detail card with metadata, location, tags |
| `/pages/things/{id}/edit-form` | GET | Inline edit form (name, description, re-enrich flag) |
| `/pages/things/{id}/update` | POST form | Apply edits; delegates to `update_thing()` |
| `/pages/things/{id}` | DELETE | Delete thing + vector; returns refreshed list |

## Data Flow

```
Browser (HTMX)
  POST /pages/things/create
    └─ ThingService.create_thing()
         ├─ RuleBasedMetadataEnricher.enrich()  →  MetadataSchema
         ├─ SqlThingRepository.create()         →  Thing (SQL)
         ├─ SentenceTransformerEmbedder.embed() →  vector[384]
         └─ QdrantVectorRepository.upsert()     →  Qdrant point
```

## Template Files

| File | Role |
|------|------|
| `templates/pages/things.html` | Main page with Register/Browse tabs |
| `templates/partials/things_list.html` | Paginated list rows |
| `templates/partials/thing_detail.html` | Detail card + action buttons |
| `templates/partials/thing_edit_form.html` | Inline edit form |

## Key Service Methods

```python
ThingService.create_thing(name, description, location_path) -> Thing
ThingService.list_things(offset, limit) -> list[Thing]
ThingService.get_thing(thing_id) -> Thing
ThingService.update_thing(thing_id, name, description, regenerate_metadata, location_path) -> Thing
ThingService.delete_thing(thing_id) -> bool
```

## Metadata Schema

Returned by `RuleBasedMetadataEnricher`:

```python
class MetadataSchema(BaseModel):
    category: str       # e.g. "tools", "kitchenware"
    material: str       # e.g. "metal", "plastic"
    room_hint: str      # e.g. "garage", "kitchen"
    tags: list[str]     # tokenised descriptors (max 30)
    usage_context: list[str]
```

## Pitfalls

- **Thing list filtering is in-memory**: `list_things(limit=10_000)` then Python filter. Acceptable for household scale (<10k items) but add a `search_by_name` repo method if you need database-level filtering.
- **Placement is separate**: Registering a Thing with a `location_id` calls `PlacementService.place_thing()` after creation. Updating a Thing does NOT update its placement - use the placements API (`/api/v1/things/{id}/place`).
- **Vector update on edit**: `update_thing()` always re-indexes vectors.

## Related Links

- [Location Management](02_location_management.md)
- [API reference: Things](/reference/shelf_mind/application/services/thing_service/)
- [User guide: Things](/user-guide/things/)
