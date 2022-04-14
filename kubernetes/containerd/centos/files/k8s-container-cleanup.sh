#!/bin/bash
# Copyright (c) 2022 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# The script will run during containerd.service ExecStop.
# This script detects whether systemd state is 'stopping' due to
# shutdown/reboot, then will stop all running containers before the
# service shuts down.
#
# All running containers are stopped one container at a time.
# The internal implementation of 'crictl stop --timeout <n>'
# sends a SIGTERM to the container, and will use SIGKILL only
# if the timeout is reached.
#

NAME=$(basename "${0}")

# Log info message to /var/log/daemon.log
function LOG {
    logger -p daemon.info -t "${NAME}($$): " "${@}"
}

# Log error message to /var/log/daemon.log
function ERROR {
    logger -p daemon.error -t "${NAME}($$): " "${@}"
}

state=$(timeout 10 systemctl is-system-running)
RC=$?
LOG "System state is: ${state}, RC = ${RC}."
case $RC in
    124)
        # systemctl hung.
        ERROR "systemctl timed out. System state unknown."
        ;;

    [01])
        # 0 - running; 1 - initializing, starting, degraded, maintenance, stopping
        if [ "$state" = "stopping" ]; then
            LOG "Stopping all containers."
            # Use crictl to gracefully stop each container. If specified timeout is
            # reached, it forcibly kills the container. There is no need to check
            # return code since there is nothing more we can do, and crictl already
            # logs to daemon.log.
            crictl ps -q | xargs -r -I {} crictl stop --timeout 5 {}
            LOG "Stopping all containers completed."
            exit 0
        fi
        ;;
esac

exit 0
