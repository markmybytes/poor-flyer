FROM node:24-slim AS frontend-builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY vite.config.ts env.d.ts ./
COPY src/frontend ./src/frontend

RUN npm run build-only

# ---

FROM python:3.12-slim

ARG S6_OVERLAY_VERSION=3.2.2.0
ARG TARGETARCH

WORKDIR /app

ENV DISPLAY=:99

VOLUME ["/app/instance"]

RUN apt-get update && apt-get install -y \
    xvfb \
    xauth \
    curl \
    xz-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN if [ "$TARGETARCH" = "amd64" ]; then S6_ARCH="x86_64"; \
    elif [ "$TARGETARCH" = "arm64" ]; then S6_ARCH="aarch64"; \
    else S6_ARCH="$TARGETARCH"; fi && \
    curl -sSL "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz" | tar -xJ -C / && \
    curl -sSL "https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${S6_ARCH}.tar.xz" | tar -xJ -C /

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .
COPY --from=frontend-builder /app/src/static/dist ./src/static/dist

COPY s6-overlay/s6-rc.d /etc/s6-overlay/s6-rc.d

RUN find /etc/s6-overlay/s6-rc.d -type f \( -name run -o -name finish -o -name up -o -name down \) -exec chmod +x {} +

RUN groupmod -g 1000 users && \
    useradd -u 911 -U -m -d /home/abc -s /bin/false abc && \
    usermod -G users abc

EXPOSE 8000

ENTRYPOINT ["/init"]
