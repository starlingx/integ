#!/bin/bash

SOURCE_SPEC=~/qemu/qemu-kvm.spec
SOURCE_PATCH_DIR=~/qemu/

# Base patch order on the '%patch' statements (not 'Patchx:' definition)
for patch in `cat $SOURCE_SPEC | grep '%patch[0-9]\{1,\} ' | awk '{print $1'}`; do
    # Resolve patch name base on it's id/number
    id=`echo $patch | sed 's/%patch//'`
    p=`grep "Patch$id:" $SOURCE_SPEC | awk '{print $2}'`

    echo "-> Processing patch: $p"
    git am -3 $SOURCE_PATCH_DIR/$p
    if [ $? -ne 0 ]; then
        echo "--> Failed, falling back to manual patching"
        git am --abort
        # patch -p1 < $SOURCE_PATCH_DIR/$p
        git apply --index $SOURCE_PATCH_DIR/$p
        if [ $? -ne 0 ]; then
            echo "--> Failed manual patching, abort"
        else
            git add -A
            git commit -m "Manual patch apply: $p"
        fi
    fi
done
