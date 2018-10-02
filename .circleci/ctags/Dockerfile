FROM circleci/python:3.5
MAINTAINER Kitware, Inc. <kitware@kitware.com>

USER root

RUN apt-get update && apt-get install --assume-yes ctags
RUN pip install six

USER circleci
