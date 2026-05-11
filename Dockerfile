FROM python:3.12-slim

WORKDIR /app

ENV DATABASE_URL=sqlite:////app/data/db.sqlite
ENV DISPLAY=:99 

VOLUME ["/app/data"]

RUN apt-get update && apt-get install -y \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN pip install --no-cache-dir .

RUN patchright install chrome && patchright install-deps

COPY . .
EXPOSE 8000

CMD ["xvfb-run", "--auto-servernum", "--server-args='-screen 0 1920x1080x24'", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "wsgi:app"]