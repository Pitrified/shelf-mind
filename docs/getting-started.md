# Getting Started

This guide walks through setting up ShelfMind for local development.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- [Qdrant](https://qdrant.tech/) vector database (for search features)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Pitrified/shelf-mind.git
cd shelf-mind
```

### 2. Install Dependencies

```bash
# Install core + webapp + dev dependencies
uv sync --extra webapp --group dev

# Or install specific groups
uv sync                    # Core only (domain, infrastructure)
uv sync --extra webapp     # Core + FastAPI webapp
uv sync --group test       # Testing only
uv sync --group lint       # Linting only
uv sync --group docs       # Documentation only
```

### 3. Start Qdrant

ShelfMind uses Qdrant for vector similarity search. The easiest option is Docker:

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

!!! tip
    ShelfMind starts gracefully even if Qdrant is unreachable.
    Location and thing management work without it; only search features require Qdrant.

### 4. Set Environment Variables

Create a `.env` file at `~/cred/shelf-mind/.env`:

```bash
# Google OAuth (required for authentication)
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here

# Session secret (required)
SM_SESSION_SECRET_KEY=your_random_secret_here
```

See the [Webapp Setup Guide](guides/webapp_setup.md) for detailed OAuth configuration.

### 5. Start the Server

```bash
uv run uvicorn shelf_mind.webapp.app:app --reload
```

The API is now available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 6. Verify Installation

```bash
# Run the full verification suite
uv run pytest && uv run ruff check . && uv run pyright
```

## Development Workflow

### Running Tests

```bash
uv run pytest                      # All tests
uv run pytest -v                   # Verbose output
uv run pytest tests/domain/        # Domain layer only
uv run pytest tests/application/   # Service layer only
uv run pytest tests/webapp/        # Webapp layer only
```

### Code Quality

```bash
# Lint (ALL ruff rules enabled)
uv run ruff check .
uv run ruff format .

# Type checking
uv run pyright
```

### Pre-commit Hooks

```bash
# Install hooks (first time only)
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

## Building Documentation

```bash
uv sync --group docs
uv run mkdocs serve     # Local server with hot reload
uv run mkdocs build     # Static site
```

## Project Structure

```
shelf-mind/
├── src/shelf_mind/
│   ├── application/         # Service layer (use cases)
│   ├── config/              # Configuration classes
│   ├── core/                # DI container
│   ├── domain/              # Entities, schemas, repository ABCs
│   ├── infrastructure/      # DB, vector store, embeddings, vision
│   ├── params/              # Environment and path resolution
│   └── webapp/              # FastAPI app, routers, middleware
├── tests/                   # Test suite (mirrors src/ structure)
├── docs/                    # Documentation (MkDocs)
├── static/                  # CSS, JS, images
├── templates/               # Jinja2 HTML templates
├── scratch_space/           # Exploratory notebooks
└── data/                    # SQLite database (auto-created)
```

## What's Next

- [User Guide](user-guide/index.md) - Learn to use the API
- [Developer Guide](dev/index.md) - Understand the architecture
- [Contributing](contributing.md) - How to contribute
