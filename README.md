# yle-dl-docker

This is dockerized yle-dl (See: https://aajanki.github.io/yle-dl/)

## Executive summary

`yle-dl` is a script that allows you to download television and
radio programs from the Finnish broadcasting company (Yle)
websites such as Yle Areena and Elävä arkisto.

Normally the script has a lot of dependencies that you do not
want pollute your system. This docker container has them all,
and you can use yle-dl script without hassle.

This image also includes an optional web interface for browser-based downloads.

## Usage

Just execute this one-liner:

```sh
docker run --rm -ti -u=$(id -u):$(id -g) -v "$(pwd)":/out taskinen/yle-dl YLE-URL [OPTIONAL-YLEDL-ARGUMENTS]
```

Then you have the downloaded file in your current working directory.

## Web Interface

The image includes an optional lightweight web server for browser-based downloads.
Enable it with `ENABLE_WEB_UI=1`:

```sh
docker run -p 8080:8080 -v "$(pwd)/downloads":/out -e ENABLE_WEB_UI=1 taskinen/yle-dl
```

or:

```sh
docker compose up -d
```

Then open http://localhost:8080 in your browser.

Features:
- Simple web form for submitting downloads
- Real-time progress streaming
- Background downloads (continues even if browser is closed)
- Supports nginx reverse proxy

### Nginx Reverse Proxy Setup

See `docs/nginx-example.conf` for configuration. Key requirement:
- Disable buffering for Server-Sent Events (SSE)

Example URL: `https://example.com/yle-dl/?url=YLE-URL`

### Environment Variables

- `ENABLE_WEB_UI`: Set to `1` or `true` to enable web interface (default: disabled)
- `WORKERS`: Max concurrent downloads (default: 3)

Job history is automatically cleaned up after 7 days.
