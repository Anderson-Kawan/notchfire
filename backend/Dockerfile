FROM python:3.14-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /build/requirements.txt
RUN python -m pip wheel --wheel-dir /build/wheels -r /build/requirements.txt

FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=notchfire_project.settings \
    DJANGO_STATIC_ROOT=/app/staticfiles \
    DJANGO_MEDIA_ROOT=/app/media \
    DJANGO_LOG_DIR=/app/logs

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system django \
    && adduser --system --ingroup django --home /app django

COPY backend/requirements.txt /app/requirements.txt
COPY --from=builder /build/wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels -r /app/requirements.txt \
    && rm -rf /wheels

COPY backend/ /app/

RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R django:django /app

USER django

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn"]
