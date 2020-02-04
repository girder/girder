#!/bin/bash
set -e

curl --fail --request 'POST' --data-urlencode 'gitUrl=git@github.com:girder/girder.git' 'https://doc.esdoc.org/api/create'
