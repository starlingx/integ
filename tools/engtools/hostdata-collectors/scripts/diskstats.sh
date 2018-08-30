#!/bin/bash
# Usage:  diskstats.sh
TOOLBIN=$(dirname $0)

# Initialize tools environment variables, and define common utility functions
. ${TOOLBIN}/engtools_util.sh
tools_init
if [ $? -ne 0 ]; then
    echo "FATAL, tools_init - could not setup environment"
    exit $?
fi

# Enable use of INTERVAL_SEC sample interval
OPT_USE_INTERVALS=1

# Print disk summary
function print_disk()
{
    print_separator
    TOOL_HIRES_TIME

  # NOTES:
  # --total (grand-total) is a new option, but don't necessarily want to add tmpfs
  #   or dummy filesystems.
  # - use -H to print in SI (eg, GB, vs GiB)
  # - can use -a to print all filesystems including dummy filesystems, but then
  #   there can be double-counting:
    print_separator
    cmd='df -h -H -T --local -t ext2 -t ext3 -t ext4 -t xfs --total'
    ${ECHO} "Disk space usage ext2,ext3,ext4,xfs,tmpfs (SI):"
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}

    print_separator
    cmd='df -h -H -T --local -i -t ext2 -t ext3 -t ext4 -t xfs --total'
    ${ECHO} "Disk inodes usage ext2,ext3,ext4,xfs,tmpfs (SI):"
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}

    print_separator
    cmd='drbd-overview'
    ${ECHO} "drbd disk usage and status:"
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}

    print_separator
    cmd='lvs'
    ${ECHO} "logical volumes usage and status:"
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}

    print_separator
    cmd='pvs'
    ${ECHO} "physical volumes usage and status:"
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}

    print_separator
    cmd='vgs'
    ${ECHO} "volume groups usage and status:"
    ${ECHO} "# ${cmd}" ; ${cmd} ; ${ECHO}
}

# Print disk static summary
function print_disk_static()
{
    print_separator
    cmd='cat /proc/scsi/scsi'
    ${ECHO} "Attached devices: ${cmd}"
    ${cmd}
    ${ECHO}

  # fdisk - requires sudo/root
    print_separator
    cmd='fdisk -l'
    if [ $UID -eq 0 ]; then
        ${ECHO} "List disk devices: ${cmd}"
        ${cmd}
    else
        WARNLOG "Skipping cmd=${cmd}, root/sudo passwd required"
    fi
    ${ECHO}

  # parted - requires sudo/root
    print_separator
    cmd='parted -l'
    if [ $UID -eq 0 ]; then
        ${ECHO} "List disk devices: ${cmd}"
        ${cmd}
    else
        WARNLOG "Skipping cmd=${cmd}, root/sudo passwd required"
    fi
    ${ECHO}
}

#-------------------------------------------------------------------------------
# MAIN Program:
#-------------------------------------------------------------------------------
# Parse input options
tools_parse_options "${@}"

# Set affinity of current script
CPULIST=""
set_affinity ${CPULIST}

LOG "collecting ${TOOLNAME} for ${PERIOD_MIN} minutes, with ${INTERVAL_SEC} second sample intervals."

# Print tools generic tools header
tools_header

# Print static disk information
print_disk_static

# Calculate number of sample repeats based on overall interval and sampling interval
((REPEATS = PERIOD_MIN * 60 / INTERVAL_SEC))

for ((rep=1; rep <= REPEATS ; rep++))
do
    print_disk
    sleep ${INTERVAL_SEC}
done
print_disk
LOG "done"

# normal program exit
tools_cleanup 0
exit 0
