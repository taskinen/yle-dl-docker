FROM alpine:3.4
MAINTAINER Timo Taskinen <timo.taskinen@iki.fi>

ENV YLEDLVERSION 2.10.2

RUN apk add --no-cache \
    bash \
    curl \
    tar \
    make \
    python \
    py-crypto \
    rtmpdump \
    php5 \
    php5-bcmath \
    php5-curl \
    php5-mcrypt

WORKDIR /app
RUN curl -L https://github.com/aajanki/yle-dl/tarball/${YLEDLVERSION} -o yledl.tar
RUN tar -xvf yledl.tar --strip-components=1
RUN rm yledl.tar
RUN make install
