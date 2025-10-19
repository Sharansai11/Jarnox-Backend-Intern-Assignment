FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (optional, keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend /app/backend
COPY frontend /app/frontend

# Expose API
EXPOSE 8000

# Start FastAPI (serves frontend at "/")
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]


