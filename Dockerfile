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
    libpython-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py && python get-pip.py

WORKDIR /girder
COPY girder /girder/girder
COPY clients /girder/clients
COPY plugins /girder/plugins
COPY scripts /girder/scripts
COPY Gruntfile.js /girder/Gruntfile.js
COPY requirements.txt /girder/requirements.txt
COPY requirements-dev.txt /girder/requirements-dev.txt
COPY setup.py /girder/setup.py
COPY package.json /girder/package.json
COPY README.rst /girder/README.rst

RUN python /girder/scripts/InstallPythonRequirements.py --mode=dev

RUN npm install -g grunt-cli && npm cache clear
RUN npm install --unsafe-perm && npm cache clear
ENTRYPOINT ["python", "-m", "girder"]
