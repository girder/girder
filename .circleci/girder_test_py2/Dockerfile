FROM circleci/python:2.7
MAINTAINER Kitware, Inc. <kitware@kitware.com>

# Don't use "sudo"
USER root

# Install Node.js 8
RUN curl --silent --location https://deb.nodesource.com/setup_8.x | bash - \
  && apt-get install --assume-yes nodejs \
  && npm install --global npm

# Install Girder system prereqs (including those for all plugins)
RUN apt-get update && apt-get install --assume-yes \
    libldap2-dev \
    libsasl2-dev

# Install Girder development prereqs
# CMake < 3.1 does not install properly from binaries, so fetch 3.0 from packages
RUN apt-get update && apt-get install --assume-yes \
    cmake

USER circleci
