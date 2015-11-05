FROM ubuntu:14.04
MAINTAINER Patrick Reynolds <patrick.reynolds@kitware.com>

EXPOSE 8080

RUN mkdir /girder
RUN mkdir /girder/logs

RUN apt-get update && apt-get install -qy software-properties-common python-software-properties && \
  apt-get update && apt-get install -qy \
    build-essential \
    curl \
    git \
    libffi-dev \
    libpython-dev \
    python-pip && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# Get node
RUN set -ex \
   && for key in \
      7937DFD2AB06298B2293C3187D33FF9D0246406D \
      114F43EE0176B71C7BC219DD50A3051F888C628D \
   ; do \
      gpg --keyserver ha.pool.sks-keyservers.net --recv-keys "$key"; \
   done

ENV NODE_VERSION 0.10.40
ENV NPM_VERSION next

RUN curl -SLO "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.gz" \
   && curl -SLO "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt.asc" \
   && gpg --verify SHASUMS256.txt.asc \
   && grep " node-v$NODE_VERSION-linux-x64.tar.gz\$" SHASUMS256.txt.asc | sha256sum -c - \
   && tar -xzf "node-v$NODE_VERSION-linux-x64.tar.gz" -C /usr/local --strip-components=1 \
   && rm "node-v$NODE_VERSION-linux-x64.tar.gz" SHASUMS256.txt.asc \
   && npm install -g npm@"$NPM_VERSION" \
   && npm cache clear

WORKDIR /girder
COPY girder /girder/girder
COPY clients /girder/clients
COPY plugins /girder/plugins
COPY Gruntfile.js /girder/Gruntfile.js
COPY requirements.txt /girder/requirements.txt
COPY requirements-dev.txt /girder/requirements-dev.txt
COPY setup.py /girder/setup.py
COPY config_parse.py /girder/config_parse.py
COPY package.json /girder/package.json
COPY README.rst /girder/README.rst

RUN pip install \
    -r requirements.txt \
    -r requirements-dev.txt \
    -r plugins/geospatial/requirements.txt \
    -r plugins/metadata_extractor/requirements.txt

RUN npm install -g grunt-cli && npm cache clear
RUN npm install && npm cache clear
RUN grunt init && grunt
ENTRYPOINT ["python", "-m", "girder"]
