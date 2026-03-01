# Next Steps

Analysis of the current codebase with proposed improvements, organized by priority.

## Critical Fixes

### 1. Add authentication to domain API endpoints

**Problem**: The location, thing, and search endpoints under `/api/v1/` are currently unprotected. Only the example `/api/v1/protected` endpoint requires authentication.

**Fix**: Add `Depends(get_current_user)` to all domain routers, or apply it at the `api_router` level:

```python
# In api_router.py, add auth dependency to the parent router
router = APIRouter(
    prefix="/api/v1",
    tags=["api-v1"],
    dependencies=[Depends(get_current_user)],
)
```

### 2. Fix `thing_id` path parameter in place endpoint

**Problem**: In `thing_router.py`, the `place_thing` endpoint takes `thing_id` as a path parameter but ignores it (marked `ARG001`), using `body.thing_id` instead. This creates a mismatch where the URL says one thing but the body can reference another.

**Fix**: Use the path parameter and remove `thing_id` from the request body:

```python
@router.post("/{thing_id}/place")
async def place_thing(thing_id: uuid.UUID, body: PlacementCreate, ...):
    placement_svc.place_thing(thing_id, body.location_id)
```

### 3. Replace in-memory session storage

**Problem**: `SessionStore` uses a plain dictionary. All sessions are lost on restart. Not suitable for multi-worker deployments.

**Fix**: Use signed cookies (e.g. `itsdangerous`), Redis, or database-backed sessions.

## Missing Features

### 4. Image indexing during thing creation

**Status**: Things are only indexed with text vectors. Image vectors are always zero vectors.

**Implementation**:

- Accept an optional image upload on `POST /api/v1/things/`
- Implement a real `VisionStrategy` (e.g. CLIP)
- Call `VectorRepository.upsert_image_vector()` with the image embedding
- Store or reference the image (file path or S3 key)

### 5. Hybrid search (text + metadata + location combined query)

**Status**: Text search re-ranks with metadata and location, but there is no combined query that searches by text AND filters by category/material directly.

**Implementation**:

- Add `category`, `material`, `tags` filter fields to `SearchRequest`
- Use Qdrant's `Filter` with multiple conditions
- Combine vector search with structured metadata filtering

### 6. Thing deletion cascade

**Status**: Deleting a thing removes its vectors but does not clean up placements in SQLite.

**Fix**: Add cascade delete or explicitly delete placements before deleting the thing:

```python
def delete_thing(self, thing_id):
    self.get_thing(thing_id)
    self._vector_repo.delete_vectors(thing_id)
    # Add: self._placement_repo.delete_by_thing(thing_id)
    return self._repo.delete(thing_id)
```

### 7. Location subtree listing via API

**Status**: `LocationService.get_subtree()` exists but has no API endpoint.

**Fix**: Add `GET /api/v1/locations/{id}/subtree` to expose the full descendant tree.

### 8. Batch operations

Add bulk endpoints for common operations:

- `POST /api/v1/things/batch` - Register multiple things
- `POST /api/v1/locations/batch` - Create multiple locations
- `DELETE /api/v1/things/batch` - Delete multiple things

## Testing Gaps

### 9. Increase test coverage for core services

Current gaps:

| Component                                | Status   |
| ---------------------------------------- | -------- |
| `SearchService`                          | No tests |
| `ThingService`                           | No tests |
| `Container`                              | No tests |
| `QdrantVectorRepository`                 | No tests |
| `SentenceTransformerEmbedder`            | No tests |
| API v1 routers (location, thing, search) | No tests |

Priority: Add unit tests for `SearchService` and `ThingService` with mocked infrastructure. Add integration tests for the API routers using `TestClient`.

### 10. Add integration test suite

Create a test fixture that spins up a real SQLite database and (optionally) a Qdrant docker container for end-to-end testing.

## Performance

### 11. Async embedding generation

**Problem**: `SentenceTransformerEmbedder.embed()` is synchronous and blocks the FastAPI event loop.

**Fix**: Wrap in `asyncio.to_thread()` or use a thread pool:

```python
import asyncio

vector = await asyncio.to_thread(self._embedder.embed, text)
```

### 12. Connection pooling for Qdrant

**Problem**: Single `QdrantClient` instance. Under high load, requests may queue.

**Fix**: Use `QdrantClient` with gRPC transport (`prefer_grpc=True`) for better concurrency, or pool multiple clients.

### 13. Database connection pooling

**Problem**: SQLite with `check_same_thread=False` is sufficient for development but not for production.

**Fix**: For production, consider PostgreSQL with SQLAlchemy's built-in connection pooling.

## Security

### 14. Rate limiting

**Status**: Middleware is defined but no rate limiting is implemented.

**Implementation**: Use `slowapi` or a custom middleware that tracks requests per IP/user and returns `429 Too Many Requests`.

### 15. Input sanitization for search queries

**Status**: Search queries are passed directly to the embedding model. No sanitization on length or content.

**Fix**: Validate query length (e.g. max 500 chars), strip HTML/scripts, and normalize whitespace.

### 16. CSRF protection for state-changing endpoints

**Status**: No CSRF tokens. The session cookie is the only auth mechanism.

**Fix**: Add CSRF token middleware for POST/PATCH/DELETE routes, or switch to Bearer token auth for the API.

## Infrastructure

### 17. Database migrations

**Status**: Tables are created via `SQLModel.metadata.create_all()`. No migration support.

**Implementation**: Add Alembic with SQLModel integration:

```bash
uv add alembic
alembic init migrations
# Configure env.py to use SQLModel metadata
```

### 18. Docker compose

**Status**: No Docker or docker-compose configuration.

**Deliverable**: `docker-compose.yml` with:

- ShelfMind app container
- Qdrant container
- Shared volume for SQLite data
- Health checks

### 19. CI/CD pipeline

**Status**: No GitHub Actions or CI configuration.

**Deliverable**: Workflow that runs `pytest`, `ruff check`, and `pyright` on every push/PR.

## UX Improvements

### 20. Frontend pages for domain operations

**Status**: The Jinja2/HTMX frontend has landing, dashboard, and error pages, but no pages for managing locations, things, or searching.

**Implementation**: Add HTMX-powered pages for:

- Location tree browser
- Thing registration form with live metadata preview
- Search page with results display

### 21. SSE/WebSocket for async search feedback

For long-running searches (especially vision), provide real-time progress updates via Server-Sent Events.

## Dependency Cleanup

### 22. Remove unused dependencies

The following packages are declared in `pyproject.toml` but not imported anywhere in the source:

- `haystack-ai`
- `ollama-haystack`
- `openai`
- `tiktoken`

These likely represent planned integrations. If not needed now, consider moving them to an optional extras group to reduce install size.
