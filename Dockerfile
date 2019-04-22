FROM alpine:3.9
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
    py-crypto \
    py-lxml \
    py-pip \
    py-setuptools \
    python \
    python2-dev \
    rtmpdump \
    tar \
    wget

RUN pip install -U pip setuptools youtube_dl yle-dl

WORKDIR /out
ENTRYPOINT ["yle-dl"]
