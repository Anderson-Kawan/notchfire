#!/bin/sh
set -eu

export POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_DB="${POSTGRES_DB:-notchfire}"
export POSTGRES_USER="${POSTGRES_USER:-notchfire}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
export GUNICORN_BIND="${GUNICORN_BIND:-0.0.0.0:8000}"
export GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
export GUNICORN_THREADS="${GUNICORN_THREADS:-2}"
export GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-60}"

wait_for_postgres() {
  echo "Aguardando PostgreSQL em ${POSTGRES_HOST}:${POSTGRES_PORT}..."

  until python <<'PY'
import os
import sys
import psycopg

database_url = os.environ.get("DATABASE_URL", "").strip()

try:
    if database_url:
        conn = psycopg.connect(database_url, connect_timeout=5)
    else:
        conn = psycopg.connect(
            host=os.environ["POSTGRES_HOST"],
            port=os.environ["POSTGRES_PORT"],
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ.get("POSTGRES_PASSWORD", ""),
            connect_timeout=5,
        )
    conn.close()
except Exception as exc:
    print(f"PostgreSQL ainda nao esta pronto: {exc}", file=sys.stderr)
    sys.exit(1)
PY
  do
    sleep 2
  done

  echo "PostgreSQL pronto."
}

run_startup_tasks() {
  wait_for_postgres
  echo "Aplicando migracoes..."
  python manage.py migrate --noinput
  echo "Coletando arquivos estaticos..."
  python manage.py collectstatic --noinput
}

if [ "${SKIP_STARTUP_TASKS:-0}" != "1" ]; then
  run_startup_tasks
fi

if [ "${1:-}" = "gunicorn" ]; then
  shift
  exec gunicorn notchfire_project.wsgi:application \
    --bind "${GUNICORN_BIND}" \
    --workers "${GUNICORN_WORKERS}" \
    --threads "${GUNICORN_THREADS}" \
    --timeout "${GUNICORN_TIMEOUT}" \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    "$@"
fi

exec "$@"
