#!/bin/sh
set -e

export FLASK_APP="${FLASK_APP:-wsgi:app}"

flask db upgrade

flask run-scheduler &
SCHEDULER_PID=$!

shutdown() {
    kill -TERM "$SCHEDULER_PID" 2>/dev/null || true
    if [ -n "${WEB_PID:-}" ]; then
        kill -TERM "$WEB_PID" 2>/dev/null || true
    fi
}

trap shutdown INT TERM

xvfb-run --auto-servernum --server-args='-screen 0 1920x1080x24' \
    gunicorn --bind 0.0.0.0:8000 --workers 1 wsgi:app &
WEB_PID=$!

wait "$WEB_PID"
WEB_STATUS=$?

kill -TERM "$SCHEDULER_PID" 2>/dev/null || true
wait "$SCHEDULER_PID" 2>/dev/null || true

exit "$WEB_STATUS"
