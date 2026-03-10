import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routes import router
from app.transcription import load_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")

    load_model()

    yield

    logger.info("Shutting down.")


app = FastAPI(
    title="Voice Transcription Service",
    description="Receive voice messages, transcribe with Whisper, expose results via REST API.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
