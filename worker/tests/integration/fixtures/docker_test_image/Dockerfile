FROM python:2.7-alpine
MAINTAINER Chris Harris <chris.harris@kitware.com>

RUN pip install click

COPY . $PWD

ENTRYPOINT ["python", "./test.py"]
