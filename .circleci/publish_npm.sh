#!/bin/bash
set -e
# Publish npm packages for selected locations
# Publishing authenticates through CircleCI OIDC.  With --dry-run, every
# package is installed, versioned, built and packed, but nothing is uploaded.

dry_run=()
if [[ "$1" == "--dry-run" ]]; then
  dry_run=(--dry-run --tag dry-run)
fi

export npm_config_prefix="$HOME/.npm-global"
npm install -g 'npm@^11.5.1'
export PATH="$npm_config_prefix/bin:$PATH"
hash -r
npm --version

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
  if [[ ${#dry_run[@]} -eq 0 ]]; then
    export NPM_ID_TOKEN=$(circleci run oidc get --claims '{"aud": "npm:registry.npmjs.org"}')
  fi
  npm publish --access public "${dry_run[@]}"
  popd
done
