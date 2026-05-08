#!/bin/sh
set -e

alembic upgrade head

if [ "${DEBUG:-false}" = "true" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
