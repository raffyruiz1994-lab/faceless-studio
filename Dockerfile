FROM python:3.12-slim

# ffmpeg + fonts for subtitle rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY static/ ./static/

RUN mkdir -p jobs && chmod 700 jobs

EXPOSE 8000

# single worker: video rendering is CPU-heavy
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
