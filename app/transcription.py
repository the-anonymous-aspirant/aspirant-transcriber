import logging

import whisper
import numpy as np

from app.config import WHISPER_MODEL

logger = logging.getLogger(__name__)

_model = None


def load_model():
    global _model
    logger.info("Loading Whisper model '%s'...", WHISPER_MODEL)
    _model = whisper.load_model(WHISPER_MODEL)
    logger.info("Whisper model '%s' loaded.", WHISPER_MODEL)


def get_model():
    return _model


def transcribe_audio(file_path: str, language_hint: str | None = None) -> dict:
    """Transcribe an audio file and return result dict.

    Returns:
        dict with keys: text, language, language_confidence, duration
    """
    model = get_model()
    if model is None:
        raise RuntimeError("Whisper model not loaded")

    # Load audio and get duration
    audio = whisper.load_audio(file_path)
    duration = len(audio) / whisper.audio.SAMPLE_RATE

    options = {}
    if language_hint:
        options["language"] = language_hint

    result = model.transcribe(audio, **options)

    # Extract language detection confidence from the model
    # Whisper detects language from the first 30 seconds
    mel = whisper.log_mel_spectrogram(
        whisper.pad_or_trim(audio), n_mels=model.dims.n_mels
    ).to(model.device)
    _, probs = model.detect_language(mel)
    detected_language = result.get("language", "unknown")
    language_confidence = float(probs.get(detected_language, 0.0))

    return {
        "text": result["text"].strip(),
        "language": detected_language,
        "language_confidence": language_confidence,
        "duration": round(duration, 2),
    }
