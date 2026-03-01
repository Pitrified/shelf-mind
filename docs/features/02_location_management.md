# Feature 02 - Location Management

## Purpose

Manage a hierarchical location tree (rooms, shelves, drawers, etc.) with materialized paths. Supports create, rename, delete, and navigation.

## UI Pages

### `/pages/locations`

Two-column layout: location tree (left) + detail panel (right).

| HTMX Endpoint | Method | Description |
|---------------|--------|-------------|
| `/pages/locations/tree` | GET | Full location tree (root nodes) |
| `/pages/locations/create` | POST form | Create root or child location |
| `/pages/locations/{id}/detail` | GET | Detail panel for one location |
| `/pages/locations/{id}/rename` | POST form | Rename location; updates descendants' paths via OOB swap |
| `/pages/locations/{id}` | DELETE | Delete location; enforces hierarchy constraints |

**Rename OOB pattern**: The rename endpoint returns two fragments:
1. Updated detail panel (primary `hx-target="#location-detail"`)
2. `<div id="location-tree" hx-swap-oob="innerHTML">...updated tree...</div>`

This keeps both panels in sync without a full page reload.

## Hierarchy Constraints

| Condition | Behavior |
|-----------|----------|
| Location has children | Delete blocked → `LocationHasChildrenError` |
| Location has Things placed | Delete blocked unless `force=1` → `LocationHasThingsError` |
| Duplicate sibling name | Create/rename blocked → `DuplicateSiblingNameError` |

**Force delete**: Passing `force=1` (form value) forces deletion; all active placements at that location are removed.

## Materialized Path

Paths are stored as strings like `/Home/Kitchen/Drawer`. On rename or move, all descendant paths are updated atomically via `SqlLocationRepository.update_paths(old_path_prefix, new_path_prefix)`.

```
/Home
/Home/Kitchen
/Home/Kitchen/Utensil Drawer  ← rename Kitchen → Cucina produces
/Home/Cucina
/Home/Cucina/Utensil Drawer
```

## Key Service Methods

```python
LocationService.create_location(name, parent_id) -> Location
LocationService.get_location(location_id) -> Location
LocationService.list_locations() -> list[Location]
LocationService.get_children(parent_id) -> list[Location]
LocationService.rename_location(location_id, new_name) -> Location
LocationService.move_location(location_id, new_parent_id) -> Location
LocationService.delete_location(location_id, force=False) -> bool
```

## Template Files

| File | Role |
|------|------|
| `templates/pages/locations.html` | Main page |
| `templates/partials/location_tree.html` | Recursive tree list |
| `templates/partials/location_detail.html` | Detail panel with rename, delete, add-child |

## Pitfalls

- **Children rendered flat**: The tree partial only renders root nodes and does not recursively render children in the tree; clicking a location shows its detail which lists children as clickable tags. Deep navigation is click-through not expandable tree.
- **Move location**: `move_location()` is implemented in `LocationService` but there is no dedicated UI form yet. Use the REST API (`PATCH /api/v1/locations/{id}`) to move locations.

## Related Links

- [Thing Registration](01_thing_registration.md)
- [API reference: Locations](/reference/shelf_mind/application/services/location_service/)
- [User guide: Locations](/user-guide/locations/)
