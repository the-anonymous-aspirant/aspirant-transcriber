# aspirant-transcriber

Voice-to-text transcription microservice using OpenAI Whisper with local inference. Receives audio files via a REST API, transcribes them in the background, and exposes transcription results with metadata.

## Quick Start

```bash
# Build the Docker image
docker build -t aspirant-transcriber .

# Start PostgreSQL (if not already running)
docker run -d --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=aspirant_online_db \
  -p 5432:5432 \
  postgres:16-alpine

# Run the transcriber
docker run -d --name transcriber \
  -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_NAME=aspirant_online_db \
  -v audiodata:/data/audio \
  aspirant-transcriber

# Verify it's running
curl http://localhost:8000/health | jq
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `POST` | `/voice-messages` | Upload audio file for transcription |
| `GET` | `/voice-messages` | List voice messages (paginated) |
| `GET` | `/voice-messages/:id` | Get voice message details and transcription |
| `GET` | `/voice-messages/:id/audio` | Download original audio file |
| `DELETE` | `/voice-messages/:id` | Delete voice message and audio |
| `POST` | `/voice-messages/:id/retry` | Retry failed/completed transcription |

### Upload Example

```bash
curl -X POST http://localhost:8000/voice-messages \
  -F "file=@recording.wav" \
  -F "language_hint=en"
```

Response (202 Accepted):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Audio uploaded. Transcription queued."
}
```

### Retrieve Transcription

```bash
curl http://localhost:8000/voice-messages/550e8400-e29b-41d4-a716-446655440000 | jq
```

Response (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "transcription": "Hello, this is a test recording.",
  "language": "en",
  "language_confidence": 0.98,
  "duration_seconds": 3.21,
  "processing_time_seconds": 1.85,
  ...
}
```

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│            FastAPI (uvicorn :8000)           │
│                                             │
│  Routes ──> Tasks ──> Whisper (local)       │
│    │         │ (semaphore, max 1 concurrent) │
│    │         │                               │
└────┼─────────┼───────────────────────────────┘
     │         │
     ▼         ▼
 PostgreSQL   Audio Volume
  :5432       /data/audio
```

- **FastAPI** handles HTTP requests and file uploads
- **Background tasks** process transcriptions asynchronously (202 Accepted pattern)
- **OpenAI Whisper** runs locally for inference (no external API calls)
- **Threading semaphore** limits to 1 concurrent transcription to prevent memory exhaustion
- **PostgreSQL** stores voice message metadata and transcription results
- **Audio volume** persists uploaded audio files

## Supported Audio Formats

WAV, MP3, M4A, OGG, WEBM, FLAC (max 25 MB)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `postgres` | PostgreSQL hostname |
| `DB_USER` | `postgres` | PostgreSQL username |
| `DB_PASSWORD` | `postgres` | PostgreSQL password |
| `DB_NAME` | `aspirant_online_db` | Database name |
| `AUDIO_STORAGE_PATH` | `/data/audio` | Audio file storage directory |
| `WHISPER_MODEL` | `base` | Whisper model size (tiny/base/small/medium/large) |

## Testing

```bash
docker build -t transcriber-test .
docker run --rm --network host \
  -e DB_HOST=localhost \
  -e DB_USER=test_user \
  -e DB_PASSWORD=test_password \
  -e DB_NAME=test_db \
  -v "$(pwd)/tests:/app/tests" \
  transcriber-test pytest tests/ -v
```

## Documentation

- [SPEC.md](docs/SPEC.md) -- Full API specification and database schema
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) -- System architecture and module responsibilities
- [OPERATIONS.md](docs/OPERATIONS.md) -- Setup, running, testing, and debugging
- [DECISIONS.md](docs/DECISIONS.md) -- Key design decisions and rationale
- [CHANGELOG.md](docs/CHANGELOG.md) -- Release history

## Conventions

This service follows [aspirant-meta conventions](https://github.com/the-anonymous-aspirant/aspirant-meta/blob/main/CONVENTIONS.md).
