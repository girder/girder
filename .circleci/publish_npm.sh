#!/bin/bash
set -e
# Publish npm packages for selected locations, using npm trusted publishing
# (CircleCI OIDC). No NPM_AUTH_TOKEN is needed.
export NPM_CONFIG_PREFIX="$HOME/.npm-global"
npm install -g 'npm@^11.5.1'
export PATH="$NPM_CONFIG_PREFIX/bin:$PATH"
hash -r
npm --version

readonly GIT_VERSION=$(git describe --tags)
readonly PUBLISHED_NPM_PACKAGES=(
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
  # OIDC tokens are short-lived, so fetch a fresh one for each publish
  export NPM_ID_TOKEN=$(circleci run oidc get --claims '{"aud": "npm:registry.npmjs.org"}')
  npm publish --access public
  popd
done

