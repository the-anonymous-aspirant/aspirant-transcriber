FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip "setuptools<78" wheel && \
    pip install --no-cache-dir --no-build-isolation -r requirements.txt

# Pre-download the Whisper base model during build
RUN python -c "import whisper; whisper.load_model('base')"

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
