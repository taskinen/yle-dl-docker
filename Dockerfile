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
    php7 \
    php7-bcmath \
    php7-curl \
    php7-mcrypt \
    php7-simplexml \
    py3-crypto \
    py3-lxml \
    py3-pip \
    py3-setuptools \
    python3 \
    python3-dev \
    rtmpdump \
    tar \
    wget

RUN pip3 install -U pip setuptools youtube_dl yle-dl

WORKDIR /out
ENTRYPOINT ["yle-dl"]
