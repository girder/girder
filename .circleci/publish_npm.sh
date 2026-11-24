#!/bin/bash
set -e
# Publish npm packages for selected locations, using npm trusted publishing
# (CircleCI OIDC). No NPM_AUTH_TOKEN is needed.
# Every package is versioned, built (if it has a prepublishOnly script),
# packed, and checked before any is published, and the checked tarballs are
# what get published.  With --dry-run, everything runs except the upload.

dry_run=()
if [[ "$1" == "--dry-run" ]]; then
  dry_run=(--dry-run --tag dry-run)
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

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

pack_root=$(mktemp -d)
trap 'rm -rf "$pack_root"' EXIT
tarballs=()
for directory in "${PUBLISHED_NPM_PACKAGES[@]}"; do
  pushd "$directory"
  npm version --allow-same-version --no-git-tag-version "$GIT_VERSION"
  # Publishing a tarball runs no lifecycle scripts, so run prepublishOnly
  # (which builds the package) before packing
  if node -e 'process.exit((require("./package.json").scripts || {}).prepublishOnly ? 0 : 1)'; then
    npm run prepublishOnly
  fi
  pack_dir="$pack_root/${directory//\//_}"
  mkdir "$pack_dir"
  npm pack --pack-destination "$pack_dir"
  tarball=("$pack_dir"/*.tgz)
  node "$script_dir/check_npm_package.js" "${tarball[0]}"
  tarballs+=("${tarball[0]}")
  popd
done

for tarball in "${tarballs[@]}"; do
  if [[ ${#dry_run[@]} -eq 0 ]]; then
    # OIDC tokens are short-lived, so fetch a fresh one for each publish
    export NPM_ID_TOKEN=$(circleci run oidc get --claims '{"aud": "npm:registry.npmjs.org"}')
  fi
  npm publish "$tarball" --access public "${dry_run[@]}"
done
