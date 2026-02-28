# Configuration

ShelfMind uses two configuration classes: `ShelfMindConfig` for the domain layer and `WebappConfig` for the web application.

## ShelfMindConfig

Central configuration for the domain layer. Used by the `Container`.

```python
from shelf_mind.config.shelf_mind_config import ShelfMindConfig

config = ShelfMindConfig(
    database_url="sqlite:///data/shelf_mind.db",
    qdrant_url="http://localhost:6333",
    qdrant_collection="things",
    text_model_name="all-MiniLM-L6-v2",
    text_vector_dim=384,
    image_vector_dim=512,
    rank_alpha=0.7,
    rank_beta=0.2,
    rank_gamma=0.1,
)
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_url` | str | `sqlite:///data/shelf_mind.db` | SQLite connection string |
| `qdrant_url` | str | `http://localhost:6333` | Qdrant server URL |
| `qdrant_collection` | str | `things` | Qdrant collection name |
| `text_model_name` | str | `all-MiniLM-L6-v2` | sentence-transformers model |
| `image_model_name` | str | `clip-ViT-B-32` | Vision model (Phase 2) |
| `text_vector_dim` | int | 384 | Text embedding dimensions |
| `image_vector_dim` | int | 512 | Image embedding dimensions |
| `rank_alpha` | float | 0.7 | Vector similarity weight |
| `rank_beta` | float | 0.2 | Metadata overlap weight |
| `rank_gamma` | float | 0.1 | Location bonus weight |

### Tuning the Ranker

The search ranker uses three weights that must sum to 1.0:

- **alpha (0.7)**: How much the raw vector similarity influences the final score. Higher values favor semantic matches.
- **beta (0.2)**: How much keyword overlap between query tokens and thing tags matters. Higher values favor exact keyword matches.
- **gamma (0.1)**: Bonus when the thing's location matches the location filter. Higher values favor spatial proximity.

## WebappConfig

Configuration for the FastAPI web application, loaded from environment variables.

### Required Environment Variables

Set these in `~/cred/shelf-mind/.env`:

```bash
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
SM_SESSION_SECRET_KEY=your_random_secret_here
```

### Webapp Settings

| Setting | Source | Description |
|---------|--------|-------------|
| `google_client_id` | `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `google_client_secret` | `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `session_secret_key` | `SM_SESSION_SECRET_KEY` | Cookie signing key |
| `debug` | Code default | Debug mode flag |
| `host` | Code default | Server bind address |
| `port` | Code default | Server port |

See the [Webapp Setup Guide](../guides/webapp_setup.md) for detailed Google OAuth configuration.

## Environment Loading

Environment variables are loaded by `shelf_mind.params.load_env.load_env()` from `~/cred/shelf-mind/.env` using `python-dotenv`. This is called during webapp startup.

## Path Resolution

`shelf_mind.params.shelf_mind_paths.ShelfMindPaths` resolves project-relative paths:

```python
from shelf_mind.params.shelf_mind_paths import ShelfMindPaths

paths = ShelfMindPaths()
paths.data_dir    # -> <project_root>/data
paths.static_dir  # -> <project_root>/static
```
