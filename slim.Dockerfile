FROM python:3.7-alpine as builder

WORKDIR /girder
RUN apk add --no-cache git gcc musl-dev libffi-dev openssl-dev
COPY . ./
RUN pip install --no-cache-dir .

FROM python:3.7-alpine as runtime
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"
EXPOSE 8080

# Set environment to support Unicode: http://click.pocoo.org/5/python3/#python-3-surrogate-handling
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

COPY --from=builder /usr/local/lib/python3.7/site-packages/ /usr/local/lib/python3.7/site-packages/
COPY --from=girder/girder:latest /usr/share/girder/static/ /usr/local/share/girder/static/

ENTRYPOINT ["python", "-c", "from girder import cli; cli.main()", "serve"]
