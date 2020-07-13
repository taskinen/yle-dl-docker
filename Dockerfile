FROM alpine:latest
LABEL maintainer="Timo Taskinen <timo.taskinen@iki.fi>"

RUN apk add --no-cache \
    bash \
    curl \
    ffmpeg \
    gcc \
    libxml2-dev \
    libxslt-dev \
    make \
    musl-dev \
    py3-crypto \
    py3-lxml \
    py3-pip \
    py3-setuptools \
    python3 \
    python3-dev \
    tar \
    wget

RUN pip3 install -U pip setuptools yle-dl

WORKDIR /out
ENTRYPOINT ["yle-dl"]
