# ShelfMind -- Functional Specification (Implementation Grade)

Date: 2026-02-28

------------------------------------------------------------------------

# 1. Product Vision

ShelfMind is a fully local-first household object registry and
multimodal retrieval system. It enables structured spatial modeling and
hybrid (text + metadata + vision) search.

System guarantees: - No cloud dependencies - Deterministic metadata
pipeline - Extensible retrieval strategies - GPU-aware execution (≤ 6GB
VRAM)

------------------------------------------------------------------------

# 2. Functional Scope

## 2.1 Location Management

### Requirements

-   Unlimited hierarchical nesting.
-   CRUD operations.
-   Materialized path auto-maintained.
-   Prevent deletion if children exist.
-   Prevent deletion if Things assigned (unless forced).

### Validation Rules

-   Unique sibling names per parent.
-   Path auto-updated on rename/move.
-   Root location immutable.

------------------------------------------------------------------------

## 2.2 Thing Registration

### Required Fields

-   name (string, 1--120 chars)

### Optional Fields

-   description
-   custom metadata fields

### System Actions on Create

1.  Deterministic metadata extraction.
2.  Metadata schema validation.
3.  Persist Thing in SQL.
4.  Generate text embedding.
5.  Store vector in Qdrant.

### Edit Behavior

-   Metadata regeneration optional.
-   Re-index vectors on change.

------------------------------------------------------------------------

## 2.3 Placement Management

-   One active placement per Thing.
-   Historical placements stored (future).
-   Moving a Thing creates new Placement record.

------------------------------------------------------------------------

## 2.4 Search -- Text

Input: - q: string - optional location filter - limit (default 10)

Pipeline: 1. Embed query. 2. Vector similarity search. 3. Payload filter
(location_path prefix). 4. Ranking layer. 5. Return DTO with confidence
score.

Latency target: \< 300ms for ≤ 5k Things.

------------------------------------------------------------------------

## 2.5 Search -- Vision

Input: - Image snapshot via browser.

Pipeline: 1. Resize (max 512px). 2. VisionStrategy.embed() 3. Vector
search against image_vector. 4. Ranked result return.

Latency target: \< 800ms on GPU.

------------------------------------------------------------------------

# 3. Metadata Schema (Strict)

Base schema (Pydantic):

-   category: str
-   subtype: str \| None
-   tags: list\[str\]
-   material: str \| None
-   room_hint: str \| None
-   usage_context: list\[str\]
-   custom: dict\[str, str\]

Validation: - tags lowercased - no duplicate tags - max 30 tags

------------------------------------------------------------------------

# 4. Error Handling

-   All validation errors → HTTP 422
-   Model loading failures → HTTP 503
-   Vector DB unavailable → HTTP 503
-   Corrupt image → HTTP 400

------------------------------------------------------------------------

# 5. Non-Functional Requirements

-   Fully offline capable
-   GPU optional but supported
-   Deterministic fallback if GPU unavailable
-   Clear extension points

------------------------------------------------------------------------

# 6. Phase Execution Plan

Phase 1: - Location + Thing + Text search

Phase 2: - Vision integration

Phase 3: - Hybrid ranking + detection

------------------------------------------------------------------------

End of Functional Specification (Implementation Grade)
