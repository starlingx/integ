#!/bin/bash
# Copyright (C) 2017, Red Hat, Inc.
#
# set_config.sh will copy a configuration from $1 to $2, in the process
# checking that the sha header for $1 matches the header in $2

source configlib.sh

if (( $# < 2 )); then
    echo "$0: source dest [comment-marker]"
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "Source file $1 must exist."
    exit 1
fi
src_file=$1
shift

if [ ! -f "$1" ]; then
    echo "Dest file $1 must exist."
    exit 1
fi
dst_file=$1
shift

comment_sep=${1:-#}

export LANG=en_US.utf8

DEST_FILE_SHA=""
SRC_FILE_SHA=""

calc_sha DEST_FILE_SHA "$dst_file" "$comment_sep" || echo "Failed to calc sha"
retr_sha SRC_FILE_SHA "$src_file" "$comment_sep" || echo "Failed to retrieve sha"

if [ "$DEST_FILE_SHA" != "$SRC_FILE_SHA" ]; then
    echo "ERROR: The requisite starting sha from $dst_file does not match the"
    echo "       specified sha in $src_file."
    echo "[ $DEST_FILE_SHA ] vs [ $SRC_FILE_SHA ]"
    exit 1
fi

mv "$dst_file" "$dst_file".OLD
cp "$src_file" "$dst_file"
echo "copied 1 config file."
exit 0
