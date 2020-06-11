FROM python:3.7-alpine as builder

WORKDIR /opt/girder
RUN apk add --no-cache git gcc musl-dev libffi-dev openssl-dev
COPY . ./
# Both PYTHONDONTWRITEBYTECODE and --no-compile are necessary to avoid creating .pyc files
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir --no-compile .

FROM python:3.7-alpine as runtime
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"
EXPOSE 8080

# Set environment to support Unicode: http://click.pocoo.org/5/python3/#python-3-surrogate-handling
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apk add --no-cache tini

COPY --from=builder /usr/local/bin/girder /usr/local/bin/girder
COPY --from=builder /usr/local/lib/python3.7/site-packages/ /usr/local/lib/python3.7/site-packages/
COPY --from=girder/girder:latest /usr/share/girder/static/ /usr/local/share/girder/static/
# Add a config file, to bind the server to all network interfaces inside the container
RUN echo '[global]\nserver.socket_host = "0.0.0.0"\n' > /etc/girder.cfg

ENTRYPOINT ["/sbin/tini", "--", "girder", "serve"]
