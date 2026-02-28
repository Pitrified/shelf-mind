# Contributing

Thank you for your interest in contributing to ShelfMind!

## Development Setup

1. Fork and clone the repository
2. Install dependencies: `uv sync --extra webapp --group dev`
3. Start Qdrant: `docker run -d --name qdrant -p 6333:6333 qdrant/qdrant`
4. Set environment variables (see [Getting Started](getting-started.md))
5. Install pre-commit hooks: `uv run pre-commit install`

## Code Style

This project uses:

- **Ruff** for linting and formatting (ALL rules enabled, see `ruff.toml`)
- **Pyright** for type checking (`src/` and `tests/`)
- **Pre-commit** hooks for automated checks
- **Google-style docstrings** on all public interfaces

### Style Guidelines

```python
# Good: Clear typing, early returns, descriptive names, msg variable
from loguru import logger as lg

def fetch_entity(table: str, entity_id: str | None) -> dict:
    if entity_id is None:
        msg = "entity_id required"
        raise ValueError(msg)

    lg.info(f"Fetching {entity_id} from {table}")
    return {"id": entity_id, "table": table}
```

- Never use em dashes (`---` or Unicode `--`). Use hyphens or rewrite.
- Error messages go in a `msg` variable, then `raise SomeError(msg)`.
- Use `from loguru import logger as lg` for logging.

## Verification

Before submitting any changes, run the full verification suite:

```bash
uv run pytest && uv run ruff check . && uv run pyright
```

All three must pass cleanly.

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear, focused commits
3. Run the full verification suite (see above)
4. Update documentation if needed (see `docs/`)
5. Submit a pull request

## Commit Messages

Use conventional commit style:

```
type(scope): description

feat(things): add batch registration endpoint
fix(search): handle empty query gracefully
docs(readme): update installation instructions
test(services): add ThingService unit tests
```

## Testing

- Write tests for new functionality
- Place tests in `tests/` mirroring the `src/shelf_mind/` structure
- Use descriptive test names: `test_function_does_expected_behavior`
- See [Next Steps](next-steps.md) for current testing gaps

```bash
uv run pytest                       # All tests
uv run pytest tests/application/    # Service layer only
uv run pytest tests/webapp/         # Webapp layer only
uv run pytest -v                    # Verbose output
```

## Project Structure

See the [Architecture Guide](dev/architecture.md) for the full project structure and layer responsibilities.

## Documentation

- Docs live in `docs/` and are built with MkDocs
- Update docs when adding new features
- Include usage examples in docstrings
- Build and preview locally: `uv run mkdocs serve`

## Questions?

Open an issue for any questions or concerns.
