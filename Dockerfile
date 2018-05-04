FROM alpine:3.7
LABEL maintainer="Timo Taskinen <timo.taskinen@iki.fi>"

ENV YLEDLVERSION 2.30

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
    py-pip \
    py-setuptools \
    py-lxml \
    wget

RUN pip install -U pip setuptools youtube_dl yle-dl

WORKDIR /out
ENTRYPOINT ["yle-dl"]
