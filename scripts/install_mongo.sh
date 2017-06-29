#!/bin/bash

PREFIX="$CACHE/mongo-$MONGO_VERSION"
if [[ ! -f "$PREFIX/bin/mongod" || -n "$UPDATE_CACHE" ]] ; then
    rm -fr "$PREFIX"
    mkdir -p "$PREFIX"
    curl -L "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-${MONGO_VERSION}.tgz" | gunzip -c | tar -x -C "$PREFIX" --strip-components 1
fi
export PATH="$PREFIX/bin:$PATH"
