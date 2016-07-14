# yle-dl-docker

This is dockerized yle-dl (See: https://github.com/aajanki/yle-dl)

## Executive summary

Yle-dl is a script that allows you to download television and
radio programs from the Finnish broadcasting company (Yle)
websites such as Yle Areena and Elävä arkisto.

Normally the script has a lot of dependencies that you do not
want pollute your system. This docker container has them all,
and you can use yle-dl script without hassle.

## Usage

Just execute this one-liner:

```docker run --rm -ti -v `pwd`:/out taskinen/yle-dl yle-dl [YLE-URL-TO-DOWNLOAD]```

And �vóila, you have the downloaded file in your current
working directory.
