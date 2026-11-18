
FROM python:3.13-slim

# Python configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies: Tesseract OCR and OpenMP
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install -r requirements.txt

# Copy backend application
COPY backend/ ./backend/

ENV PYTHONPATH=/app/backend

EXPOSE 8000

# Start FastAPI
CMD ["sh", "-c", "python -m uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8000}"]

