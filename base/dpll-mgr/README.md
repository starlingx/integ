# dpll-mgr — Advanced PTP Timing Synchronization Manager

A timing synchronization manager for Intel platforms with DPLL hardware
support (Granite Rapids-D / E830 NIC). Coordinates PTP clock recovery,
DPLL lock management, gearshift phase alignment, and GNSS reference
monitoring.

## Build

Requires: `libcjson-dev`, `libgps-dev`, `libnl-3-dev`, `linux-libc-dev`

```
make
```

## Install

```
make install DESTDIR=/usr/local
```

## Configuration

Copy `config/dpll_mgr.conf.sample` to `/etc/dpll-mgr/dpll_mgr.conf` and
set `global.phc_interface` to the NIC interface name (e.g., `eno8303np0`).

## License

BSD-3-Clause (Intel Corporation)
YNL library: GPL-2.0 OR BSD-3-Clause (Linux kernel)
