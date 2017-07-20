FROM alpine:3.6
MAINTAINER Timo Taskinen <timo.taskinen@iki.fi>

ENV YLEDLVERSION 2.20

RUN apk add --no-cache \
    bash \
    curl \
    tar \
    make \
    python \
    py-crypto \
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
