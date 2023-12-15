FROM alpine:latest
LABEL maintainer="Timo Taskinen <timo.taskinen@iki.fi>"

RUN apk update && apk add --no-cache \
    bash \
    ffmpeg \
    gcc \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    make \
    musl-dev \
    pipx \
    python3 \
    python3-dev \
    wget

RUN pipx install yle-dl

WORKDIR /out
ENTRYPOINT ["/root/.local/bin/yle-dl"]
