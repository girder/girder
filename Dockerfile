FROM node:0.10.40
MAINTAINER Patrick Reynolds <patrick.reynolds@kitware.com>

EXPOSE 8080

RUN mkdir /girder
RUN mkdir /girder/logs

RUN apt-get update && apt-get install -qy software-properties-common python-software-properties && \
  apt-get update && apt-get install -qy \
    build-essential \
    git \
    libffi-dev \
    libpython-dev \
    python-pip && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

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
