#!/bin/bash
set -e
# Publish npm packages for selected locations
# NPM_AUTH_TOKEN must be set by the build environment

npm install -g 'npm@^11.5.1'

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
  npm ci
  npm version --allow-same-version --no-git-tag-version "$GIT_VERSION"
  export NPM_ID_TOKEN=$(circleci run oidc get --claims '{"aud": "npm:registry.npmjs.org"}')
  npm publish --access public
  popd
done
