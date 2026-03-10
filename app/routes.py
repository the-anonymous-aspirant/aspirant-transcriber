import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    AUDIO_STORAGE_PATH,
    MAX_FILE_SIZE,
    WHISPER_MODEL,
)
from app.database import get_db
from app.models import VoiceMessage
from app.schemas import (
    HealthResponse,
    UploadResponse,
    VoiceMessageListResponse,
    VoiceMessageResponse,
)
from app.tasks import process_transcription
from app.transcription import get_model


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    checks = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception:
        checks["database"] = "disconnected"

    model = get_model()
    checks["whisper_model"] = "loaded" if model is not None else "not_loaded"

    all_ok = all(v in ("connected", "loaded", "available") for v in checks.values())
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        service="transcriber",
        version="1.0.0",
        checks=checks,
    )


@router.post("/voice-messages", response_model=UploadResponse, status_code=202)
async def upload_voice_message(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language_hint: str | None = Query(None, max_length=10),
    db: Session = Depends(get_db),
):
    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return _error(
            400, "validation_error",
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Validate MIME type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        return _error(
            400, "validation_error",
            f"Unsupported MIME type '{file.content_type}'.",
        )

    # Read file and check size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        return _error(
            400, "validation_error",
            f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    # Save to disk
    message_id = uuid.uuid4()
    stored_filename = f"{message_id}{ext}"
    storage_dir = Path(AUDIO_STORAGE_PATH)
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / stored_filename

    with open(file_path, "wb") as f:
        f.write(contents)

    # Create DB record
    msg = VoiceMessage(
        id=message_id,
        filename=stored_filename,
        original_filename=file.filename or "unknown",
        file_path=str(file_path),
        file_size_bytes=len(contents),
        mime_type=file.content_type or "application/octet-stream",
        status="pending",
        language_hint=language_hint,
        whisper_model=WHISPER_MODEL,
    )
    db.add(msg)
    db.commit()

    # Queue background transcription
    background_tasks.add_task(process_transcription, str(message_id))

    return UploadResponse(
        id=message_id,
        status="pending",
        message="Audio uploaded. Transcription queued.",
    )


@router.get("/voice-messages", response_model=VoiceMessageListResponse)
def list_voice_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    language: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(VoiceMessage)

    if status:
        query = query.filter(VoiceMessage.status == status)
    if language:
        query = query.filter(VoiceMessage.language == language)

    total = query.count()
    items = (
        query.order_by(VoiceMessage.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return VoiceMessageListResponse(
        items=[VoiceMessageResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/voice-messages/{message_id}", response_model=VoiceMessageResponse)
def get_voice_message(message_id: uuid.UUID, db: Session = Depends(get_db)):
    msg = db.query(VoiceMessage).filter(VoiceMessage.id == message_id).first()
    if msg is None:
        return _error(404, "not_found", "Voice message not found")
    return VoiceMessageResponse.model_validate(msg)


@router.delete("/voice-messages/{message_id}", status_code=204)
def delete_voice_message(message_id: uuid.UUID, db: Session = Depends(get_db)):
    msg = db.query(VoiceMessage).filter(VoiceMessage.id == message_id).first()
    if msg is None:
        return _error(404, "not_found", "Voice message not found")

    # Delete audio file
    try:
        if os.path.exists(msg.file_path):
            os.remove(msg.file_path)
    except OSError as e:
        logger.warning("Failed to delete audio file %s: %s", msg.file_path, e)

    db.delete(msg)
    db.commit()


@router.get("/voice-messages/{message_id}/audio")
def download_audio(message_id: uuid.UUID, db: Session = Depends(get_db)):
    msg = db.query(VoiceMessage).filter(VoiceMessage.id == message_id).first()
    if msg is None:
        return _error(404, "not_found", "Voice message not found")

    if not os.path.exists(msg.file_path):
        return _error(404, "not_found", "Audio file not found on disk")

    return FileResponse(
        path=msg.file_path,
        media_type=msg.mime_type,
        filename=msg.original_filename,
    )


@router.post("/voice-messages/{message_id}/retry", response_model=UploadResponse, status_code=202)
def retry_transcription(
    message_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    msg = db.query(VoiceMessage).filter(VoiceMessage.id == message_id).first()
    if msg is None:
        return _error(404, "not_found", "Voice message not found")

    if msg.status not in ("failed", "completed"):
        return _error(
            400, "validation_error",
            f"Cannot retry message with status '{msg.status}'. Only 'failed' or 'completed' messages can be retried.",
        )

    msg.status = "pending"
    msg.error_message = None
    msg.retry_count += 1
    msg.updated_at = datetime.now(timezone.utc)
    msg.completed_at = None
    msg.transcription = None
    msg.processing_time_seconds = None
    db.commit()

    background_tasks.add_task(process_transcription, str(message_id))

    return UploadResponse(
        id=message_id,
        status="pending",
        message="Transcription retry queued.",
    )
