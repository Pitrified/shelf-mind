# Developer Guide

Technical documentation for contributors and maintainers.

## Sections

- [Architecture](architecture.md) - Layered design, DI container, request flow
- [Services](services.md) - Application services and business logic
- [Infrastructure](infrastructure.md) - Database, vector store, embeddings, vision
- [Configuration](configuration.md) - Config classes, environment variables, tuning

## Quick Reference

| Layer | Package | Responsibility |
|-------|---------|---------------|
| Domain | `shelf_mind.domain` | Entities (SQLModel), repository ABCs, domain schemas |
| Application | `shelf_mind.application` | Services, errors, search ranker |
| Infrastructure | `shelf_mind.infrastructure` | SQLite repos, Qdrant, embeddings, vision, metadata enricher |
| Core | `shelf_mind.core` | DI container |
| Webapp | `shelf_mind.webapp` | FastAPI app, routers, middleware, auth, schemas |
| Config/Params | `shelf_mind.config`, `shelf_mind.params` | Pydantic configs, env loading, paths |

## Code Style

```python
from loguru import logger as lg

def fetch_entity(table: str, entity_id: str | None) -> dict:
    if entity_id is None:
        msg = "entity_id required"
        raise ValueError(msg)

    lg.info(f"Fetching {entity_id} from {table}")
    return {"id": entity_id, "table": table}
```

Key style rules:

- Ruff with ALL rules enabled (see `ruff.toml`)
- Pyright strict mode on `src/` and `tests/`
- Google-style docstrings on all public interfaces
- Never use em dashes
- Error messages in a separate `msg` variable before `raise`
