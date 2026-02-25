FROM cimg/python:3.9
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

# Don't use "sudo"
USER root

# Install Girder system prereqs (including those for all plugins)
RUN apt-get update \
  && apt-get install --assume-yes \
    libldap2-dev \
    libsasl2-dev \
    autotools-dev \
    automake \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Girder development prereqs
RUN apt-get update \
  && apt-get install --assume-yes \
    cmake \
  # Note: universal-ctags is installed for use in the public_names CI job.
  && git clone "https://github.com/universal-ctags/ctags.git" "./ctags" \
  && cd ./ctags \
  && ./autogen.sh \
  && ./configure \
  && make \
  && make install \
  && cd .. \
  && rm -rf ./ctags \
  && pip3 install --no-cache --upgrade \
    pip \
    setuptools \
    tox

ENV NODE_VERSION=14

RUN mkdir 777 /.nvm && \
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | NVM_DIR=/.nvm bash && \
    . /.nvm/nvm.sh && \
    npm config set fetch-timeout 600000 && \
    npm cache clean --force && \
    ln -s $(dirname `which npm`) /usr/local/node

ENV PATH="/usr/local/node:$PATH"

USER circleci
