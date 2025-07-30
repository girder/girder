FROM python:3.11-slim
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

RUN pip install --no-cache-dir --find-links https://girder.github.io/large_image_wheels large_image[sources]

RUN pip install --no-cache-dir girder-slicer-cli-web

COPY . /
ENTRYPOINT ["python", "./cli_list.py"]
