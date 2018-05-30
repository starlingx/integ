#!/bin/sh
#
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

### BEGIN INIT INFO
# Provides:          lvm2
# Required-Start:    
# Required-Stop:     
# Default-Start:     S
# Default-Stop:
# Short-Description: Activate volume groups
### END INIT INFO

. /etc/init.d/functions

case "$1" in
  start)
    /usr/sbin/vgscan --ignorelockingfailure > /dev/null 2> /dev/null && /usr/sbin/vgchange --ignorelockingfailure -a y > /dev/null 2> /dev/null
    ;;
  stop)
    ;;
  restart)
    /usr/sbin/vgscan ; /usr/sbin/vgchange -a y
    ;;
  status)
    /usr/sbin/vgdisplay
    ;;
  *)
    echo "Usage: $0 {start|stop|status|restart}"
    exit 1
esac

exit 0
