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


# Install Universal Ctags
RUN curl -sSL "https://github.com/universal-ctags/ctags-nightly-build/releases/download/$(curl -s https://api.github.com/repos/universal-ctags/ctags-nightly-build/releases/latest | grep '"tag_name"' | head -1 | cut -d '"' -f 4)/uctags-$(curl -s https://api.github.com/repos/universal-ctags/ctags-nightly-build/releases/latest | grep '"tag_name"' | head -1 | cut -d '"' -f 4 | cut -d '+' -f 1)-$(uname -m | sed 's/x86_64/linux-x86_64/;s/aarch64/linux-aarch64/').deb" -o /tmp/uctags.deb && \
    dpkg --force-architecture -i /tmp/uctags.deb && \
    rm /tmp/uctags.deb


# Use `venv` to install Python dependencies so they can be run as a non-root user
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel setuptools-scm tox


# Install Node via NodeSource - https://nodesource.com/
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*


# Install Playwright, Chromium and Firefox
# we must specify Playwright's installation directory - https://playwright.dev/docs/browsers#managing-browser-binaries
# and let the directory be accessible to non-root users
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx --yes playwright@1.61.0 install --with-deps chromium firefox \
  && rm -rf /var/lib/apt/lists/* \
  && chmod -R a+rwX "/ms-playwright"


# in lieu of creating a user, we'll make an "ubuntu" home directory
ENV HOME=/home/ubuntu
RUN mkdir -p "$HOME/.cache/pip" "$HOME/.npm" "$HOME/.tox" \
  && chmod -R 0777 "$HOME"


# The actual UID & GID should come from the `docker-compose.yaml` file
# this is a safeguard against running the container as root
USER 1000:1000


# Run the tests
WORKDIR /home/ubuntu/girder
ENTRYPOINT ["tox"]
