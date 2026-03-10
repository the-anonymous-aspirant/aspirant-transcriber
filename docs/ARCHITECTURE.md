# Transcriber Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Docker Container                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                    FastAPI (uvicorn)                    │  │
│  │                       :8000                            │  │
│  │                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │  │
│  │  │   Routes     │  │   Schemas    │  │   Config    │  │  │
│  │  │  (routes.py) │  │ (schemas.py) │  │ (config.py) │  │  │
│  │  └──────┬───────┘  └──────────────┘  └─────────────┘  │  │
│  │         │                                              │  │
│  │         │  POST /voice-messages                        │  │
│  │         │  triggers background task                    │  │
│  │         ▼                                              │  │
│  │  ┌──────────────┐                                      │  │
│  │  │    Tasks     │                                      │  │
│  │  │  (tasks.py)  │                                      │  │
│  │  │              │                                      │  │
│  │  │  semaphore   │  max 1 concurrent transcription      │  │
│  │  └──────┬───────┘                                      │  │
│  │         │                                              │  │
│  │         ▼                                              │  │
│  │  ┌────────────────────┐                                │  │
│  │  │   Transcription    │                                │  │
│  │  │ (transcription.py) │                                │  │
│  │  │                    │                                │  │
│  │  │  OpenAI Whisper    │  local inference, no API calls │  │
│  │  │  (base model)      │  ~140 MB in memory             │  │
│  │  └────────────────────┘                                │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────┬──────────────────────────┬────────────────────┘
               │                          │
               ▼                          ▼
    ┌────────────────────┐     ┌────────────────────┐
    │    PostgreSQL       │     │   Audio Volume      │
    │    :5432            │     │   /data/audio       │
    │                     │     │                     │
    │  voice_messages     │     │  {uuid}.wav         │
    │  table              │     │  {uuid}.mp3         │
    │                     │     │  {uuid}.m4a         │
    └────────────────────┘     └────────────────────┘
```

## Module Responsibilities

### app/main.py
- Application entry point
- FastAPI lifespan: creates database tables and loads Whisper model at startup
- Includes the router

### app/config.py
- Reads environment variables
- Defines constants: database URL, Whisper model name, storage path, file size limits
- Defines allowed MIME types and file extensions

### app/database.py
- SQLAlchemy engine and session factory
- `Base` declarative base for models
- `get_db()` dependency for request-scoped sessions

### app/models.py
- `VoiceMessage` SQLAlchemy model
- Maps to `voice_messages` table
- UUID primary key, status tracking, transcription results, timestamps

### app/schemas.py
- Pydantic models for request/response validation
- `VoiceMessageResponse`, `VoiceMessageListResponse`, `HealthResponse`, `UploadResponse`, `ErrorResponse`

### app/routes.py
- All HTTP endpoint handlers
- File upload validation (extension, MIME type, size)
- CRUD operations on voice messages
- Triggers background transcription tasks

### app/tasks.py
- Background task runner for transcription
- Threading semaphore (max 1 concurrent) to prevent memory exhaustion
- Status management: pending -> processing -> completed/failed
- Error handling with failure recording

### app/transcription.py
- Whisper model loading and caching (singleton)
- Audio transcription with language detection
- Returns text, detected language, confidence score, duration

## Request Flow

### Upload + Transcribe

```
Client                    FastAPI                    Tasks                Whisper              PostgreSQL
  │                         │                         │                    │                      │
  │  POST /voice-messages   │                         │                    │                      │
  │ ───────────────────────>│                         │                    │                      │
  │                         │  validate file          │                    │                      │
  │                         │  save to /data/audio    │                    │                      │
  │                         │  INSERT voice_messages ─────────────────────────────────────────────>│
  │                         │                         │                    │                      │
  │                         │  add_task()             │                    │                      │
  │   202 {id, "pending"}   │ ──────────────────────> │                    │                      │
  │ <───────────────────────│                         │                    │                      │
  │                         │                         │                    │                      │
  │                         │                    (background)              │                      │
  │                         │                         │  acquire semaphore │                      │
  │                         │                         │  UPDATE status = "processing" ───────────>│
  │                         │                         │                    │                      │
  │                         │                         │  transcribe()      │                      │
  │                         │                         │ ──────────────────>│                      │
  │                         │                         │   {text, lang}     │                      │
  │                         │                         │ <──────────────────│                      │
  │                         │                         │                    │                      │
  │                         │                         │  UPDATE status = "completed" ────────────>│
  │                         │                         │  release semaphore │                      │
```

### Retrieve Results

```
Client                    FastAPI                                        PostgreSQL
  │                         │                                                │
  │  GET /voice-messages/id │                                                │
  │ ───────────────────────>│  SELECT * FROM voice_messages WHERE id = ...   │
  │                         │ ──────────────────────────────────────────────>│
  │                         │                                                │
  │   200 {transcription..} │ <──────────────────────────────────────────────│
  │ <───────────────────────│                                                │
```
