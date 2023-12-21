FROM cimg/python:3.8
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

RUN curl -sL https://deb.nodesource.com/setup_16.x | bash - \
  && apt-get install -y nodejs \
  && find / -xdev -name __pycache__ -type d -exec rm -r {} \+ \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Girder development prereqs
RUN apt-get update \
  && apt-get install --assume-yes \
    cmake \
    automake \
    nodejs \
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
