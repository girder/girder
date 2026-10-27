#!/bin/bash
set -e
# Publish npm packages for selected locations.
# Every package is installed, versioned, packed (its prepack script builds
# it), and checked before any is published, and the checked tarballs are what
# get published.  Publishing authenticates through CircleCI OIDC.  With
# --dry-run, everything runs except the upload.

dry_run=()
if [[ "$1" == "--dry-run" ]]; then
  dry_run=(--dry-run --tag dry-run)
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

export npm_config_prefix="$HOME/.npm-global"
npm install -g 'npm@^11.5.1'
export PATH="$npm_config_prefix/bin:$PATH"
hash -r
npm --version

GIT_VERSION=$(git describe --tags)
readonly GIT_VERSION
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

# Files a package must contain beyond what its package.json declares
required_files() {
  case "$1" in
    girder/web)
      # The full source tree for downstream external builds
      echo dist-lib/src/index.ts dist-lib/src/views/App.js
      ;;
  esac
}

pack_root=$(mktemp -d)
trap 'rm -rf "$pack_root"' EXIT
tarballs=()
for directory in "${PUBLISHED_NPM_PACKAGES[@]}"; do
  pushd "$directory"
  npm ci
  npm version --allow-same-version --no-git-tag-version "$GIT_VERSION"
  pack_dir="$pack_root/${directory//\//_}"
  mkdir "$pack_dir"
  npm pack --pack-destination "$pack_dir"
  tarball=("$pack_dir"/*.tgz)
  # shellcheck disable=SC2046
  node "$script_dir/check_npm_package.js" "${tarball[0]}" $(required_files "$directory")
  tarballs+=("${tarball[0]}")
  popd
done

for tarball in "${tarballs[@]}"; do
  if [[ ${#dry_run[@]} -eq 0 ]]; then
    NPM_ID_TOKEN=$(circleci run oidc get --claims '{"aud": "npm:registry.npmjs.org"}')
    export NPM_ID_TOKEN
  fi
  npm publish "$tarball" --access public "${dry_run[@]}"
done
