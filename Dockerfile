FROM python:3.12-slim

WORKDIR /app

ENV DATABASE_URL=sqlite:////app/data/db.sqlite
ENV DISPLAY=:99 
ENV FLASK_APP=wsgi:app

VOLUME ["/app/data"]

RUN apt-get update && apt-get install -y \
    xvfb \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://github.com/just-containers/s6-overlay/releases/download/v3.1.6.2/s6-overlay-noarch-3.1.6.2.tar.xz | tar -xJ -C / && \
    curl -sSL https://github.com/just-containers/s6-overlay/releases/download/v3.1.6.2/s6-overlay-x86_64-3.1.6.2.tar.xz | tar -xJ -C /

COPY pyproject.toml .
RUN pip install --no-cache-dir .
RUN patchright install chrome && patchright install-deps

COPY . .

COPY s6-overlay/s6-rc.d /etc/s6-overlay/s6-rc.d

RUN mkdir -p /var/log/db-migrate /var/log/web /var/log/scheduler && \
    chmod 755 /var/log/db-migrate /var/log/web /var/log/scheduler

RUN chmod -R +x /etc/s6-overlay/s6-rc.d/*/run /etc/s6-overlay/s6-rc.d/*/log/run

EXPOSE 8000

ENTRYPOINT ["/init"]
