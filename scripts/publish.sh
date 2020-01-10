#!/bin/bash
set -e

# Build and publish sdist's for all Python packages in this repo
PUBLISHED_PYTHON_PACKAGES=(
  .
  plugins/*
  pytest_girder
  clients/python
)
for directory in "${PUBLISHED_PYTHON_PACKAGES[@]}"; do
    pushd "$directory"
    rm -fr dist
    python setup.py sdist
    popd
    twine upload --skip-existing "$directory/dist/*"
done

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
for directory in "${PUBLISHED_NPM_PACKAGES[@]}"; do
  pushd "$directory"
  npm version --allow-same-version --no-git-tag-version "$GIT_VERSION"
  # NPM_AUTH_TOKEN must be set by the build environment
  # CircleCI does not consider environment variables in npm's "npm_config_" format to be valid
  # https://npm.community/t/cannot-set-npm-config-keys-containing-underscores-registry-auth-tokens-for-example-via-npm-config-environment-variables/233/9
  env "npm_config_//registry.npmjs.org/:_authtoken=${NPM_AUTH_TOKEN}" npm publish
  popd
done
