FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -s /bin/bash -m appuser

COPY requirements.txt* backend/requirements.txt* /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /tmp/src
RUN if [ -d /tmp/src/backend/app ]; then \
        mv /tmp/src/backend/app /app/backend/app; \
    else \
        mkdir -p /app/backend && mv /tmp/src/app /app/backend/app; \
    fi && \
    rm -rf /tmp/src && \
    mkdir -p /app/storage && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
