# APTS Manager - Assisted partial timing support manager

## Overview

APTS (Assisted Partial Timing Support) Manager is a user space reference software application based on Linux platform meant to handle time synchronization, timing failover between multiple clock source like GNSS/PTP/SyncE, holdover, and extended holdover scenarios for FlexRAN GNR-D platform which has the following hardware components with respect to the timing.
- Microchip Timing Module ZL3073x
- GNR-D Integrated PHC (PTP Hardware Clock as part of the GNR-D SoC)
- Cater Flat/Connersville(CNV) NIC PHC


## Key Features

- **Failover Support**: Detects active timing source transitions in real time and switches clock-parameter handling to the new source.
- **Holdover Support**: Detects holdover entry/exit and maintains timing behavior using holdover state handling when no valid upstream source is available.
- **Clock Parameter Forwarding to Other Leaders**: Reads timing/clock datasets from the json file and forwards synchronized parameters to configured remote ptp4l leader instances.
- **DPLL Integration**: Monitors DPLL state and applies phase/frequency adjustments for timing alignment. In HW_BASED mode, continuously monitors DPLL pin phase offset and applies incremental corrections to keep offset within bounds.
- **DPLL Pin Priority Configuration**: At startup, reads `dpll0.pin_priority_map` and `dpll1.pin_priority_map` from `apts_mgr.json` and programs pin priorities into the EEC (DPLL0/frequency) and PPS (DPLL1/phase) DPLL devices.
- **Timing Delay Compensation**: At startup, reads per-pin propagation delays from `config/timing_delays.json` and programs each DPLL pin's `phase_adjust` to compensate for board-level and system-level delays (ZL3073x only). Input (REF) and output (OUT) pin compensation can be enabled independently at compile time.
- **SW_BASED Operation Mode**: On failover, sends `GEARSHIFT_NP` PMC management messages to ptp4l and ts2phc to switch the active timing source in software, without hardware DPLL phase adjustment.
- **Gear Park / Neutral Mode on Failover**: Controls whether the idle gear on failover is set to PARK or NEUTRAL. Configurable at compile time via `USE_GEAR_PARK` (default: PARK); pass `EXTRA_CFLAGS=-UUSE_GEAR_PARK` to switch to NEUTRAL.
- **Event-Driven Mode (CPU Optimization)**: In `BUILD_MODE=event`, APTS Manager subscribes to kernel DPLL netlink multicast notifications instead of polling. This eliminates periodic netlink requests, significantly reducing CPU usage compared to poll mode.
- **Startup Master Detection and Gear Correction**: At bringup, queries the DPLL connected pin state to identify the current active timing master (GNSS, PTP, or holdover). If the detected master does not match the configured gear state in ptp4l/ts2phc, the correct gear is applied automatically — eliminating the need for manual gear pre-configuration.
- **Logging**: Provides configurable logging levels (RAW, INFO, ERROR, DEBUG) with optional file output.


## Components

### Core Files

1. **apts_manager.c** - Main application logic, initialization, and shared main loop utilities
2. **apts_mgr_event.c** - Event-based main loop (BUILD_MODE=event): subscribes to zl3073x DPLL events, listens for device status change notifications, and processes them to identify failover
3. **apts_mgr_poll.c** - Poll-based main loop (BUILD_MODE=poll): periodically polls DPLL device state via netlink; on detected state changes, reads pin states to identify failover
4. **ptp_protocol.c** - PTP management protocol message handling
5. **dpll_utils.c** - DPLL device state monitoring and pin control
6. **dpll_phase_adjust.c** - DPLL phase offset monitoring and incremental adjustment logic
7. **config_parser.c** - Boot-time configuration loader that parses `apts_mgr.json` into the application control block.
8. **gnss_utils.c** - GNSS parameter retrieval and mapping into the timing control flow.
9. **gearshift.c** - Software-based failover control. Sends `MGMT_ID_GEARSHIFT_NP` (0xC0F0) PMC management messages to ptp4l and ts2phc daemons on source transitions. Used only when `operation_mode` is `SW_BASED`.
10. **phc_utils.c** - PHC device discovery and phase/frequency adjustment utilities.
11. **timing_delays.c** - Parses `config/timing_delays.json` and programs per-pin `phase_adjust` values into the ZL3073x DPLL at startup to compensate for propagation delays.

### Key Functions

- `monitor_and_adjust_phase_offset()` - Monitors DPLL pin phase offset every second and adjusts if >5ns
- `perform_phase_adjustment()` - Applies gradual DPLL phase correction in bounded iterations to avoid large timing steps.
- `process_messages()` - Processes incoming PTP management messages
- `forward_clock_parameters()` - Forwards timing parameters to remote instances
- `dpll_get_device_state_and_connected_pin()` - Retrieves DPLL state and active pin
- `handle_sw_based_failover()` - On failover in SW_BASED mode, sends `GEARSHIFT_NP` SET messages to ptp4l and ts2phc to shift gears

## Installation Dependencies

Before building APTS Manager, ensure the following dependencies are installed:

### Required Libraries

1. **libgps** - GPS daemon library (for GNSS support)

   Build and install version `3.27.5` from source (choose one option):
   ```bash
   sudo apt-get update
   sudo apt-get install -y git build-essential scons python3 pkg-config
   ```

   Option A: clone and checkout tag
   ```bash
   git clone https://gitlab.com/gpsd/gpsd.git
   cd gpsd
   git checkout release-3.27.5
   scons -j$(nproc)
   sudo scons install
   sudo ldconfig
   ```

   Option B: download tarball directly
   ```bash
   wget https://download-mirror.savannah.gnu.org/releases/gpsd/gpsd-3.27.5.tar.gz
   tar -xzf gpsd-3.27.5.tar.gz
   cd gpsd-3.27.5
   scons -j$(nproc)
   sudo scons install
   sudo ldconfig
   ```

   Reference directory listing:
   ```text
   https://download-mirror.savannah.gnu.org/releases/gpsd/
   ```

2. **cJSON** - JSON parsing library

   Build and install pinned version:
   ```bash
   sudo apt-get update
   sudo apt-get install -y git build-essential

   git clone https://github.com/DaveGamble/cJSON.git
   cd cJSON
   git checkout v1.7.19
   make clean all
   sudo make install
   sudo ldconfig
   ```

3. **ynl (YAML Netlink)** - Netlink utility tool
   ```bash
   # Usually available from kernel source tools or as standalone utility
   # Check if installed:
   which ynl
   
   # If not installed, it may need to be built from kernel tools/net/ynl/
   ```

4. **socat (Multipurpose relay)** - command line based utility
   ```bash
   # Check if installed:
   which socat
   
   # If not installed, install by using following command
   apt install socat  
   ```

### Verification

Check if dependencies are installed:
```bash
# Check cJSON
pkg-config --modversion libcjson

# Check libgps
pkg-config --modversion libgps

# Check ynl
ynl --help
```

## Building


### Build Modes

Two build modes are available:

| Mode | Description |
|------|-----------|
| `event` | Subscribes to zl3073x DPLL events; the kernel pushes device status change notifications |
| `poll`  | Reads DPLL device and pin status by sending netlink request messages at a fixed interval |

### Quick Start

```bash

# Build with default (event mode)
make clean all

# Build in event mode (default — same as omitting BUILD_MODE)
make clean all BUILD_MODE=event

# Build in poll mode
make clean all BUILD_MODE=poll

# Build without timing delay compensation
make clean all DPLL_ZL3073X_TIMING_DELAYS=

# Build with input (REF) pin compensation disabled
make clean all EXTRA_CFLAGS=-UDPLL_IP_TIMING_DELAY

# Build with output (OUT) pin compensation disabled
make clean all EXTRA_CFLAGS=-UDPLL_OP_TIMING_DELAY
```

### Notes

- The default target builds `apts_mgr` in the workspace root. If `BUILD_MODE` is not specified, `event` mode is used by default.
- **Event mode** (`BUILD_MODE=event`): DPLL device status change notifications are received via the kernel multicast group; master transitions are detected within one kernel notification latency.
- **Poll mode** (`BUILD_MODE=poll`): DPLL device and pin status are queried periodically using netlink messages.
- In `SW_BASED` mode, DPLL phase adjustment is disabled; failover is handled exclusively via `GEARSHIFT_NP` PMC messages.

## Usage

### Basic Usage

```bash
./apts_mgr [-c <config_file>] [-o <log_file>] [-h]
```

### Command Line Options

- `-c, --config <file>` - Configuration file path (default: `config/apts_mgr.json`)
- `-o, --output <file>` - Log output file (default: stdout)
- `-h, --help` - Show help message

### Examples

**Run with default configuration:**
```bash
./apts_mgr
```

**Run with explicit config file:**
```bash
./apts_mgr -c config/apts_mgr.json
```

**Monitor with logging:**
```bash
./apts_mgr -c config/apts_mgr.json -o /var/log/apts_mgr.log
```

leader/free running ptp4l UDS paths are configured in `config/apts_mgr.json`.
If there is any change, updates are also needed in the config file.

## Prerequisites to run

### Required

- Linux kernel with DPLL subsystem support (Tested with v6.19-rc4, and ice-2.5.0_rc2)
- ptp4l (from linuxptp) — configuration depends on operation mode (see below)
- ts2phc (from linuxptp) — required in SW_BASED mode for GNSS source control

### ptp4l Configuration

The required ptp4l configuration depends on the `operation_mode` set in `apts_mgr.json`:

**HW_BASED mode** — ptp4l runs in free-running mode:
```bash
ptp4l -i <interface> -m -l 7 -f config/ptp4l_time_receiver.cfg
```
```ini
[global]
free_running 1
```

**SW_BASED mode** — ptp4l runs as a time receiver (software timestamping, NOT free-running):
```bash
ptp4l -i <interface> -m -l 7 -f config/ptp4l_time_receiver.cfg
```
The `start_services.sh` script automatically selects the correct config based on the `MODE` environment variable (`SW_BASED` or `HW_BASED`, default: `SW_BASED`).

Example ptp4l configuration files are available in the `config/` directory.

## Configuration

### Runtime Configuration

- Main configuration file: `config/apts_mgr.json` (or custom path via `-c`)
- Channel mapping: time-receiver channel (`ptp_fr`/`ptp_bh`), clock-param receiver channels (`ptp_0`, `ptp_1`, `ptp_2`, ...), and ts2phc channels (`ts2_0`, `ts2_1`, `ts2_2`)
- DPLL policy/settings: pin priority maps and holdover duration thresholds
- Log destination: stdout by default, file path via `-o`

### Operation Mode

Set via `operation_mode` in the `global` section of `config/apts_mgr.json`:

```json
{
  "global": {
    "operation_mode": "SW_BASED"
  }
}
```

| Mode | Value | Description |
|------|-------|-------------|
| Hardware-based | `HW_BASED` | DPLL drives switching; phase offset adjusted via DPLL pin commands. ptp4l runs in free-running mode. |
| Software-based | `SW_BASED` | On failover, `GEARSHIFT_NP` PMC messages are sent to ptp4l and ts2phc. No DPLL phase adjustment. ptp4l runs as a time receiver. |

**Gearshift state machine (SW_BASED mode):**

| Event | ptp4l (`ptp_bh`) | ts2phc (`ts2_0`) |
|-------|-----------------|------------------|
| Failover → GNSS | NEUTRAL | DRIVE |
| Failover → PTP  | DRIVE   | NEUTRAL |

Gear values: `PARK=P`, `NEUTRAL=N`, `DRIVE=D`

### Timing Delay Compensation

At startup, APTS Manager reads `config/timing_delays.json` and programs each ZL3073x DPLL pin's `phase_adjust` register to compensate for accumulated propagation delays across the timing path.

#### Output pin granularity rounding

For output pins (`OUT*`), the ZL3073x hardware enforces a `phase_adjust_gran` granularity constraint. The computed total is rounded to the nearest multiple of this granularity before being applied. If the rounded value would be zero but the computed total is non-zero, the granularity step itself is used as the minimum adjustment.

#### JSON format

The first object in the array is a header row (non-numeric values) and is skipped automatically. Each subsequent object identifies a pin by the `"DPLL"` key matching the hardware package label (e.g., `REF0P`, `OUT3`).

```json
[

  {
    "DPLL": "REF0P",
    "Timing Module (ps)": 130,
    "Motherboard (ps)": 5732,
    "System (ps)": 0,
    "Add-in Card (ps)": 0,
    "Integrator Adjustment (ps)": 0,
    "Total (ps)": 5862
  }
]
```

#### Enabling / disabling

Timing delay compensation is enabled by default. It is controlled in the Makefile by the `DPLL_ZL3073X_TIMING_DELAYS` variable:

```makefile
# In Makefile — comment out this line to disable all timing delay compensation:
DPLL_ZL3073X_TIMING_DELAYS := 1
```

Or pass it on the command line to disable without editing the Makefile:

```bash
make clean all DPLL_ZL3073X_TIMING_DELAYS=
```

When disabled, `timing_delays.c` is not compiled and none of the `timing_delays_*` / `apply_timing_delays_phase_adjust` functions are linked or called.

#### Per-direction filtering (input / output pins)

When `DPLL_ZL3073X_TIMING_DELAYS` is enabled, compensation for input (REF) and output (OUT) pins can be controlled independently at compile time via two sub-macros:

| Macro | Controls | Default |
|-------|----------|---------|
| `DPLL_IP_TIMING_DELAY` | Input (REF\*) pin compensation | Enabled |
| `DPLL_OP_TIMING_DELAY` | Output (OUT\*) pin compensation | Enabled |

Comment out either line in the Makefile to disable that direction:

```makefile
# Disable output pin compensation only (keep input pin compensation):
# CFLAGS += -DDPLL_OP_TIMING_DELAY

# Disable input pin compensation only (keep output pin compensation):
# CFLAGS += -DDPLL_IP_TIMING_DELAY
```

Or selectively disable on the command line:

```bash
# Disable output (OUT) pin compensation only:
make clean all EXTRA_CFLAGS=-UDPLL_OP_TIMING_DELAY

# Disable input (REF) pin compensation only:
make clean all EXTRA_CFLAGS=-UDPLL_IP_TIMING_DELAY
```

> **Note**: `DPLL_IP_TIMING_DELAY` and `DPLL_OP_TIMING_DELAY` have no effect unless `DPLL_ZL3073X_TIMING_DELAYS` is also enabled.

### Log Levels

- `LOG_RAW` - Important status messages (always shown)
- `LOG_INFO` - Informational messages (Default )
- `LOG_ERROR` - Error messages
- `LOG_DEBUG` - Debug messages (compile-time enabled with -DDEBUG)

### Key Log Messages

```
Timing Manager Starting...
Configuration loaded successfully from: config/apts_mgr.json
DPLL netlink initialized successfully
Operation Mode: EVENT-BASED (SUBSCRIBE_EVENTS_NP subscription)
FAILOVER DETECTED: <old_source> -> <new_source>
```

### Common Issues

1. **Leap second issue**
   - If a leap second is observed while starting synchronization services, set the time of day again in normal mode, then restart synchronization services.

2. **`ice` driver reload**
   - After reloading the `ice` driver, verify the PHC mapping and update configuration/scripts if needed.
   - Check with:
     ```bash
     ethtool -T <phc interface>
     ```

3. **Not receiving messages from ptp4l / Failed to send message to ptp4l**
   - Check that the PTP domain number matches the grandmaster's domain number in all of the following:
     1. `config/apts_mgr.json`
     2. PTP configuration files (e.g., `config/ptp4l_*.cfg`)
     3. TS2PHC configuration files (e.g., `config/ts2phc_*.cfg`)
     4. `hdr/apts_manager.h` — defines the domain number used when sending PMC management messages
   - If the domain number is correct, restart the `ptp4l` process.

4. **Grandmaster change or PTP domain number change**
   - Update the domain number in all files listed in issue #3 above.

5. **Kernel headers not available in default include directories**
   - If kernel headers are missing from the default include paths and the kernel is installed from a repository, install them with:
     ```bash
     make headers_install INSTALL_HDR_PATH=/usr
     ```

6. **ynl library not installed**
   - If the ynl library is not available, build and install it from the kernel source repository:
     ```bash
     cd tools/net/ynl
     make
     make install
     ```

7. **ptp4l backhaul port not reaching TIME_RECEIVER state**
   - Verify that PTP packets are arriving on the grandmaster-facing interface:
     ```bash
     tcpdump -i <backhaul_interface> -n udp port 319 or udp port 320
     ```
   - If no PTP packets are seen, the grandmaster may be connected to a different interface. Identify the correct interface and update the ptp4l startup command (`-i` option) and `config/apts_mgr.json` UDS paths accordingly.

8. **Redeclaration of `dpll_lock_status_error` or `dpll_feature_state`**
   - This gap exists only in certain kernel versions where `ynl/dpll-user.h`
     is newer than `linux/dpll.h` and references `dpll_lock_status_error` and
     `dpll_feature_state` enum types that the corresponding `linux/dpll.h` does
     not yet define. On kernels where `linux/dpll.h` has caught up and defines
     these enums, the stub declarations in `hdr/dpll_utils.h` cause a
     redeclaration conflict.
   - `hdr/dpll_utils.h` contains stub/dummy declarations of these enums as a
     compatibility shim for those affected kernel versions.
   - On kernels where `linux/dpll.h` already defines these enums, the compiler
     will report a redeclaration error.
   - **Fix**: comment out the conflicting declarations in `hdr/dpll_utils.h`:
     ```c
     /* Comment out if linux/dpll.h already defines these enums */
     // #ifndef DPLL_A_LOCK_STATUS_ERROR
     // enum dpll_lock_status_error {
     //         DPLL_LOCK_STATUS_ERROR_UNSPEC = 0,
     // };
     // #endif

     // #ifndef DPLL_A_PHASE_OFFSET_MONITOR
     // enum dpll_feature_state {
     //         DPLL_FEATURE_STATE_UNSPEC = 0,
     // };
     // #endif
     ```


## Testing

### Basic Functionality Test

```bash
# Extract the release package and enter the directory
$ tar -xzvf apts_mgr-<VERSION>.tar.gz
$ cd apts_mgr-<VERSION>

# Bring-up steps
# COMMON NOTE (all scripts):
# If using these scripts, log messages are redirected to $HOME/ptp_logs.
# Please modify the scripts based on your platform.

1) Configure DPLL mode
$ ./scripts/configure_ptp_pins.sh

# NOTE (configure_ptp_pins.sh):
# i) Update the interface names to GNR-D NAC PF0 in the script.
# ii) If the ice driver is reloaded, the PHC device file may change.
#     Get the device file from: ethtool -T <interface>
# iii) This script uses NIC-specific sysfs nodes and pin names (SDP0/SDP1/SDP2, ptp0,
#      tspll_cfg, phy/tx_clk). Adjust these based on your NIC/driver capabilities.
# iv) Check the PTP domain number in the config files and edit if required to match
#     the grandmaster's domain number.

2) Set time of day
# i) Start phc2sys:
$ phc2sys -s /dev/ptp0 -O -37 -w -m -c CLOCK_REALTIME -z /var/run/ptp_bh.ptp4l --domain 0
Observe that phc2sys process waits for ptp4l to get started

# ii) Start ptp4l:
# ifconfig eno8303np0 up
$ ptp4l -i eno8303np0 -m -l 6 -f ./config/ptp4l_time_receiver_tod.cfg

Verify that the host time is synchronized with UTC by checking against
https://time.is/UTC, then stop both processes.

3) Start synchronization services
# Optionally, pass the linuxptp source directory as the first argument:
# Note: If using a patched linuxptp build from a custom directory, pass that
# directory as the argument so the script picks up the correct binaries.
# This script uses the cfg files in config directory and assume GNSS is the
# initial master. APTS Manager will auto-detect the current master at bringup
# and correct the gear if required.
$ ./scripts/start_services.sh [/path/to/linuxptp]

# NOTE (start_services.sh):
# Update the interface names as per your platform.
# Also verify platform-specific defaults in the script:
# - CPU affinity for free-running ptp4l (PTP_FR_CPU, default: 39)
# - UTC offset used by phc2sys (currently -37)
# - Set the default gear (gear X) for ts2phc and ptp4l processes based on current master
# - default config assumes GNSS as the current master
# - UDS/domain defaults (/var/run/ptp_*.ptp4l, domain 0)
# - /etc/linuxptp configuration file install path and permissions

# If the above scripts fails start the processes manually.use the following
# commands to start ptp4l processes (paths must match config/apts_mgr.json):
$ ptp4l -i <iface_fr> -m -l 7 -f config/ptp4l_time_receiver.cfg
$ ptp4l -i <iface_0> -m -l 7 -f config/ptp4l_0.cfg
# Start socat to duplicate the NMEA stream from gpsd to ts2phc instances
# (one socat per ts2phc instance; default ports 2948 and 2949)
$ socat EXEC:'gpspipe -r' TCP-LISTEN:2948,reuseaddr,fork >> $HOME/ptp_logs/socat_nmea.log 2>&1 &
$ socat EXEC:'gpspipe -r' TCP-LISTEN:2949,reuseaddr,fork >> $HOME/ptp_logs/socat_nmea_cf.log 2>&1 &

# NOTE (socat):
# - Ensure gpsd is running and a GNSS device is available before starting socat.
# - The port numbers must match ts2phc.nmea_remote_port in the ts2phc config files.
# - Each ts2phc instance requires its own socat listener on a separate port.

# Start ts2phc instances (GNSS PPS source)
$ ts2phc -f config/ts2phc.cfg -s nmea -m -l 7 >> $HOME/ptp_logs/ts2phc_out.log 2>&1 &
$ ts2phc -f config/ts2phc_cf.cfg -s nmea -m -l 7 >> $HOME/ptp_logs/ts2phc_cf_out.log 2>&1 &

# NOTE (ts2phc):
# - ts2phc.nmea_remote_port in each config file must match the corresponding socat port.
# - The gear in ts2phc config should be set based on the current master:
#   GNSS master: ts2phc gear = D (DRIVE), ptp4l gear = P (PARK)
#   PTP master:  ts2phc gear = P (PARK),  ptp4l gear = D (DRIVE)

# Run APTS Manager
# NOTE: Before starting, verify the domain number in config/apts_mgr.json matches
#       the grandmaster's PTP domain number and edit if required.
$ ./apts_mgr -c config/apts_mgr.json -o test.log

# Verify operation
$ tail -f test.log
```

### Multi-Instance Test

```bash
# Terminal 1: Start ptp4l instances
$ ptp4l -i <iface_fr> -m -l 7 -f config/ptp4l_time_receiver_fr.cfg
$ ptp4l -i <iface_0> -m -l 7 -f config/ptp4l_0.cfg
$ ptp4l -i <iface_1> -m -l 7 -f config/ptp4l_1.cfg
$ ptp4l -i <iface_2> -m -l 7 -f config/ptp4l_2.cfg

# Terminal 2: Run APTS Manager
$ ./apts_mgr -c config/apts_mgr.json \
             -o apts_mgr.log
```

## Known Issues
- Time offset is not converging to 0 in case of PTP is driving the Timing Module and the PTP DPLL input pin REF0N phase is adjusted by the apts_mgr (HW_BASED mode).
- In some deployments, ptp4l may intermittently flip between LISTENING and UNCALIBRATED states when Announce/Sync messages are briefly interrupted; verify `domainNumber` and `transportSpecific` match the GM profile, and tune `logAnnounceInterval`/`announceReceiptTimeout` (with expected behavior when `free_running 1` is enabled in HW_BASED mode).
- When the PTP port goes down and then comes back up, APTS Manager may not receive a port-up notification because ptp4l is running in free-running mode (HW_BASED). In this case, the PTP pin state needs to be moved manually to the selectable state.
- In SW_BASED mode, if a `GEARSHIFT_NP` response is not received within 500 ms (e.g., ts2phc not running), apts_mgr logs an error and continues; the gear state of the unresponsive daemon remains unchanged.


## Support

For issues/questions, please refer to SECURITY.md.


## References

- [IEEE 1588-2019 (PTP v2)](https://standards.ieee.org/standard/1588-2019.html)
- [linuxptp Documentation](http://linuxptp.sourceforge.net/)
- [Linux DPLL Subsystem](https://www.kernel.org/doc/html/latest/driver-api/dpll.html)
- [BUILD_MODES.md](BUILD_MODES.md) - Detailed build instructions
