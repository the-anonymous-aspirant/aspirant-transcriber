# aspirant-transcriber

## Service Description

Voice-to-text transcription microservice using OpenAI Whisper with local inference. Receives audio files via a REST API, transcribes them in the background using the Whisper model running on the local machine (no external API calls), and exposes transcription results with metadata.

Built with FastAPI and SQLAlchemy. Follows [aspirant-meta conventions](https://github.com/the-anonymous-aspirant/aspirant-meta/blob/main/CONVENTIONS.md) for API contract, error responses, pagination, health endpoint, logging, testing, and Docker standards.

## How to Run

Requires PostgreSQL. Run via Docker Compose or locally with a PostgreSQL instance available.

```bash
# Build and run with Docker
docker build -t aspirant-transcriber .
docker run -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_NAME=aspirant_online_db \
  -v audiodata:/data/audio \
  aspirant-transcriber
```

The service creates its database tables automatically on startup.

## How to Test

Tests require a running PostgreSQL database. The recommended approach is to run tests via Docker Compose to ensure the database dependency is available:

```bash
# Build the image
docker build -t transcriber-test .

# Run tests against a local PostgreSQL
docker run --rm --network host \
  -e DB_HOST=localhost \
  -e DB_USER=test_user \
  -e DB_PASSWORD=test_password \
  -e DB_NAME=test_db \
  -v "$(pwd)/tests:/app/tests" \
  transcriber-test pytest tests/ -v
```

## Port

- **8000** (container)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (database + Whisper model status) |
| POST | `/voice-messages` | Upload audio file for transcription (returns 202) |
| GET | `/voice-messages` | List voice messages (paginated, filterable) |
| GET | `/voice-messages/:id` | Get a single voice message with transcription |
| GET | `/voice-messages/:id/audio` | Download the original audio file |
| DELETE | `/voice-messages/:id` | Delete voice message and audio file |
| POST | `/voice-messages/:id/retry` | Retry a failed/completed transcription |

## Database Tables Owned

- **voice_messages** -- stores upload metadata, transcription results, and processing status

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `postgres` | PostgreSQL hostname |
| `DB_USER` | `postgres` | PostgreSQL username |
| `DB_PASSWORD` | `postgres` | PostgreSQL password |
| `DB_NAME` | `aspirant_online_db` | Database name |
| `DATABASE_URL` | (built from above) | Full connection string (overrides individual vars) |
| `AUDIO_STORAGE_PATH` | `/data/audio` | Directory for storing uploaded audio files |
| `WHISPER_MODEL` | `base` | Whisper model size (tiny/base/small/medium/large) |
| `MAX_FILE_SIZE` | `26214400` | Maximum upload size in bytes (25 MB) |

## Conventions

This service follows [aspirant-meta conventions](https://github.com/the-anonymous-aspirant/aspirant-meta/blob/main/CONVENTIONS.md).
