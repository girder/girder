FROM circleci/python:3.4
MAINTAINER Kitware, Inc. <kitware@kitware.com>

# Don't use "sudo"
USER root

# Install Node.js 8
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash - \
  && apt-get install -y nodejs \
  && npm install -g npm

# Install Girder system prereqs (including those for all plugins)
RUN apt-get update && apt-get install -y \
    libldap2-dev \
    libsasl2-dev

# Install Girder development prereqs
# Get a very recent version of CMake
RUN mkdir --parents "/opt/cmake" \
  && curl --location "https://cmake.org/files/v3.9/cmake-3.9.4-Linux-x86_64.tar.gz" | \
    gunzip --stdout | \
    tar --extract --directory "/opt/cmake" --strip-components 1 \
  && ln --symbolic --force "/opt/cmake/bin/cmake" "/usr/local/bin/cmake" \
  && ln --symbolic --force "/opt/cmake/bin/ctest" "/usr/local/bin/ctest"

USER circleci
