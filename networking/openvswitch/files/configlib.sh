# Copyright (C) 2017, Red Hat, Inc.
#
# Core configuration file library.

# Configurations are determined by sha values.  The way to determine is by
# the special text:
# $FILE_COMMENT_TYPE -*- cfg-sha: $SHA256 -*-

export LC_ALL=C

# check required binaries
__check_reqd_binaries() {
    local BIN __binaries=("egrep" "sort" "sha256sum" "sed")
    for BIN in $__binaries; do
        if ! type -P $BIN >/dev/null 2>&1; then
            echo "Binary $BIN not found.  Please install."
            exit 1
        fi
    done
}

# Calculates a sha from a file
# The algorithm for generating a sha from a config is thus:
#
# 1. Remove all comment lines and blank lines
# 2. Sort the content
# 3. generate the sha-256 sum
#
# From a script perspective, this means:
#   egrep -v ^\# %file% | egrep -v ^$ | sort -u | sha256sum
#
# Params:
#  $1 = output variable
#  $2 = file to use to calculate the shasum
#  $3 = file comment type (defaults to # if unspecified)
calc_sha() {
    __check_reqd_binaries

    if [ "$1" == "" ]; then
        echo "Please pass in a storage variable."
        return 1
    fi

    local __resultvar=$1
    __retval=1
    shift

    local __file=$1
    local cmnt=${2:-#}

    if [ -f "$__file" ]; then
        local __shasum=$(egrep -v ^"$cmnt" "$__file" | egrep -v ^$ | sort -u | sha256sum -t | cut -d" " -f1)
        eval $__resultvar="'$__shasum'"
        __retval=0
    fi
    return $__retval
}

# Retrieves a sha stored in a file
# Param:
#  $1 = output variable
#  $2 = file to use to calculate the shasum
#  $3 = file comment type (defaults to # if unspecified)
retr_sha() {
    __check_reqd_binaries

    if [ "$1" == "" ]; then
        echo "Please pass in a storage variable."
        return 1
    fi

    local __resultvar=$1
    __retval=1
    shift

    local __file=$1
    local cmnt=${2:-#}

    if [ -f "$__file" ]; then
        if grep -q "$cmnt -\*- cfg-sha:" "$__file"; then
            local __shasum=$(grep "$cmnt -\*- cfg-sha:" "$__file" | sed -e "s@$cmnt -\*- cfg-sha: @@" | cut -d" " -f1)
            eval $__resultvar="'$__shasum'"
            __retval=0
        fi
    fi
    return $__retval
}


# Set a config value
# set_conf dpdk_build_tree parameter value
# dpdk_build_tree is the directory where the .config lives
# parameter is the config parameter
# value is the value to set for the config parameter
set_conf() {
    c="$1/.config"
    shift

    if grep -q "$1" "$c"; then
        sed -i "s:^$1=.*$:$1=$2:g" $c
    else
        echo $1=$2 >> "$c"
    fi
}

