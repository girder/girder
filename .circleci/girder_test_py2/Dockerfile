FROM circleci/python:2.7
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

# Don't use "sudo"
USER root

# Install Node.js 10
RUN curl --fail --silent --location 'https://deb.nodesource.com/setup_10.x' | bash - \
  && apt-get install --assume-yes \
    'nodejs=10.*' \
  && npm install --global \
    npm

# Install Girder system prereqs (including those for all plugins)
RUN apt-get update \
  && apt-get install --assume-yes \
    libldap2-dev \
    libsasl2-dev

# Install Girder development prereqs
RUN apt-get update \
  && apt-get install --assume-yes \
    cmake \
  && pip install --no-cache --upgrade \
    pip \
    setuptools \
    tox

USER circleci
