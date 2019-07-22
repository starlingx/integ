#!/bin/bash
#
# SPDX-License-Identifier: GPLv2
#
# The qemu command details and the 98-102% range is taken from
# find-lapictscdeadline-optimal.sh and script.sh
# from the tuned package available at
# https://github.com/redhat-performance/tuned/tree/master/profiles/realtime-virtual-host
#
# The tuned package is GPLv2 therefore this component is GPLv2
#
# Copyright(c) 2019 Wind River Systems, Inc. All rights reserved.
#
QEMU=/usr/libexec/qemu-kvm
ADVANCE_FILE="/sys/module/kvm/parameters/lapic_timer_advance_ns"
ADVANCE_CALIB="/etc/kvm-timer-advance/calibrated_lapic_timer_advance_ns"

function log {
    logger -p local1.info -t $0 $@
    echo $0: "$@"
}


# This is a check for a virtualbox machine where kvm modules are not loaded
if [ ! -f $ADVANCE_FILE ]; then
    exit 1
fi

# Use previous calibrated advance result
if [ -f $ADVANCE_CALIB ]; then
    read -r advance < $ADVANCE_CALIB
    if [[ "$advance" =~  ^[0-9]+$ ]]; then
        echo $advance > $ADVANCE_FILE
        log "using previously calibrated advance value of" $(cat $ADVANCE_FILE)
        exit 0
    fi
fi

# Use the application cpus calculated by puppet. This will ensure that
# we run on a CPU that isn't being used by management or vswitch.
VCPU_PIN_STR=$(grep vcpu_pin_set /etc/kvm-timer-advance/kvm-timer-advance.conf)
VCPU_PIN_STR=${VCPU_PIN_STR//\"/}
FLOAT_CPUS=${VCPU_PIN_STR##*=}
if [ -z "${FLOAT_CPUS}" ]; then
    log "skip calibration, we have not configured yet"
    exit 0
fi
log "Calibrating with FLOAT_CPUS: ${FLOAT_CPUS}"
taskset --pid --cpu-list ${FLOAT_CPUS} $$ &> /dev/null

dir=$(mktemp -d)

advance=1500
latency=1000000


for i in $(seq 1500 500 7000); do
        log "test advance ${i}"
        echo $i > $ADVANCE_FILE
        timeout --foreground --signal TERM 10s \
        chrt -f 1 stdbuf -oL ${QEMU} -enable-kvm -device pc-testdev \
                -device isa-debug-exit,iobase=0xf4,iosize=0x4 \
                -display none -serial stdio -device pci-testdev \
                -kernel /usr/share/qemu-kvm/tscdeadline_latency.flat \
                -cpu host | awk 'NF==2 && /latency:/ {print $2}' > ${dir}/out0
        # chomp last line since output may be incomplete
        sed \$d < ${dir}/out0 > ${dir}/out

        # Calculate the average of all the latency numbers output by
        # the test image.
        A=0
        while read l; do
            A=$(($A + $l))
        done < $dir/out

        lines=$(wc -l $dir/out | cut -f 1 -d " ")
        if [ ${lines} -eq 0 ]; then
            # this shouldn't happen
            log "got no output from test, aborting"
            break
        fi

        ans=$(($A/$lines))

        # Get the current latency as a percentage of the previous latency
        value=$((${ans}*100/${latency}))

        if [ $value -ge 102 ]; then
            # Latency has increased by too much, we don't want to use this
            # much advance.  I didn't see this in practice, this is just
            # a sanity check.
            advance=$((${i} - 500))
            log "latency too large, reverting to advance of ${advance}"
            echo $advance > $ADVANCE_FILE
            break
        elif [ $value -ge 98 ]; then
            # If we're close to the previous latency, then use the current
            # advance. The algorithm has a tendency to underestimate a bit,
            # so we don't want to use the previous advance value.
            break
        else
            # We're substantially lower than the previous latency, so store
            # the current advance and latency numbers and loop through again
            # to see if it improves further with a bit higher advance.
            latency=$ans
            advance=$i
        fi
done

# Save calibrated result
cat $ADVANCE_FILE > $ADVANCE_CALIB
log "using advance value of" $(cat $ADVANCE_FILE)

rm -rf $dir
exit 0
