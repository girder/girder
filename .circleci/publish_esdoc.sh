#!/bin/bash
set -e

curl 'https://doc.esdoc.org/api/create' -X POST --data-urlencode "gitUrl=git@github.com:girder/girder.git"
