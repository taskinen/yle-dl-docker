FROM alpine:latest
LABEL maintainer="Timo Taskinen <timo.taskinen@iki.fi>"

RUN apk update && apk add --no-cache \
    bash \
    ffmpeg \
    python3 \
    wget

RUN pip3 install -U pip pysocks setuptools yle-dl

WORKDIR /out
ENTRYPOINT ["yle-dl"]
