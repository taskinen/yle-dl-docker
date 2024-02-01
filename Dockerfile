FROM python:3.12-slim
LABEL maintainer="Timo Taskinen <timo.taskinen@iki.fi>"

RUN apt-get update && apt-get install -y \
    bash \
    build-essential \
    ffmpeg \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    pipx \
    python3-dev \
    wget \
  && rm -rf /var/lib/apt/lists/*

RUN pipx ensurepath
RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install yle-dl

WORKDIR /out
ENTRYPOINT ["yle-dl"]
