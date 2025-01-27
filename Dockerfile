FROM python:3.13-slim
LABEL maintainer="Timo Taskinen <timo.taskinen@iki.fi>"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    pipx \
    wget \
  && rm -rf /var/lib/apt/lists/*

RUN pipx ensurepath
RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install yle-dl

WORKDIR /out
ENTRYPOINT ["yle-dl"]
