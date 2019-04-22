# yle-dl-docker

This is dockerized yle-dl (See: https://github.com/aajanki/yle-dl)

## Executive summary

`yle-dl` is a script that allows you to download television and
radio programs from the Finnish broadcasting company (Yle)
websites such as Yle Areena and Elävä arkisto.

Normally the script has a lot of dependencies that you do not
want pollute your system. This docker container has them all,
and you can use yle-dl script without hassle.

## Usage

Just execute this one-liner:

```sh
docker run --rm -ti -u=$(id -u):$(id -g) -v "$(pwd)":/out taskinen/yle-dl YLE-URL [OTHER-YLEDL-ARGUMENTS]
```

Then you have the downloaded file in your current working directory.


## Building the container locally

It is also possible to build a container locally.
Download the Git repository containing the `Dockerfile`.
Then run the following command to build a new container.

```sh
docker build -t taskinen/yle-dl .
```

Running the locally built container:

```sh
docker run --rm -ti -u=`id -u`:`id -g` -v "`pwd`":/out taskinen/yle-dl YLE_URL_TO_DOWNLOAD
```

Removing locally built containers:

```sh
docker image rm taskinen/yle-dl:latest
```
