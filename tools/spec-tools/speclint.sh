#!/bin/bash
#
# SPDX-License-Identifier: Apache-2.0
#
# Derived from the openstack/rpm-packaging scripts

set -e

usage() {
    echo ""
    echo "Usage: "
    echo "   Provide lint-like info about specfiles:"
    echo "   speclint.sh <spec files list>"
    exit 1
}

if [ ${#@} -eq 0 ]; then
    usage
fi

while getopts "h" o; do
    case "${o}" in
        *)
            usage
            ;;
    esac
done

tmpdir=$(mktemp -d)
MAXPROC=4
if [ -d ../stx-integ ]; then
    echo "Fetching from stx-integ"
    cat ../stx-integ/tools/spec-tools/macros.openstack-singlespec > $tmpdir/.rpmmacros
elif [ -d ../integ ]; then
    echo "Fetching from integ"
    cat ../integ/tools/spec-tools/macros.openstack-singlespec > $tmpdir/.rpmmacros
else
    echo "Fetching from git"
    wget -q -O $tmpdir/.rpmmacros https://opendev.org/openstack/rpm-packaging/raw/branch/master/openstack/openstack-macros/macros.openstack-singlespec
    echo "%tis_patch_ver 1" >> $tmpdir/.rpmmacros
fi

failed=0
for spec in $@; do
    if [ ! -f $spec ]; then
        echo "$spec does not exisit, please pass valid RPM specfiles on the cmdline"
        failed=1
        continue 1
    fi
    echo "Checking $spec"
    specname=$(basename $spec)
    egrep -q '^Source:' $spec && {
        echo "$spec should not have Source: lines. Please use Source0: instead."
        failed=1
    }
    egrep -q '^%setup' $spec && {
        echo "$spec should not use '%setup'. Please use '%autosetup' instead."
        failed=1
    }
    egrep -q '%{__python[23]}' $spec && {
        echo "$spec should not use '%{__python[23]}'. Please use 'python2' or 'python3' instead."
        failed=1
    }

    (cd $(dirname $spec); HOME=$tmpdir rpmspec -q --qf "%{VERSION}\n" $specname) >/dev/null || {
            echo "$spec does not parse properly. Please check your syntax."
            failed=1
    }

    echo "spec-cleaner checking $specname"
    # Make a copy to do some fix-ups required by spec-cleaner
    cp $spec $tmpdir/$specname
    # NOTE(toabctl):spec-cleaner can not ignore epochs currently
    sed -i '/^Epoch:.*/d' $tmpdir/$specname
    # NOTE(jpena): spec-cleaner wants python2/python3 instead of
    # %{__python2}/%{__python3}
    # https://github.com/openSUSE/spec-cleaner/issues/173
    sed -i 's/%{__python2}/python2/g' $tmpdir/$specname
    sed -i 's/%{__python3}/python3/g' $tmpdir/$specname
    spec-cleaner -m -d --no-copyright --diff-prog "diff -uw" \
                 $tmpdir/$specname > $tmpdir/$specname.cleaner.diff &
    let count+=1
    [[ count -eq $MAXPROC ]] && wait && count=0
done

# check if some diffs are available
for specdiff in $tmpdir/*.cleaner.diff; do
    if [ -s "$specdiff" ]; then
        echo "##### `basename ${specdiff} .cleaner.diff` ##### "
        cat $specdiff
        failed=1
    fi
done

rm -rf $tmpdir

exit $failed
