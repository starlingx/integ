#!/bin/bash

#
# Copyright (c) 2013-2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

root="../../../../../.."
centOSBuildRoot=".."
jenkinsBuildFileName="BUILD"
jenkinsBuildFile="$root/$jenkinsBuildFileName"
jenkinsBuildFileCentOS="$centOSBuildRoot/$jenkinsBuildFileName"
releaseInfoFile="../release-info.inc"
destFile="build.info"
destH="build_info.h"

# If Jenkins build file does not exist in the expected Rel 2 directory,
# check if it was packaged in the source RPM
if  [ ! -e $jenkinsBuildFile ]; then
    if [ -e $jenkinsBuildFileCentOS ]; then
        jenkinsBuildFile=$jenkinsBuildFileCentOS
    fi
fi

if [ -e $releaseInfoFile ]; then
    source $releaseInfoFile
fi

if [ "${REPO}x" == "x" ]; then
    REPO=`grep CONFIGURE_CMD $root/config.properties | awk ' { print $1 } ' | awk -F '"' ' { print $2 } ' | sed 's|\(.*\)\(\/.*\/.*\)$|\1|g'`
fi

if  [ -e $jenkinsBuildFile ]; then
    cp $jenkinsBuildFile $destFile
    source $jenkinsBuildFile
else
    # PLATFORM_RELEASE should be set in release-info.inc
    if [ "x${PLATFORM_RELEASE}" == "x" ]; then
        SW_VERSION="Unknown"
    else
        SW_VERSION="${PLATFORM_RELEASE}"
    fi

    BUILD_TARGET="Unknown"
    BUILD_TYPE="Informal"
    BUILD_ID="n/a"
    JOB="n/a"
    if [ "${BUILD_BY}x" == "x" ]; then
        BUILD_BY="$USER"
    fi
    BUILD_NUMBER="n/a"
    BUILD_HOST="$HOSTNAME"
    if [ "${BUILD_DATE}x" == "x" ]; then
        BUILD_DATE=`date "%F %T %z"`
        if [ $? -ne 0 ]; then
            BUILD_DATE=`date "+%F %T %z"`
        fi
    fi

    echo "SW_VERSION=\"$SW_VERSION\"" > $destFile
    echo "BUILD_TARGET=\"$BUILD_TARGET\"" >> $destFile
    echo "BUILD_TYPE=\"$BUILD_TYPE\""  >> $destFile
    echo "BUILD_ID=\"$BUILD_ID\"" >> $destFile
    echo "" >> $destFile
    echo "JOB=\"$JOB\"" >> $destFile
    echo "BUILD_BY=\"$BUILD_BY\""  >> $destFile
    echo "BUILD_NUMBER=\"$BUILD_NUMBER\"" >> $destFile
    echo "BUILD_HOST=\"$BUILD_HOST\"" >> $destFile
    echo "BUILD_DATE=\"$BUILD_DATE\"" >> $destFile
    echo "" >> $destFile
    echo "BUILD_DIR=\""`bash -c "cd $root; pwd"`"\"" >> $destFile
    echo "WRS_SRC_DIR=\"$REPO\"" >> $destFile
    if [ "${WRS_GIT_BRANCH}x" == "x" ]; then
        echo "WRS_GIT_BRANCH=\""`cd $REPO; git status -s -b | grep '##' | awk ' { printf $2 } '`"\"" >> $destFile
    else
        echo "WRS_GIT_BRANCH=\"$WRS_GIT_BRANCH\"" >> $destFile
    fi

    echo "CGCS_SRC_DIR=\"$REPO/stx\"" >> $destFile
    if [ "${CGCS_GIT_BRANCH}x" == "x" ]; then
        echo "CGCS_GIT_BRANCH=\""`cd $REPO/stx/; git status -s -b | grep '##' | awk ' { printf $2 } '`"\"" >> $destFile
    else
        echo "CGCS_GIT_BRANCH=\"$CGCS_GIT_BRANCH\"" >> $destFile
    fi

fi

echo "#ifndef _BUILD_INFO_H_" > $destH
echo "#define _BUILD_INFO_H_" >> $destH
echo "" >> $destH
echo "#define RELEASE_NAME \"$RELEASE_NAME\"" >> $destH
echo "#define SW_VERSION \"$SW_VERSION\"" >> $destH
echo "" >> $destH
echo "#define BUILD_TARGET \"$BUILD_TARGET\"" >> $destH
echo "#define BUILD_TYPE \"$BUILD_TYPE\""  >> $destH
echo "#define BUILD_ID \"$BUILD_ID\"" >> $destH
echo "" >> $destH
echo "#define JOB \"$JOB\"" >> $destH
echo "#define BUILD_BY \"$BUILD_BY\""  >> $destH
echo "#define BUILD_NUMBER \"$BUILD_NUMBER\"" >> $destH
echo "#define BUILD_HOST \"$BUILD_HOST\"" >> $destH
echo "#define BUILD_DATE \"$BUILD_DATE\"" >> $destH
echo "#endif /* _BUILD_INFO_H_ */" >> $destH
