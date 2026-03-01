# Infrastructure

The infrastructure layer provides concrete implementations of domain repository interfaces, plus cross-cutting components for embeddings, vector storage, metadata enrichment, and vision.

## Database (SQLite + SQLModel)

**Package**: `shelf_mind.infrastructure.db`

### Engine Management

The database uses a module-level engine pattern:

```python
from shelf_mind.infrastructure.db.database import create_db_engine, init_db

# Called once at startup (via Container.initialize)
create_db_engine("sqlite:///data/shelf_mind.db")
init_db()  # CREATE TABLE IF NOT EXISTS for all SQLModel entities
```

- Default: `sqlite:///data/shelf_mind.db` (auto-created)
- `check_same_thread=False` for SQLite (required for FastAPI's async)
- Sessions are created per-request via `get_domain_session()` dependency

### SQL Repositories

Each domain repository ABC has a SQL implementation:

| ABC | Implementation | Table |
|-----|----------------|-------|
| `LocationRepository` | `SqlLocationRepository` | `location` |
| `ThingRepository` | `SqlThingRepository` | `thing` |
| `PlacementRepository` | `SqlPlacementRepository` | `placement` |

All repositories take a `Session` in their constructor and call `session.commit()` / `session.refresh()` on write operations.

### Entity Relationships

```
Location 1:N Location  (parent-child, self-referential)
Location 1:N Placement
Thing    1:N Placement
```

Key SQLModel details:

- UUIDs as primary keys (generated with `uuid.uuid4()`)
- `location.path` is indexed for prefix queries
- `placement.active` is a boolean flag (not a soft-delete timestamp)
- Cascade: `Location.children` uses `cascade="all"` for parent-child

## Vector Store (Qdrant)

**Package**: `shelf_mind.infrastructure.vector`

### Collection Setup

The collection uses **named vectors** to store text and image embeddings in the same point:

```python
vectors_config = {
    "text_vector": VectorParams(size=384, distance=Distance.COSINE),
    "image_vector": VectorParams(size=512, distance=Distance.COSINE),
}
```

Payload indexes are created for filtering:

- `thing_id` (keyword)
- `name` (keyword)
- `category` (keyword)
- `location_path` (keyword)
- `tags` (keyword)

### Point Structure

Each Qdrant point represents one Thing:

```json
{
    "id": "<thing-uuid>",
    "vector": {
        "text_vector": [0.12, -0.34, ...],
        "image_vector": [0.0, 0.0, ...]
    },
    "payload": {
        "thing_id": "<thing-uuid>",
        "name": "Red spatula",
        "description": "Silicone spatula for cooking",
        "category": "kitchenware",
        "tags": ["red", "spatula", "silicone", "cooking"],
        "location_path": "/Home/Kitchen"
    }
}
```

### Search

- **Text search** uses `query_points()` with the `text_vector` named vector.
  When `location_filter` is provided, a `FieldCondition` with `MatchText` filters on `location_path`.
- **Image search** uses `query_points()` with the `image_vector` named vector.

Both return `SearchResult` domain objects hydrated from the point's payload.

### Connection

Default URL: `http://localhost:6333` (configurable via `ShelfMindConfig.qdrant_url`).

For persistent local storage (no external server), set `ShelfMindConfig.qdrant_path`:

```python
# In config or environment:
QDRANT_PATH=/data/qdrant_storage  # uses local filesystem instead of URL
```

When `qdrant_path` is set, the client opens the collection directly from disk, which
is ideal for single-node deployments. When using a remote server, gRPC is preferred
(`prefer_grpc=True`) for better throughput.

The app starts gracefully without Qdrant - only search features require it.

## Text Embeddings

**Package**: `shelf_mind.infrastructure.embeddings`

### SentenceTransformerEmbedder

- Model: `all-MiniLM-L6-v2` (384 dimensions)
- **Lazy-loaded**: The model is imported and loaded on the first call to `embed()`, avoiding startup overhead
- Output: `list[float]` of 384 values
- Configurable via `ShelfMindConfig.text_model_name`

```python
class SentenceTransformerEmbedder(TextEmbeddingProvider):
    def embed(self, text: str) -> list[float]:
        model = self._load_model()  # lazy load
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
```

!!! warning "Synchronous embedding"
    Embedding generation is synchronous and runs on the main thread. For production use, consider wrapping in `asyncio.to_thread()` or using a background task queue.

## Metadata Enrichment

**Package**: `shelf_mind.infrastructure.metadata`

### RuleBasedMetadataEnricher

A fully deterministic, offline enricher that uses keyword dictionaries:

- **8 categories**: electronics, kitchenware, clothing, tools, furniture, stationery, toiletries, toys (+ "general" default)
- **7 materials**: metal, plastic, wood, glass, ceramic, fabric, paper
- **7 room hints**: kitchen, bedroom, bathroom, living room, garage, office, laundry

**Category detection** scores each category by counting matching keywords; the highest score wins. Tie goes to the first match.

**Tag extraction** splits name + description into tokens, filters stop words and tokens shorter than 3 characters, deduplicates, and caps at 30 tags.

### Extending the Enricher

To add a new enrichment strategy (e.g. LLM-based):

1. Subclass `MetadataEnricher` (ABC)
2. Implement `enrich(name, description) -> MetadataSchema`
3. Register it in `Container.__init__()` instead of `RuleBasedMetadataEnricher`

## Vision

**Package**: `shelf_mind.infrastructure.vision`

### VisionStrategy (ABC)

```python
class VisionStrategy(ABC):
    def preprocess(self, image_bytes: bytes) -> Any: ...
    def embed(self, image_array: Any) -> list[list[float]]: ...
```

### NoOpVisionStrategy (Phase 1)

Returns a single zero vector of 512 dimensions. Allows the system to operate without a vision model.

### Implementing a Real Vision Strategy

To add image search support:

1. Create `CLIPVisionStrategy(VisionStrategy)` in `infrastructure/vision/`
2. Implement `preprocess()` (PIL resize + normalize) and `embed()` (CLIP forward pass)
3. Register it in `Container.initialize()`:

```python
self._vision = CLIPVisionStrategy(model_name=self._config.image_model_name)
```

4. When creating/updating things, also call `VectorRepository.upsert_image_vector()` with the image embedding

## Middleware

**Package**: `shelf_mind.webapp.core.middleware`

The FastAPI app registers several middleware layers:

| Middleware | Purpose |
|-----------|---------|
| RequestID | Adds `X-Request-ID` header (UUID) to every response |
| Security | Sets security headers (CSP, X-Frame-Options, etc.) |
| Logging | Logs request method, path, status, and duration |
| CORS | Configurable cross-origin resource sharing |

## Authentication

Google OAuth 2.0 with SQLite-backed session storage:

1. `/auth/google` - Redirects to Google consent screen
2. `/auth/google/callback` - Handles OAuth callback, creates session
3. `/auth/logout` - Destroys session
4. Session cookie (`session`) maps to `SessionData` in a `SqliteSessionStore` backed by SQLite

!!! note
    All domain API endpoints (locations, things, search) now require authentication via the `get_current_user` dependency on the v1 router.

## Database Connection Pooling

SQLite connections are lightweight and do not benefit from heavy pooling. By default
SQLModel opens a new connection per session via `create_engine(url, connect_args={"check_same_thread": False})`.

For **PostgreSQL** deployments, configure connection pooling via SQLAlchemy's pool parameters:

```python
from sqlmodel import create_engine

engine = create_engine(
    "postgresql+psycopg2://user:pass@localhost/shelf_mind",
    pool_size=10,          # permanent connections
    max_overflow=20,       # temporary overflow connections
    pool_timeout=30,       # seconds to wait for a free connection
    pool_recycle=1800,     # recycle connections after 30 min
    pool_pre_ping=True,    # verify connections before use
)
```

Alternatively, use an external connection pooler like **PgBouncer** in transaction mode, and
set `pool_size=1` in SQLAlchemy to let PgBouncer handle multiplexing.

## Migrations (Alembic)

Database schema migrations are managed by Alembic. Config lives in `alembic.ini`,
migration scripts in `migrations/`.

```bash
# Create a new migration after changing SQLModel entities:
uv run alembic revision --autogenerate -m "describe changes"

# Apply pending migrations:
uv run alembic upgrade head

# Rollback one step:
uv run alembic downgrade -1
```

!!! note
    The migration env uses `render_as_batch=True` for SQLite compatibility (ALTER TABLE
    limitations). For PostgreSQL, normal migrations work fine.
