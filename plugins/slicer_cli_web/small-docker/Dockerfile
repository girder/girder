# Use a version of alpine that includes bash and python
FROM python:3.11-alpine
LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

# Since we are using a BusyBox variant, we need to use addgroup and adduser,
# rather than let girder_worker use groupadd and useradd.  Those will fail,
# which is allowed if the worker user and group exist.
RUN addgroup -g 1000 -S worker
RUN adduser -u 1000 -h /home/worker -S -G worker -s /bin/bash worker

# Suppress errors from groupadd and useradd
RUN touch /usr/local/bin/groupadd
RUN chmod a+x /usr/local/bin/groupadd
RUN touch /usr/local/bin/useradd
RUN chmod a+x /usr/local/bin/useradd

RUN pip install --no-cache-dir girder-slicer-cli-web girder-client
COPY . .

ENTRYPOINT ["python", "./cli_list.py"]
