FROM ubuntu:14.04
MAINTAINER Patrick Reynolds <patrick.reynolds@kitware.com>

EXPOSE 8080

RUN mkdir /girder
RUN mkdir /girder/logs

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

RUN apt-get update && apt-get install -y software-properties-common python-software-properties

RUN add-apt-repository ppa:chris-lea/node.js

RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libpython-dev \
    python-pip \
    nodejs
RUN pip install \
    -r requirements.txt \
    -r requirements-dev.txt \
    -r plugins/geospatial/requirements.txt \
    -r plugins/metadata_extractor/requirements.txt
RUN pip install -U six
RUN npm install -g grunt-cli
RUN npm install
RUN grunt init && grunt
ENTRYPOINT ["python", "-m", "girder"]
