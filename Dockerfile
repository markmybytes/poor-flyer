FROM python:3.12-slim

WORKDIR /app

ENV DATABASE_URL=sqlite:////app/data/db.sqlite

VOLUME ["/app/data"]

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "wsgi:app"]
