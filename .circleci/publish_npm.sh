#!/bin/bash
set -e
# Publish npm packages for selected locations
# NPM_AUTH_TOKEN must be set by the build environment

readonly GIT_VERSION=$(git describe --tags)
readonly PUBLISHED_NPM_PACKAGES=(
  # Published Fontello is used by all builds, and is critical to publish
  girder/web/fontello
  # The raw JS source is used by some downstream 'external builds'
  girder/web
  # These plugins were published to support downstream external builds, and should be kept updated
  plugins/jobs/girder_jobs/web_client
  plugins/oauth/girder_oauth/web_client
  plugins/gravatar/girder_gravatar/web_client
)
for directory in "${PUBLISHED_NPM_PACKAGES[@]}"; do
  pushd "$directory"
  # Trying to set the auth token via 'npm_config_' environment variables does not work
  echo '//registry.npmjs.org/:_authToken=${NPM_AUTH_TOKEN}' > ./.npmrc
  npm version --allow-same-version --no-git-tag-version "$GIT_VERSION"
  npm publish --access public
  rm --interactive=never ./.npmrc
  popd
done
