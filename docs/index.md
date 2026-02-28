# ShelfMind

Welcome to the **ShelfMind** documentation.

ShelfMind is a fully local-first household object registry and multimodal retrieval system.
It enables structured spatial modeling and hybrid (text + metadata + vision) search, all running on your own hardware with zero cloud dependencies.

## What it Does

- **Register household objects** with automatic metadata enrichment (category, material, room hints, tags)
- **Organize locations** in an unlimited hierarchy (house > room > shelf > drawer)
- **Track placement** of objects across locations with full history
- **Search by text** using semantic vector similarity enhanced with metadata re-ranking
- **Search by image** (Phase 2) using vision embeddings for visual object retrieval

## Architecture at a Glance

```
┌──────────────────────────────────────────────────────┐
│  FastAPI Webapp (REST API + Jinja2/HTMX frontend)    │
├──────────────────────────────────────────────────────┤
│  Application Services (Location, Thing, Placement,   │
│  Search, SearchRanker)                               │
├──────────────────────────────────────────────────────┤
│  Domain Layer (Entities, Schemas, Repository ABCs)   │
├──────────────────────────────────────────────────────┤
│  Infrastructure (SQLite, Qdrant, SentenceTransformer,│
│  RuleBasedEnricher, VisionStrategy)                  │
└──────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone and install
git clone https://github.com/Pitrified/shelf-mind.git
cd shelf-mind
uv sync --extra webapp

# Start the server (Qdrant must be running on localhost:6333)
uv run uvicorn shelf_mind.webapp.app:app --reload

# Run the verification suite
uv run pytest && uv run ruff check . && uv run pyright
```

## Documentation Overview

| Section | Description |
|---------|-------------|
| [Getting Started](getting-started.md) | Installation, environment setup, first run |
| [User Guide](user-guide/index.md) | How to use the API: locations, things, search |
| [Developer Guide](dev/index.md) | Architecture, services, infrastructure deep dives |
| [Next Steps](next-steps.md) | Proposed improvements and future features |
| [Specifications](specs/functional_specification.md) | Original functional and technical specs |
| [Guides](guides/uv.md) | Tool-specific guides (uv, pre-commit, webapp setup) |
| [API Reference](reference/) | Auto-generated API docs from source |
| [Contributing](contributing.md) | How to contribute |
