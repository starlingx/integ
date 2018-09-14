#!/bin/bash
# Designer patches:
#   http://twiki.wrs.com/PBUeng/Patching

if [ -z $MY_WORKSPACE ] || [ -z $MY_REPO ]; then
    echo "Some dev environment variables are not set."
    echo "Refer to http://wiki.wrs.com/PBUeng/CentOSBuildProcess for instructions."
    exit 1
fi

ENGTOOLS=$(ls ${MY_WORKSPACE}/std/rpmbuild/RPMS/engtools*noarch.rpm 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "Engtools RPM has not been built. Please run \"build-pkgs engtools\" first."
    exit 1
fi

source ${MY_REPO}/stx/middleware/recipes-common/build-info/release-info.inc
#TiS_REL="16.10"
#PATCH_ID="ENGTOOLS-${TiS_REL}"
PATCH_ID="ENGTOOLS-${PLATFORM_RELEASE}"

PWD=$(pwd)

# Create CGCS Patch
cd ${MY_WORKSPACE}
PATCH_BUILD=${MY_REPO}/stx/stx-update/extras/scripts/patch_build.sh
${PATCH_BUILD} --id ${PATCH_ID} --reboot-required=N \
    --summary "System engineering data collection and analysis tools." \
    --desc    "System engineering data collection and analysis tools." \
    --all-nodes ${ENGTOOLS} \
    --warn "Intended for system engineering use only."
cd ${PWD}
exit 0
