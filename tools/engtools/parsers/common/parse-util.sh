#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
#PARSERDIR=$(dirname $0)
#LOGFILE="${PARSERDIR}/parserlog.txt"
LOGFILE="parserlog.txt"

function LOG ()
{
    local tstamp_H=$( date +"%Y-%0m-%0e %H:%M:%S" )
    echo -e "${tstamp_H} $0($$): $@" >> ${LOGFILE}
}

function ERRLOG ()
{
    LOG "ERROR: $@"
}

function WARNLOG ()
{
    LOG "WARN: $@"
}

