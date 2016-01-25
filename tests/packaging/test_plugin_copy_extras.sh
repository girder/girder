#!/bin/bash

# This is a regression test for issue #1179.
# Make sure the plugin installation also copies the "extras" directory.
virtualenv_activate="${1}"
source_path="${2}"
unset PYTHONPATH

source "${virtualenv_activate}"

extras_path="$(girder-install web-root)/static/built/plugins/plugin_with_extras"
echo $extras_path
rm -fr "$extras_path"

girder-install plugin -f "${source_path}/tests/packaging/plugin_with_extras"

if [ "$?" -ne 0 ] ; then
    echo "Failed to install the test plugin"
    exit 1
fi


if [ ! -f "${extras_path}/extra/data.txt" ] ; then
    echo "Error: extra file not copied to the web root"
    exit 1
fi

exit 0
