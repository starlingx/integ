# ovs-access-monitor

OVS Access Bridge Failover Monitor for StarlingX.

## Overview

`ovs-access-monitor` is a systemd service that continuously monitors the health
of the OVS agent pod and manages PF (Physical Function) interface membership in
the `ovs0` Linux bridge. It acts as a host-level safety net ensuring that the
platform always has network connectivity through `ovs0` — either via the OVS
pod's veth interface (preferred) or the PF (fallback).

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│  HOST                                                             │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐       │
│  │  ovs-access-monitor.service (systemd, Type=simple)     │       │
│  │                                                        │       │
│  │  Reads: /etc/ovs-access-monitor/ovs-access-monitor.conf│       │
│  │    failover_interface=eno8403                          │       │
│  │    monitoring_period=0.5                               │       │
│  │                                                        │       │
│  │  Loop every monitoring_period:                         │       │
│  │    1. Query http://localhost:19082/status              │       │
│  │    2. Decide state → HEALTHY or UNHEALTHY              │       │
│  │    3. Enforce desired bridge membership on ovs0        │       │
│  └───────────┬────────────────────────────────────────────┘       │
│              │                                                    │
│              ▼                                                    │
│  ┌─────── ovs0 (Linux bridge) ────────┐                           │
│  │                                    │                           │
│  │  Members (mutual exclusion):       │                           │
│  │   • failover_interface (PF)  ←── when pod UNHEALTHY            │
│  │   • <ifname>-ovs (veth)     ←── always present (created        │
│  │                                  by create_ovs_access)         │
│  └─────────────────────────────────────┘                          │
│                                                                   │
│              ▲                                                    │
│              │ host0 veth (pod-side of NAD)                       │
│  ┌───────────┴────────────────────────────────────────────┐       │
│  │  ovs-agent-operator pod                                │       │
│  │   - OVS bridges with real ports                        │       │
│  │   - /status endpoint on hostPort 19082                 │       │
│  └────────────────────────────────────────────────────────┘       │
└───────────────────────────────────────────────────────────────────┘
```

## State Machine

The monitor maintains a two-state FSM and also manages the veth interface
(created by bridge-cni, named `veth<hash>`) attached to `ovs0`:

| State | Meaning | PF in ovs0? | veth state | Traffic path |
|-------|---------|-------------|------------|--------------|
| **POD_HEALTHY** | OVS pod is operational | **No** | UP | Host ↔ veth ↔ OVS pod bridges |
| **POD_UNHEALTHY** | OVS pod is not ready | **Yes** | DOWN | Host ↔ PF ↔ physical network |

Additionally, if no veth interface is found on the bridge at all (pod never
started or veth was removed), the PF is forced into the bridge regardless of
other state.

## Decision Logic

Each monitoring cycle:

1. HTTP GET `http://localhost:<status_port>/status` (default port 19082).
2. If the response is HTTP 200 with `{"healthy": true}`, the pod is considered
   healthy.
3. Any connection error, timeout, non-200 status, or `healthy: false` is treated
   as unhealthy.
4. Discover the veth interface on the bridge (name starts with `veth` followed
   by a hash, e.g. `vethf43858ac`).

State transitions:

- **To HEALTHY**: A single healthy reading immediately removes the PF from the
  bridge and sets the veth interface UP (both idempotent).
- **To UNHEALTHY**: Requires `unhealthy_threshold` (default: 3) consecutive
  unhealthy readings before adding the PF back to the bridge and setting the
  veth DOWN. This hysteresis prevents flapping during transient pod restarts.
- **No veth on bridge**: If no veth interface is found as a member of `ovs0`,
  the PF is forced into the bridge unconditionally. This covers the case where
  the pod has not started yet or the bridge-cni veth was removed.

## Configuration

The configuration file is located at
`/etc/ovs-access-monitor/ovs-access-monitor.conf`. It uses a simple
`key=value` format:

```ini
# PF interface that provides fallback connectivity to the ovs0 bridge.
# (Required - no default)
failover_interface=eno8403

# Polling interval in seconds (supports fractional values, e.g. 0.5 = 500ms).
# (Default: 0.5)
monitoring_period=0.5

# TCP port where the OVS agent pod exposes its /status HTTP endpoint.
# (Default: 19082)
# status_port=19082

# Name of the Linux bridge to manage.
# (Default: ovs0)
# bridge_name=ovs0

# Number of consecutive unhealthy readings before switching to PF fallback.
# (Default: 3)
# unhealthy_threshold=3
```

The configuration file path can be overridden via the
`OVS_ACCESS_MONITOR_CONF` environment variable.

## Systemd Service

The service is installed as `ovs-access-monitor.service`:

```ini
[Unit]
Description=OVS Access Bridge Failover Monitor
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/ovs-access-monitor
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
systemctl enable --now ovs-access-monitor.service
```

## Integration with Related Changes

This service is part of a three-component system:

1. **ifupdown scripts** (`create_ovs_access` / `delete_ovs_access` from
   `starlingx/integ` change 991162): Creates the `ovs0` Linux bridge, attaches
   the PF, creates the veth pair for the pod, writes the configuration file,
   and enables/starts this service.

2. **OVS agent pod** (`starlingx/app-openvswitch` change 991309): The pod's
   `bridge-failover.sh` lifecycle hooks remove the PF on start and re-add it
   on graceful stop. The pod exposes an HTTP `/status` endpoint on hostPort
   19082 reporting bridge health.

3. **This service** (`ovs-access-monitor`): Continuously monitors the pod
   health endpoint and enforces PF membership as a safety net, covering cases
   where the pod dies unexpectedly (OOMKill, SIGKILL) and the `preStop` hook
   cannot fire.

## Scenarios

| Scenario | Behavior |
|----------|----------|
| Pod starts normally | Pod's `bridge-failover.sh start` removes PF; monitor confirms healthy, removes PF (idempotent), sets veth UP |
| Pod stops gracefully | Pod's `bridge-failover.sh stop` adds PF back; monitor detects unhealthy, adds PF, sets veth DOWN |
| Pod dies unexpectedly | No preStop fires; within `monitoring_period × unhealthy_threshold` seconds the monitor adds PF back and sets veth DOWN |
| Pod recovers | Status goes healthy; monitor removes PF and sets veth UP |
| Service starts before pod exists | Endpoint unreachable, no veth on bridge → PF stays in bridge (correct initial state) |
| Bridge does not exist yet | Monitor waits in preflight loop until `create_ovs_access` creates it |
| Failover interface missing | Logged as error, enforcement skipped, monitor keeps polling |
| No veth on bridge | PF forced into bridge regardless of pod status |

## Debugging

Enable debug logging by setting the environment variable:

```bash
OVS_ACCESS_MONITOR_DEBUG=1
```

Or override in the systemd unit:

```bash
systemctl edit ovs-access-monitor.service
```

Add the following lines, it will be added to the override section:
```ini
[Service]
Environment=OVS_ACCESS_MONITOR_DEBUG=1
```

View logs:

```bash
cat /var/log/daemon.log | grep ovs-access-monitor
```

To turn-off the debug:
```bash
systemctl revert ovs-access-monitor.service
```
This deletes the override file and reloads the daemon in one step.


## Package Contents

```
networking/ovs-access-monitor/
├── PKG-INFO
├── LICENSE
├── README.md
├── config/
│   └── ovs-access-monitor.conf.sample
├── scripts/
│   └── ovs-access-monitor              ← main Python daemon
├── systemd/
│   └── ovs-access-monitor.service      ← systemd unit file
└── debian/
    ├── bullseye/
    │   ├── meta_data.yaml
    │   └── deb_folder/
    └── trixie/
        ├── meta_data.yaml
        └── deb_folder/
```

## Dependencies

- Python 3 (standard library only — no pip packages required)
- iproute2 (`ip` command)
- systemd
