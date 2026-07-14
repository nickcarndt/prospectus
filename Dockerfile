# Prospectus API — build from repo root
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Shared / retrieval / generation packages first (editable installs need sources)
COPY packages/shared /app/packages/shared
COPY packages/retrieval /app/packages/retrieval
COPY packages/generation /app/packages/generation
COPY services/api/requirements.txt /app/services/api/requirements.txt

RUN pip install --no-cache-dir -r /app/services/api/requirements.txt \
    && pip install --no-cache-dir \
        /app/packages/shared \
        /app/packages/retrieval \
        /app/packages/generation

COPY services/api /app/services/api

WORKDIR /app/services/api

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
