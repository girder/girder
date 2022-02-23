FROM node:12-buster
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

RUN apt-get update && apt-get install -qy \
    gcc \
    libpython3-dev \
    git \
    libldap2-dev \
    libsasl2-dev \
    python3-pip \
&& apt-get clean && rm -rf /var/lib/apt/lists/* \
&& python3 -m pip install --upgrade \
    pip \
    setuptools \
    setuptools_scm \
    wheel

# See http://click.pocoo.org/5/python3/#python-3-surrogate-handling for more detail on
# why this is necessary.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

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
