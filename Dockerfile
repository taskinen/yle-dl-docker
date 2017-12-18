FROM alpine:3.7
MAINTAINER Timo Taskinen <timo.taskinen@iki.fi>

ENV YLEDLVERSION 2.29

RUN apk add --no-cache \
    bash \
    curl \
    tar \
    gcc \
    musl-dev \
    make \
    python \
    py-crypto \
    python2-dev \
    libxslt-dev \
    libxml2-dev \
    rtmpdump \
    ffmpeg \
    php7 \
    php7-bcmath \
    php7-curl \
    php7-mcrypt \
    php7-simplexml \
    py-pip

RUN pip install -U pip setuptools youtube_dl yle-dl

WORKDIR /out
ENTRYPOINT ["yle-dl"]
