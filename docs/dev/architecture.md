# Architecture

ShelfMind follows a **layered Domain-Driven Design** with strict dependency direction: outer layers depend on inner layers, never the reverse.

## Layer Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     Webapp Layer                                 │
│  FastAPI app, routers, middleware, auth, Jinja2/HTMX templates   │
│  shelf_mind.webapp.*                                             │
├──────────────────────────────────────────────────────────────────┤
│                     Application Layer                            │
│  Use-case services, errors, search ranker                        │
│  shelf_mind.application.*                                        │
├──────────────────────────────────────────────────────────────────┤
│                     Domain Layer                                 │
│  Entities (SQLModel), repository ABCs, domain schemas            │
│  shelf_mind.domain.*                                             │
├──────────────────────────────────────────────────────────────────┤
│                     Infrastructure Layer                         │
│  SQLite repos, Qdrant vectors, embeddings, enricher, vision      │
│  shelf_mind.infrastructure.*                                     │
└──────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### Repository pattern

Domain defines abstract repository interfaces (ABCs). Infrastructure provides concrete implementations. Services depend only on abstractions.

```
domain/repositories/location_repository.py   -> LocationRepository (ABC)
infrastructure/db/location_repo.py           -> SqlLocationRepository(LocationRepository)
```

### Strategy pattern (Vision)

The vision system uses the Strategy pattern to allow swapping implementations:

```
infrastructure/vision/vision_strategy.py -> VisionStrategy (ABC)
                                         -> NoOpVisionStrategy (Phase 1)
                                         -> (future) CLIPVisionStrategy
```

### Materialized path for hierarchies

Locations use a materialized path string (`/Home/Kitchen/Drawer`) for fast prefix queries. The path is auto-maintained on create, rename, and move operations, including all descendants.

## DI Container

The `Container` class (`shelf_mind.core.container`) is the central dependency injection registry. It holds singleton infrastructure instances and provides factory methods for session-scoped services.

### Lifecycle

```python
# 1. Create container with config
container = Container(config=ShelfMindConfig())

# 2. Initialize (creates DB, Qdrant collection, loads embedder)
container.initialize()

# 3. Get session-scoped services
location_svc = container.location_service(session)
thing_svc = container.thing_service(session)
placement_svc = container.placement_service(session)

# 4. Get session-independent services
search_svc = container.search_service()
```

### What gets initialized

| Component | Type | Scope |
|-----------|------|-------|
| SQLite engine | Module-level global | Application |
| QdrantClient | Singleton | Application |
| QdrantVectorRepository | Singleton | Application |
| SentenceTransformerEmbedder | Singleton (lazy-loaded) | Application |
| RuleBasedMetadataEnricher | Singleton | Application |
| NoOpVisionStrategy | Singleton | Application |
| SearchRanker | Singleton | Application |
| SqlLocationRepository | New instance | Per-session |
| SqlThingRepository | New instance | Per-session |
| SqlPlacementRepository | New instance | Per-session |

## Request Flow

A typical API request flows through these layers:

```
HTTP Request
  -> FastAPI Router (webapp/api/v1/*_router.py)
    -> Dependency injection (get_domain_session, get_domain_container)
      -> Application Service (application/services/*_service.py)
        -> Repository ABC call
          -> Infrastructure implementation (infrastructure/db/*_repo.py)
            -> SQLModel/SQLite
        -> Vector repository (infrastructure/vector/qdrant_repository.py)
          -> Qdrant
      -> Response DTO (webapp/schemas/domain_schemas.py)
  -> HTTP Response
```

### Example: Creating a Thing

1. `POST /api/v1/things/` hits `thing_router.create_thing()`
2. FastAPI injects `Session` and `Container` via dependencies
3. Router calls `container.thing_service(session)` to get a `ThingService`
4. `ThingService.create_thing()`:
    - Calls `MetadataEnricher.enrich()` to extract category, tags, material
    - Persists the `Thing` entity via `ThingRepository.create()`
    - Builds embed text from name + description + tags
    - Generates a 384-dim vector via `TextEmbeddingProvider.embed()`
    - Upserts the vector + payload into Qdrant via `VectorRepository.upsert_text_vector()`
5. If `location_id` was provided, router also calls `PlacementService.place_thing()`
6. Router constructs and returns `ThingResponse` DTO

## Webapp Structure

The webapp layer follows a modular organization:

```
webapp/
├── app.py              # FastAPI application factory
├── main.py             # Entrypoint
├── api/v1/             # Domain API routers (locations, things, search)
│   ├── api_router.py   # Aggregates all v1 routes
│   ├── location_router.py
│   ├── thing_router.py
│   └── search_router.py
├── routers/            # Webapp routers (auth, health, pages)
│   ├── auth_router.py
│   ├── health_router.py
│   └── pages_router.py
├── core/               # Cross-cutting concerns
│   ├── dependencies.py # FastAPI Depends functions
│   ├── exceptions.py   # Custom exceptions + handlers
│   ├── middleware.py    # RequestID, Security, Logging, CORS
│   ├── security.py     # Security headers, CSP
│   └── templating.py   # Jinja2 setup
├── schemas/            # API DTOs (Pydantic models)
│   ├── domain_schemas.py   # Location/Thing/Placement/Search DTOs
│   ├── auth_schemas.py     # Auth DTOs
│   └── common_schemas.py   # Shared response schemas
└── services/           # Webapp-level services (auth, user)
    ├── auth_service.py
    └── user_service.py
```

## Testing Strategy

Tests mirror the source structure:

```
tests/
├── application/     # Service unit tests (mocked repos)
├── domain/          # Entity and schema tests
├── infrastructure/  # Repository and infra tests
├── webapp/          # API integration tests (TestClient)
├── config/          # Configuration tests
├── params/          # Parameter loading tests
└── metaclasses/     # Singleton pattern tests
```

Run with: `uv run pytest`
