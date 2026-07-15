FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive 
ENV LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  ca-certificates \
  cmake \
  curl \
  git \
  vim \
  fuse3 \
  libfuse3-dev \
  libldap2-dev \
  libsasl2-dev \
  pkg-config \
  libpython3-dev \
  python3.10 \
  python3.10-venv \
  python3.10-dev \
  redis \
  rabbitmq-server \
  && rm -rf /var/lib/apt/lists/*


# Ubuntu 22 can install and run Python 3.10 easily
# Later Ubuntu versions will require a more involved setup
# Use `venv` to install `tox`, etc on the non-root PATH
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel setuptools-scm tox


# Install Node via NodeSource - https://nodesource.com/
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*


# Install Playwright and Chromium
# specifying Playwright's installation path - https://playwright.dev/docs/browsers#managing-browser-binaries
# and making the `/ms-playwright` directory accessible to non-root users
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx --yes playwright@1.61.0 install --with-deps chromium firefox \
  && chmod -R a+rwX "/ms-playwright"


# Install MongoDB 6.0
RUN apt-get update && apt-get install -y --no-install-recommends gnupg \
  && curl -fsSL https://pgp.mongodb.com/server-6.0.asc \
    | gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor \
  && echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" \
    > /etc/apt/sources.list.d/mongodb-org-6.0.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends mongodb-org \
  && rm -rf /var/lib/apt/lists/*


# Create a non-root user, "ubuntu"
# (starting in Ubuntu 24.04, this user is already available)
ARG UID=1000
ARG GID=1000
RUN groupadd -g "${GID}" ubuntu \
  && useradd -m -u "${UID}" -g "${GID}" -s /bin/bash ubuntu
USER ubuntu


# Create directory for MongoDB, not as root user
RUN mkdir -p /home/ubuntu/mongo/db/


# create directories for RabbitMQ
ENV RABBITMQ_MNESIA_BASE=/home/ubuntu/rabbitmq/mnesia \
    RABBITMQ_LOG_BASE=/home/ubuntu/rabbitmq/log
RUN mkdir -p /home/ubuntu/rabbitmq/mnesia /home/ubuntu/rabbitmq/log


# Copy start script
WORKDIR /home/ubuntu
COPY --chown=ubuntu start.sh start.sh


# Run startup script automatically
WORKDIR /home/ubuntu
ENTRYPOINT ["./start.sh"]
