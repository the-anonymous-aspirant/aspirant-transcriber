# Design Decisions

## Whisper Base Model

**Decision:** Use the `base` model as the default.

**Rationale:** The `base` model (~140 MB) provides a good balance between transcription accuracy and resource consumption. It runs comfortably in a 2 GB container. The `tiny` model is faster but significantly less accurate, while `small`/`medium`/`large` require more memory and CPU time without a proportional improvement for typical voice message lengths (under 5 minutes). The model can be changed via the `WHISPER_MODEL` environment variable without code changes.

## Local Inference (No External API)

**Decision:** Run Whisper locally inside the container instead of calling the OpenAI transcription API.

**Rationale:** Local inference avoids per-request API costs, eliminates network latency and external dependencies, keeps audio data on-premises (no third-party processing), and provides deterministic behavior. The tradeoff is higher container resource requirements (~1 GB RAM for the base model) and slower cold starts (model loading at startup).

## UUID Primary Keys

**Decision:** Use UUID v4 as primary keys for voice messages.

**Rationale:** UUIDs prevent enumeration attacks (sequential IDs leak information about volume), allow client-side ID generation, and avoid coordination issues if the service is ever scaled horizontally. The slight storage and index overhead compared to integer IDs is negligible for this use case.

## Background Transcription with Semaphore

**Decision:** Use FastAPI BackgroundTasks with a threading semaphore (max 1 concurrent) instead of a task queue (Celery, Redis, etc.).

**Rationale:** A single-threaded semaphore is the simplest approach that prevents memory exhaustion from concurrent Whisper inference. The Whisper model consumes significant memory per transcription, and running multiple in parallel would exceed container limits. FastAPI BackgroundTasks avoids the operational complexity of running a separate worker process and message broker. If throughput becomes a bottleneck, this can be replaced with a proper task queue later.

## SQLAlchemy with Auto-Create Tables

**Decision:** Use `Base.metadata.create_all()` at startup instead of a migration tool (Alembic).

**Rationale:** The service owns a single table (`voice_messages`) with a stable schema. Auto-creation simplifies deployment (no migration step needed) and is idempotent. If the schema evolves significantly, Alembic can be introduced later. The `create_all()` call is a no-op if tables already exist.

## File Storage on Disk

**Decision:** Store audio files on a Docker volume (`/data/audio`) rather than in the database or object storage.

**Rationale:** Audio files (up to 25 MB each) are too large for efficient database storage. Local disk via a Docker volume is the simplest option that provides persistence across container restarts. The file path is stored in the database for retrieval. If the service needs to scale across multiple hosts, this can be migrated to S3 or similar object storage.

## Monorepo Extraction

**Decision:** Extract the transcriber from the aspirant-online monorepo into its own repository.

**Rationale:** The transcriber is an independent service with its own Dockerfile, dependencies, and test suite. A separate repository enables independent CI/CD pipelines, clearer ownership, and simpler dependency management. The service communicates with other components only through the shared PostgreSQL database, making extraction straightforward.
