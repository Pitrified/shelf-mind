# User Guide

ShelfMind exposes a REST API for managing your household objects.
This guide covers the three core systems and how to interact with them.

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Location** | A named place in a hierarchy (e.g. Home > Kitchen > Drawer) |
| **Thing** | A household object with auto-enriched metadata |
| **Placement** | A record that a Thing is (or was) at a Location |
| **Search** | Find Things by text query or image, using vector similarity |

## Workflow Overview

```
1. Create a location hierarchy
2. Register things (metadata auto-generated)
3. Place things at locations
4. Search by text or image to find them
```

## API Base URL

All domain endpoints live under `/api/v1/`. When running locally:

```
http://localhost:8000/api/v1/
```

Interactive API docs (Swagger UI) are available at:

```
http://localhost:8000/docs
```

## Sections

- [Locations](locations.md) - Create and manage your location hierarchy
- [Things](things.md) - Register, update, and retrieve household objects
- [Search](search.md) - Find things by text query or image
