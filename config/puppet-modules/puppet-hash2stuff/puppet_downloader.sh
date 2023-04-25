#!/bin/sh

BRANCH="master"
repo="https://github.com/mmckinst"
module="puppet-hash2stuff"
git ls-remote ${repo}/${module} ${BRANCH}
SHA=`git ls-remote ${repo}/${module} ${BRANCH} | awk '{print $1}'`
echo ${SHA}
wget ${repo}/${module}/archive/${BRANCH}.tar.gz -O "${module}"-"${SHA}".tar.gz


