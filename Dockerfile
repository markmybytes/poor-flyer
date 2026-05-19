FROM python:3.12-slim

ARG S6_OVERLAY_VERSION=3.2.2.0
ARG S6_OVERLAY_ARCH="x86_64"

WORKDIR /app

ENV DATABASE_URL=sqlite:////app/data/db.sqlite
ENV DISPLAY=:99

VOLUME ["/app/data"]

RUN apt-get update && apt-get install -y \
    xvfb \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz" | tar -xJ -C / && \
    curl -sSL "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${S6_OVERLAY_ARCH}.tar.xz" | tar -xJ -C /

COPY pyproject.toml .
RUN pip install --no-cache-dir .
RUN patchright install chrome && patchright install-deps

COPY . .

COPY s6-overlay/s6-rc.d /etc/s6-overlay/s6-rc.d

RUN mkdir -p /var/log/db-migrate /var/log/web /var/log/scheduler && \
    chmod 755 /var/log/db-migrate /var/log/web /var/log/scheduler

RUN find /etc/s6-overlay/s6-rc.d -type f \( -name run -o -name finish \) -exec chmod +x {} +

RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g 1000 -d /home/appuser -m appuser

EXPOSE 8000

ENTRYPOINT ["/init"]
