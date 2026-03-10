import uuid
from datetime import datetime

from pydantic import BaseModel


class VoiceMessageResponse(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    duration_seconds: float | None
    status: str
    transcription: str | None
    language_hint: str | None
    language: str | None
    language_confidence: float | None
    whisper_model: str | None
    processing_time_seconds: float | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class VoiceMessageListResponse(BaseModel):
    items: list[VoiceMessageResponse]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    checks: dict[str, str]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class UploadResponse(BaseModel):
    id: uuid.UUID
    status: str
    message: str
