FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ripgrep curl && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash fastcode

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN mkdir -p /app/data && chown -R fastcode:fastcode /app/data

USER fastcode

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
