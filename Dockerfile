# Use latest stable Python 3 slim image
FROM python:3.13-slim

# Metadata
LABEL maintainer="Timo Taskinen <timo.taskinen@iki.fi>" \
      org.opencontainers.image.description="Downloader for Yleisradio TV and radio programs" \
      org.opencontainers.image.source="https://github.com/taskinen/yle-dl-docker"

# Build arguments
ARG YLE_DL_VERSION
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIPX_HOME=/opt/pipx \
    PIPX_BIN_DIR=/usr/local/bin \
    PATH="/usr/local/bin:$PATH"

# Install system dependencies and pipx in a single optimized layer
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        libffi-dev \
        libxml2-dev \
        libxslt-dev \
        pipx \
        python3-dev \
        wget \
        ca-certificates && \
    apt-get clean

# Install yle-dl using pipx with build cache
RUN --mount=type=cache,target=/root/.cache/pipx \
    pipx ensurepath && \
    if [ -n "$YLE_DL_VERSION" ]; then \
        pipx install yle-dl==$YLE_DL_VERSION; \
    else \
        pipx install yle-dl; \
    fi

# Set working directory
WORKDIR /out

# Set entrypoint
ENTRYPOINT ["yle-dl"]
