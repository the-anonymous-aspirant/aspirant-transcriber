# Transcriber Operations

## Prerequisites

- Docker (for containerized deployment)
- PostgreSQL 16+ (standalone or via Docker)
- Python 3.11+ (for local development only)

## Setup

### 1. Database

The transcriber requires a PostgreSQL database. Tables are created automatically on service startup.

```bash
# Start PostgreSQL via Docker (development)
docker run -d --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=aspirant_online_db \
  -p 5432:5432 \
  postgres:16-alpine
```

### 2. Build the Docker Image

```bash
docker build -t aspirant-transcriber .
```

The build pre-downloads the Whisper `base` model (~140 MB) so the first request does not incur download latency.

### 3. Run the Service

```bash
docker run -d --name transcriber \
  -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_NAME=aspirant_online_db \
  -v audiodata:/data/audio \
  aspirant-transcriber
```

## Running Tests

Tests require a running PostgreSQL instance.

```bash
# Option 1: Run tests in Docker (recommended)
docker build -t transcriber-test .
docker run --rm --network host \
  -e DB_HOST=localhost \
  -e DB_USER=test_user \
  -e DB_PASSWORD=test_password \
  -e DB_NAME=test_db \
  -v "$(pwd)/tests:/app/tests" \
  transcriber-test pytest tests/ -v

# Option 2: Run tests locally (requires PostgreSQL and Python dependencies)
DB_HOST=localhost DB_USER=postgres DB_PASSWORD=postgres DB_NAME=test_db \
  pytest tests/ -v
```

## Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DB_HOST=localhost
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_NAME=aspirant_online_db
export AUDIO_STORAGE_PATH=./audio_storage

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Debugging

### Health Check

```bash
curl http://localhost:8000/health | jq
```

Expected response when healthy:
```json
{
  "status": "ok",
  "service": "transcriber",
  "version": "1.0.0",
  "checks": {
    "database": "connected",
    "whisper_model": "loaded"
  }
}
```

If `status` is `"degraded"`, check the `checks` object:
- `database: "disconnected"` -- PostgreSQL is unreachable (check DB_HOST, credentials, network)
- `whisper_model: "not_loaded"` -- model failed to load at startup (check logs, memory)

### Common Issues

**Transcription stuck in "processing" status:**
- The service may have crashed mid-transcription. Check container logs.
- Use `POST /voice-messages/{id}/retry` to re-queue.

**Out of memory:**
- The Whisper `base` model needs ~1 GB RAM. Increase container memory limit or switch to `tiny` model via `WHISPER_MODEL=tiny`.

**Audio file not found on disk:**
- The audio volume may not be mounted correctly. Verify the `-v audiodata:/data/audio` flag.
- Check that `AUDIO_STORAGE_PATH` matches the volume mount path.

**Database connection refused:**
- Verify `DB_HOST` is reachable from the container.
- For Docker-to-host connections, use `host.docker.internal` (macOS/Windows) or `172.17.0.1` (Linux).

### Logs

```bash
# View container logs
docker logs transcriber

# Follow logs
docker logs -f transcriber
```

Log format: `2026-01-15T12:00:00Z [INFO] app.main: Creating database tables...`

Key log messages:
- `Creating database tables...` -- startup, table creation
- `Database tables ready.` -- tables created successfully
- `Loading Whisper model 'base'...` -- model loading started
- `Whisper model 'base' loaded.` -- model ready
- `Transcription complete for {id} (5.2s audio, 3.1s processing)` -- successful transcription
- `Transcription failed for {id}` -- failure with stack trace

### Database Inspection

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U postgres -d aspirant_online_db

# Check pending messages
SELECT id, status, created_at FROM voice_messages WHERE status = 'pending';

# Check failed messages
SELECT id, error_message, retry_count FROM voice_messages WHERE status = 'failed';

# Count by status
SELECT status, COUNT(*) FROM voice_messages GROUP BY status;
```
