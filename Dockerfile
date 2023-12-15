FROM alpine:latest
LABEL maintainer="Timo Taskinen <timo.taskinen@iki.fi>"

RUN apk update && apk add --no-cache \
    bash \
    ffmpeg \
    pipx \
    python3 \
    wget

RUN pipx install yle-dl

WORKDIR /out
ENTRYPOINT ["/root/.local/bin/yle-dl"]
