FROM circleci/python:3.5
MAINTAINER Kitware, Inc. <kitware@kitware.com>

# Don't use "sudo"
USER root

# Install Node.js 10
RUN curl --silent --location https://deb.nodesource.com/setup_10.x | bash - \
  && apt-get install --assume-yes nodejs \
  && npm install --global npm

# Install Girder system prereqs (including those for all plugins)
RUN apt-get update && apt-get install --assume-yes \
    libldap2-dev \
    libsasl2-dev

# Install Girder development prereqs
# Get a very recent version of CMake
RUN mkdir --parents "/opt/cmake" \
  && curl --location "https://cmake.org/files/v3.12/cmake-3.12.2-Linux-x86_64.tar.gz" | \
    gunzip --stdout | \
    tar --extract --directory "/opt/cmake" --strip-components 1 \
  && ln --symbolic --force "/opt/cmake/bin/cmake" "/usr/local/bin/cmake" \
  && ln --symbolic --force "/opt/cmake/bin/ctest" "/usr/local/bin/ctest" \
  # Note: universal-ctags is installed for use in the public_names CI job.
  && git clone "https://github.com/universal-ctags/ctags.git" "./ctags" \
  && cd ./ctags \
  && ./autogen.sh \
  && ./configure \
  && make \
  && make install \
  && cd .. \
  && rm -rf ./ctags

USER circleci
