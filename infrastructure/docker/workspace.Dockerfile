FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    netcat-traditional \
    iputils-ping \
    dnsutils

WORKDIR /workspace