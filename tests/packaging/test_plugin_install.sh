#!/bin/bash

virtualenv_activate="${1}"
source_path="${2}"
virtualenv_pip="${3}"
unset PYTHONPATH

source "${virtualenv_activate}"

girder-install plugin "${source_path}/plugins/thumbnails"

if [ $? -eq 0 ] ; then
    echo "Error: expected an error when installing an existing plugin without -f"
    exit 1
fi

girder-install plugin -f "${source_path}/plugins/thumbnails" "${source_path}/plugins/oauth" || exit 1

dest_path=$(girder-install plugin-path)
girder-install plugin -f "${dest_path}/thumbnails" || exit 1

if [ ! -f "${dest_path}/thumbnails/plugin.yml" ] ; then
    echo "Error: plugin was deleted"
    exit 1
fi

extras_path="$(girder-install web-root)/static/built/plugins/plugin_with_extras"
rm -fr "$extras_path"

girder-install plugin -f "${source_path}/tests/packaging/plugin_with_extras" || exit 1
girder-install web --plugins=plugin_with_extras

if [ ! -f "${extras_path}/extra/data.txt" ] ; then
    echo "Error: extra file not copied to the web root"
    exit 1
fi
