#!/usr/bin/env bash

set -e
IMAGE='jallirs/redfishtool:latest'
if [ "x$(pwd)" = "x/" ]; then
    UPDIR=/
    WORKDIR=/up
else
    UPDIR=$(pwd)/..
    WORKDIR=/up/$(basename $(pwd))
fi

exec docker run --rm \
    --net host \
    -v $UPDIR:/up \ 
    -w $WORKDIR \
    $IMAGE \
         $*
