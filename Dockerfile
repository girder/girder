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
&& python3 -m pip install --upgrade \
    pip \
    setuptools \
    setuptools_scm \
    wheel

# Use nvm to install node
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash

# Default node version
RUN . ~/.bashrc && \
    nvm install 14 && \
    nvm alias default 14 && \
    nvm use default && \
    ln -s $(dirname `which npm`) /usr/local/node

ENV PATH="/usr/local/node:$PATH"

RUN mkdir /girder
WORKDIR /girder
COPY . /girder/

# Build girder wheel file, and install it
RUN python3 setup.py bdist_wheel \
 && cd dist && python3 -m pip install girder && cd .. \
 && rm -rf build dist

RUN girder build

EXPOSE 8080

ENTRYPOINT ["girder", "serve"]
