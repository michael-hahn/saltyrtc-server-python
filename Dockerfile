# syntax=docker/dockerfile:1
# Dockerfile for the SaltyRTC Server.
# This Dockerfile is updated for the Splice version of the server.
#
# WARNING: This Dockerfile does not include TLS termination. Make sure to run
#          the container behind a reverse proxy (e.g. Nginx) or make use of
#          the -tc and -tk parameters to provide the certificate and key
#          directly.
FROM ubuntu:18.04

# Set working directory
WORKDIR /usr/src/saltyrtc-server

# Install dependencies
RUN apt-get update -qqy \
 && apt-get install -qqy --no-install-recommends \
    libsodium23 \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/*
# SaltyRTC is recommended to run on Python 3.7
RUN apt-get update
RUN apt-get install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa -y
RUN apt-get install python3.7 python3.7-dev python3.7-distutils python3.7-venv python3-wheel -y
RUN apt-get install python3-pip -y

# Copy sources
# COPY examples ./examples
COPY saltyrtc ./saltyrtc
# COPY tests ./tests
COPY saltyrtc.crt ./
COPY saltyrtc.key ./
COPY CHANGELOG.rst LICENSE README.rst setup.cfg setup.py ./

# Install the server
# RUN pip install --no-cache-dir ".[logging, uvloop]"
RUN python3.7 setup.py install

# Rnn the server
CMD ["/usr/local/bin/saltyrtc-server", "serve", "-p", "8765", "-k", "./saltyrtc/server/permanent-key", "-tc", "./saltyrtc.crt", "-tk", "./saltyrtc.key"]
