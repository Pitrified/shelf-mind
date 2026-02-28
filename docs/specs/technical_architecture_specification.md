# ShelfMind -- Technical Architecture Specification (Implementation Grade)

Date: 2026-02-28

------------------------------------------------------------------------

# 1. Architecture Style

Pattern: - Layered DDD - Dependency Injection container - Repository
abstraction - Strategy pattern for vision - Open/Closed principle
enforced

------------------------------------------------------------------------

# 2. Database Schema (SQLModel)

## Location Table

-   id: UUID (PK)
-   name: str (indexed)
-   parent_id: UUID (FK nullable)
-   path: str (indexed)
-   created_at: datetime

Index: - idx_location_path

------------------------------------------------------------------------

## Thing Table

-   id: UUID (PK)
-   name: str (indexed)
-   description: str
-   metadata_json: JSON
-   created_at
-   updated_at

Index: - idx_thing_name

------------------------------------------------------------------------

## Placement Table

-   id (PK)
-   thing_id (FK)
-   location_id (FK)
-   placed_at

Index: - idx_thing_location

------------------------------------------------------------------------

# 3. Qdrant Collection Configuration

Collection name: things

Vector fields: - text_vector (dim=384) - image_vector (dim=512)

Distance metric: - Cosine

Payload indexed fields: - thing_id - name - category - tags -
location_path

------------------------------------------------------------------------

# 4. Interfaces

## VectorRepository

Methods: - upsert_text_vector() - upsert_image_vector() -
search_text() - search_image() - delete_vectors()

------------------------------------------------------------------------

## TextEmbeddingProvider

Methods: - embed(text: str) -\> list\[float\]

------------------------------------------------------------------------

## VisionStrategy

Methods: - embed(image_array) -\> list\[list\[float\]\]

------------------------------------------------------------------------

## MetadataEnricher

Methods: - enrich(name: str, description: str \| None) -\>
MetadataSchema

------------------------------------------------------------------------

## SearchRanker

Methods: - rank(results, query_context) -\> ordered results

------------------------------------------------------------------------

# 5. Dependency Injection

Container responsibilities: - Singleton embedding providers - Singleton
Qdrant client - Config injection - Lazy model loading

------------------------------------------------------------------------

# 6. Settings (Pydantic BaseSettings)

Fields: - DATABASE_URL - QDRANT_URL - TEXT_MODEL_NAME -
IMAGE_MODEL_NAME - RANK_ALPHA - RANK_BETA - RANK_GAMMA

------------------------------------------------------------------------

# 7. Vision Pipeline Details

Image preprocessing: - Convert to RGB - Resize max 512px - Normalize

GPU fallback: - If CUDA unavailable → CPU mode

------------------------------------------------------------------------

# 8. Search Scoring Implementation

score = alpha \* vector_score + beta \* metadata_overlap + gamma \*
location_bonus

Metadata overlap: - Jaccard similarity between tags

Location bonus: - +0.1 if direct match - +0.05 if ancestor match

------------------------------------------------------------------------

# 9. Project Structure

src/shelfmind/

    domain/
        entities/
        repositories/
        schemas/

    application/
        commands/
        queries/
        services/

    infrastructure/
        db/
        vector/
        embeddings/
        vision/
        metadata/

    api/
        routers/

    core/
        config.py
        container.py

------------------------------------------------------------------------

# 10. Deployment

Local execution:

docker-compose: - qdrant - app

Uvicorn command: uvicorn shelfmind.main:app --reload

------------------------------------------------------------------------

End of Technical Architecture Specification (Implementation Grade)
