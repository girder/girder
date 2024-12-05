FROM python:3.11-slim
MAINTAINER David Manthey <david.manthey@kitware.com>

RUN pip install --find-links https://girder.github.io/large_image_wheels large_image[sources]
RUN pip install girder-slicer-cli-web

COPY . $PWD
ENTRYPOINT ["python", "./cli_list.py"]
