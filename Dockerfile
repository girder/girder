FROM ubuntu:22.04

LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -qy \
    gcc \
    libpython3-dev \
    git \
    libldap2-dev \
    libsasl2-dev \
    python3-pip \
    curl \
&& apt-get clean && rm -rf /var/lib/apt/lists/* \
&& python3 -m pip install --upgrade --no-cache-dir \
    pip \
    setuptools \
    setuptools_scm \
    wheel

RUN curl -LJ https://github.com/krallin/tini/releases/download/v0.19.0/tini -o /sbin/tini && \
    chmod +x /sbin/tini

RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -qy nodejs

RUN mkdir /girder
COPY . /girder/

RUN cd /girder/girder/web && npm i && npm run build

RUN pip install -e /girder

EXPOSE 8080

ENTRYPOINT ["/sbin/tini", "--", "girder", "serve"]
