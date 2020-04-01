FROM circleci/python:3.6-node
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

# Don't use "sudo"
USER root

# Install Girder system prereqs (including those for all plugins)
RUN apt-get update \
  && apt-get install --assume-yes \
    libldap2-dev \
    libsasl2-dev

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

USER circleci
