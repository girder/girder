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
  && rm -rf /var/lib/apt/lists/*


# Ubuntu 22 can install and run Python 3.10 easily
# Installing Python 3.10 on later Ubuntu versions will require additional setup


# Use `venv` to install Python dependencies so they can be run as a non-root user
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel setuptools-scm tox


# Install Node via NodeSource - https://nodesource.com/
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*


# Install Playwright and Chromium
# we must specify Playwright's installation directory - https://playwright.dev/docs/browsers#managing-browser-binaries
# and let the directory be accessible to non-root users
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx --yes playwright@1.61.0 install --with-deps chromium firefox \
  && chmod -R a+rwX "/ms-playwright"


# Create a non-root user, "ubuntu"
# (starting in Ubuntu 24.04, this user is already available)
ARG UID=1000
ARG GID=1000
RUN groupadd -g "${GID}" ubuntu \
  && useradd -m -u "${UID}" -g "${GID}" -s /bin/bash ubuntu
USER ubuntu


# Run the tests
WORKDIR /home/ubuntu/girder
ENTRYPOINT ["tox"]
