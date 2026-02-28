# Services

Application services implement business use cases. Each service receives repository abstractions and infrastructure components through constructor injection.

## LocationService

Manages the hierarchical location tree.

**Dependencies**: `LocationRepository`, `PlacementRepository` (for force-delete).

### Operations

| Method | Description |
|--------|-------------|
| `create_location(name, parent_id)` | Create with auto-generated materialized path |
| `get_location(id)` | Get by UUID |
| `get_location_by_path(path)` | Get by materialized path |
| `list_locations()` | All locations sorted by path |
| `get_children(parent_id)` | Direct children |
| `get_subtree(id)` | All descendants |
| `rename_location(id, new_name)` | Rename and update all descendant paths |
| `move_location(id, new_parent_id)` | Move and rebuild all descendant paths |
| `delete_location(id, force=False)` | Delete with hierarchy constraints |

### Hierarchy Rules

- **Sibling uniqueness**: No two children of the same parent can share a name.
- **Delete constraints**: Cannot delete a location that has children. Cannot delete a location with placed things unless `force=True`.
- **Path maintenance**: On rename or move, all descendant paths are bulk-updated via `update_paths()`.

### Errors

- `LocationNotFoundError` - 404
- `DuplicateSiblingNameError` - 409
- `LocationHasChildrenError` - 409
- `LocationHasThingsError` - 409

## ThingService

Manages thing registration with automatic metadata enrichment and vector indexing.

**Dependencies**: `ThingRepository`, `VectorRepository`, `TextEmbeddingProvider`, `MetadataEnricher`.

### Operations

| Method | Description |
|--------|-------------|
| `create_thing(name, description, location_path)` | Register with enrichment + indexing |
| `get_thing(id)` | Get by UUID |
| `list_things(offset, limit)` | Paginated listing |
| `count_things()` | Total count |
| `update_thing(id, name, description, regenerate_metadata, location_path)` | Update with optional re-enrichment |
| `delete_thing(id)` | Delete thing + vectors |

### Create Pipeline

```
1. MetadataEnricher.enrich(name, description)
   -> MetadataSchema (category, tags, material, room_hint, usage_context)
2. ThingRepository.create(thing)
   -> Persist to SQLite
3. Build embed text: "{name} {description} {tags joined}"
4. TextEmbeddingProvider.embed(text)
   -> 384-dim vector
5. VectorRepository.upsert_text_vector(id, vector, payload)
   -> Store in Qdrant with indexed payload
```

### Embed Text Construction

The text used for embedding is built from three parts:

```python
parts = [name]
if description:
    parts.append(description)
if tags:
    parts.append(" ".join(tags))
return " ".join(parts)
```

This ensures the vector captures the object's name, its description, and all enriched tags for better semantic search.

## PlacementService

Manages the Thing-to-Location relationship. Only one placement per thing is active at a time.

**Dependencies**: `PlacementRepository`, `ThingRepository`, `LocationRepository`.

### Operations

| Method | Description |
|--------|-------------|
| `place_thing(thing_id, location_id)` | Place or move (deactivates previous) |
| `get_current_placement(thing_id)` | Active placement |
| `get_placement_history(thing_id)` | All placements (active and historical) |
| `get_things_at_location(location_id)` | Active placements at a location |
| `remove_placement(thing_id)` | Deactivate current placement |

### Move Semantics

Moving a thing to a new location:

1. Deactivates all active placements for the thing
2. Creates a new active placement at the target location
3. The old placement remains in history with `active=False`

## SearchService

Orchestrates text and vision search pipelines.

**Dependencies**: `VectorRepository`, `TextEmbeddingProvider`, `SearchRanker`, `VisionStrategy`.

### Text Search Pipeline

```
1. Embed query -> TextEmbeddingProvider.embed(query)
2. Vector search -> VectorRepository.search_text(vector, limit, location_filter)
3. Extract query tags -> query.lower().split()
4. Re-rank -> SearchRanker.rank(results, query_tags, location_path)
5. Return ranked SearchResult list
```

### Vision Search Pipeline

```
1. Preprocess -> VisionStrategy.preprocess(image_bytes)
2. Embed -> VisionStrategy.embed(processed)
3. Vector search -> VectorRepository.search_image(vector, limit)
4. Sort by score descending
```

Currently uses `NoOpVisionStrategy` which returns empty results.

## SearchRanker

Re-ranks raw vector search results using a weighted formula.

### Scoring Formula

$$
\text{score} = \alpha \cdot \text{vector\_score} + \beta \cdot \text{jaccard}(\text{result\_tags}, \text{query\_tags}) + \gamma \cdot \text{location\_bonus}
$$

| Weight | Default | Meaning |
|--------|---------|---------|
| $\alpha$ | 0.7 | Vector similarity importance |
| $\beta$ | 0.2 | Metadata tag overlap importance |
| $\gamma$ | 0.1 | Location match bonus |

- **Jaccard similarity**: $|A \cap B| / |A \cup B|$ between result tags and query tokens.
- **Location bonus**: 1.0 if the result's `location_path` starts with the query `location_filter`, otherwise 0.0.

## MetadataEnricher

Extracts structured metadata from thing name and description using rule-based keyword matching.

**Implementation**: `RuleBasedMetadataEnricher` (deterministic, no LLM).

### Enrichment Pipeline

```
1. Tokenize "{name} {description}".lower()
2. Detect category (8 keyword lists, best match wins)
3. Detect material (7 keyword lists, first match)
4. Detect room hint (7 keyword lists, best match wins)
5. Extract tags (filter stop words, max 30)
6. Infer usage context from category + room
```

### Output Schema

```python
class MetadataSchema(BaseModel):
    category: str            # "electronics", "kitchenware", etc.
    subtype: str | None      # Reserved for future use
    tags: list[str]          # Max 30, lowercase, deduplicated
    material: str | None     # "metal", "plastic", etc.
    room_hint: str | None    # "kitchen", "bedroom", etc.
    usage_context: list[str] # Inferred from category + room
    custom: dict[str, str]   # Reserved for user-defined metadata
```
