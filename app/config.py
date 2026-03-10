import os


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://{user}:{password}@{host}/{name}".format(
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
        host=os.environ.get("DB_HOST", "postgres"),
        name=os.environ.get("DB_NAME", "aspirant_online_db"),
    ),
)

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
AUDIO_STORAGE_PATH = os.environ.get("AUDIO_STORAGE_PATH", "/data/audio")
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 25 * 1024 * 1024))  # 25 MB

ALLOWED_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
    "audio/x-flac",
}

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac"}
