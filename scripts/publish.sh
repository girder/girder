#!/bin/bash
set -e

# Build and publish sdist's for all Python packages in this repo
PUBLISHED_PYTHON_PACKAGES=(
  .
  plugins/*
  pytest_girder
  clients/python
)
for d in "${PUBLISHED_PYTHON_PACKAGES[@]}"; do
    pushd $d
    rm -fr dist
    python setup.py sdist
    popd
done
twine upload --skip-existing dist/* plugins/*/dist/* clients/python/dist/* pytest_girder/dist/*

# Publish npm packages for selected locations
GIT_VERSION=$(git describe --tags)
PUBLISHED_NPM_PACKAGES=(
  # Published Fontello is used by all builds, and is critical to publish
  girder/web_client/fontello
  # These lint configs are used by downstream plugins
  girder/web_client/eslint-config
  girder/web_client/pug-lint-config
  # The raw JS source is used by some downstream 'external builds'
  girder/web_client/src
  # These plugins were published to support downstream external builds, and should be kept updated
  plugins/jobs/girder_jobs/web_client
  plugins/oauth/girder_oauth/web_client
  plugins/gravatar/girder_gravatar/web_client
)
for d in "${PUBLISHED_NPM_PACKAGES[@]}"; do
  pushd $d
  npm version --allow-same-version --no-git-tag-version "$GIT_VERSION"
  npm publish
  popd
done

