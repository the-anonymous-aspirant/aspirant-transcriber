# Voice Transcription Service Specification

A REST microservice that receives audio files, transcribes them using OpenAI Whisper (local inference), and exposes results with metadata.

This service follows the [aspirant-meta conventions](https://github.com/the-anonymous-aspirant/aspirant-meta/blob/main/CONVENTIONS.md) for API contract (URL patterns, error responses, pagination, health endpoint), logging, testing, and Docker standards. This spec documents only what is specific to the transcriber.

## Architecture

The transcriber runs as a standalone FastAPI container alongside the existing Go backend and Vue.js frontend, sharing the same PostgreSQL instance via Docker Compose networking.

```
                  ┌─────────────┐
                  │   Client    │
                  │  (Vue.js)   │
                  │   :80       │
                  └─────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
  ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼───────────┐
  │   Server    │ │ Transcriber│ │   PostgreSQL    │
  │   (Go/Gin)  │ │ (FastAPI)  │ │                 │
  │   :8081     │ │   :8082    │ │   :5432         │
  └──────┬──────┘ └─────┬──────┘ └────────────────┘
         │              │              ▲
         └──────────────┴──────────────┘
               (shared database)
```

## API Endpoints

### Health Check

```
GET /health
```

Returns service status following the [standard health endpoint contract](https://github.com/the-anonymous-aspirant/aspirant-meta/blob/main/CONVENTIONS.md#health-endpoint).

**Response:**
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

### Upload Voice Message

```
POST /voice-messages
Content-Type: multipart/form-data
```

**Parameters:**
- `file` (required) - Audio file (WAV, MP3, M4A, OGG, WEBM, FLAC; max 25 MB)
- `language_hint` (optional) - ISO language code hint for Whisper (e.g., `en`, `sv`)

**Response (202 Accepted):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Audio uploaded. Transcription queued."
}
```

### List Voice Messages

```
GET /voice-messages?page=1&page_size=20&status=completed&language=en
```

All query parameters are optional. Returns paginated results ordered by creation date (newest first).

### Get Voice Message

```
GET /voice-messages/{id}
```

Returns full metadata and transcription for a single message.

### Delete Voice Message

```
DELETE /voice-messages/{id}
```

Deletes the database record and the stored audio file. Returns 204 No Content.

### Download Audio

```
GET /voice-messages/{id}/audio
```

Returns the original audio file with correct MIME type and filename.

### Retry Transcription

```
POST /voice-messages/{id}/retry
```

Re-queues a failed or completed message for transcription. Increments `retry_count`.

## Database Schema

**Table: `voice_messages`**

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| filename | VARCHAR(255) | Stored filename (UUID + extension) |
| original_filename | VARCHAR(255) | User's original filename |
| file_path | VARCHAR(512) | Absolute path on disk |
| file_size_bytes | INTEGER | File size |
| mime_type | VARCHAR(100) | MIME type |
| duration_seconds | FLOAT | Audio duration (set after processing) |
| status | VARCHAR(20) | pending / processing / completed / failed |
| transcription | TEXT | Transcribed text |
| language_hint | VARCHAR(10) | User-provided language hint |
| language | VARCHAR(10) | Detected language code |
| language_confidence | FLOAT | Detection confidence (0-1) |
| whisper_model | VARCHAR(50) | Model used (e.g., "base") |
| processing_time_seconds | FLOAT | Wall-clock processing time |
| error_message | TEXT | Error details (if failed) |
| retry_count | INTEGER | Number of retry attempts |
| created_at | TIMESTAMPTZ | Upload timestamp |
| updated_at | TIMESTAMPTZ | Last modification |
| completed_at | TIMESTAMPTZ | Transcription completion time |

**Indexes:** status, created_at (DESC), language

## Status Transitions

```
           upload
             │
             ▼
         ┌────────┐
         │pending  │
         └───┬─────┘
             │  background task picks up
             ▼
       ┌───────────┐
       │processing  │
       └──┬─────┬───┘
          │     │
   success│     │failure
          ▼     ▼
   ┌──────────┐ ┌──────┐
   │completed │ │failed │
   └────┬─────┘ └──┬───┘
        │          │
        └────┬─────┘
             │  POST /retry
             ▼
         ┌────────┐
         │pending  │  (retry_count incremented)
         └────────┘
```

## Audio Formats

Supported file extensions: `.wav`, `.mp3`, `.m4a`, `.ogg`, `.webm`, `.flac`

Supported MIME types: `audio/wav`, `audio/x-wav`, `audio/mpeg`, `audio/mp3`, `audio/mp4`, `audio/x-m4a`, `audio/m4a`, `audio/ogg`, `audio/webm`, `audio/flac`, `audio/x-flac`

Maximum file size: 25 MB

## Whisper Model

The service uses OpenAI Whisper for local inference (no API calls to OpenAI). The model is pre-downloaded during Docker image build.

Available model sizes: `tiny`, `base`, `small`, `medium`, `large`

Default: `base` (~140 MB, good balance of speed and accuracy)

The model is loaded once at startup and shared across all requests. A threading semaphore limits concurrent transcriptions to 1 to prevent memory exhaustion.

## Processing Pipeline

1. Client uploads audio file via `POST /voice-messages`
2. File is validated (extension, MIME type, size) and saved to the `audiodata` volume
3. Database record is created with status `pending`
4. A background task is queued (FastAPI BackgroundTasks)
5. A threading semaphore (max 1 concurrent) prevents memory exhaustion
6. Whisper transcribes the audio, detecting language and confidence
7. Results are saved to the database with status `completed`
8. On failure, status is set to `failed` with error details

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| DB_USER | postgres | PostgreSQL username |
| DB_PASSWORD | postgres | PostgreSQL password |
| DB_HOST | postgres | PostgreSQL hostname |
| DB_NAME | aspirant_online_db | Database name |
| DATABASE_URL | (built from above) | Full connection string (overrides individual vars) |
| WHISPER_MODEL | base | Whisper model size (tiny/base/small/medium/large) |
| AUDIO_STORAGE_PATH | /data/audio | Audio file storage directory |
| MAX_FILE_SIZE | 26214400 | Maximum upload size in bytes (25 MB) |

## Resource Requirements

- **RAM:** ~1 GB for the `base` model, 2 GB container limit
- **Disk:** Whisper model (~140 MB) + audio storage
- **CPU:** Transcription is CPU-bound; one file at a time via semaphore
- **Port:** 8082 (host) mapped to 8000 (container)
