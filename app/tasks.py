import logging
import threading
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import VoiceMessage
from app.transcription import transcribe_audio

logger = logging.getLogger(__name__)

_semaphore = threading.Semaphore(1)


def process_transcription(message_id: str):
    """Background task: transcribe audio for a given voice message ID."""
    acquired = _semaphore.acquire(timeout=300)
    if not acquired:
        logger.error("Timed out waiting for transcription semaphore for %s", message_id)
        _mark_failed(message_id, "Timed out waiting for processing slot")
        return

    try:
        _run_transcription(message_id)
    finally:
        _semaphore.release()


def _run_transcription(message_id: str):
    db: Session = SessionLocal()
    try:
        msg = db.query(VoiceMessage).filter(VoiceMessage.id == message_id).first()
        if msg is None:
            logger.error("Voice message %s not found", message_id)
            return

        msg.status = "processing"
        msg.updated_at = datetime.now(timezone.utc)
        db.commit()

        start = time.monotonic()
        result = transcribe_audio(msg.file_path, msg.language_hint)
        elapsed = round(time.monotonic() - start, 2)

        msg.transcription = result["text"]
        msg.language = result["language"]
        msg.language_confidence = result["language_confidence"]
        msg.duration_seconds = result["duration"]
        msg.whisper_model = msg.whisper_model  # already set at upload
        msg.processing_time_seconds = elapsed
        msg.status = "completed"
        msg.completed_at = datetime.now(timezone.utc)
        msg.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            "Transcription complete for %s (%.1fs audio, %.1fs processing)",
            message_id,
            result["duration"],
            elapsed,
        )
    except Exception as e:
        logger.exception("Transcription failed for %s", message_id)
        db.rollback()
        _mark_failed_in_session(db, message_id, str(e))
    finally:
        db.close()


def _mark_failed(message_id: str, error: str):
    db = SessionLocal()
    try:
        _mark_failed_in_session(db, message_id, error)
    finally:
        db.close()


def _mark_failed_in_session(db: Session, message_id: str, error: str):
    msg = db.query(VoiceMessage).filter(VoiceMessage.id == message_id).first()
    if msg:
        msg.status = "failed"
        msg.error_message = error[:2000]
        msg.updated_at = datetime.now(timezone.utc)
        db.commit()
