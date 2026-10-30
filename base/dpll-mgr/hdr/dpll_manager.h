/*
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Copyright (c) 2026, Intel Corporation
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived from
 *    this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */


/**
 * @file timing_manager.h
 * @brief Timing Manager Application Header
 * 
 * Definitions, structures, and function prototypes for the timing manager
 * application that monitors and forwards PTP synchronization parameters.
 */

#ifndef TIMING_MANAGER_H
#define TIMING_MANAGER_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <stdbool.h>
#include <time.h>
#include <getopt.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <sys/timex.h>
#include <arpa/inet.h>
#include <stdint.h>
#include <inttypes.h>
#include <linux/dpll.h>
#include "config_parser.h"
#include "dpll_utils.h"  /* For enum pin_source */
#include "log.h"  /* For LOG macros and LogLevel */

/* Configuration */
#define MAX_REMOTE_INSTANCES 16
#define BUFFER_SIZE 8192
#define SUBSCRIPTION_DURATION 60  /* Subscribe for 60 seconds */

/* PTP liveness backstop (Signal 1): if no PTP message is received from ptp4l
 * within this window, treat the port as down. MUST exceed the subscription-ack
 * cadence (SUBSCRIPTION_DURATION - 10), which is the only steady-state RX in
 * SW_BASED mode, with margin for one missed ack. Compile-time for now; promote
 * to JSON config only if per-deployment tuning is ever required.
 */
#define PTP_LIVENESS_TIMEOUT_SEC 75

/* GNSS-side liveness (ts2phc). The raw GNSS 1PPS into the DPLL REF4P pin keeps
 * pulsing even when ts2phc (the service that disciplines the PHC from the GNSS
 * 1PPS) is dead, so the DPLL would otherwise hold a stale lock on an
 * undisciplined reference. Probe ts2phc over its UDS on this cadence; after
 * this many consecutive no-replies, treat the GNSS source as down and
 * disconnect REF4P. Symmetric to the ptp4l/SDP0 liveness (2 strikes). */
#define TS2PHC_PROBE_INTERVAL_SEC 5
#define TS2PHC_PROBE_FAIL_STRIKES 2

/* Note: LogLevel enum and g_log_level are defined in dpll.h */

/* PTP Management Protocol Constants */
#define PTP_MANAGEMENT 0x0D
#define PTP_VERSION 0x02

/* Management Action Fields */
#define GET 0
#define SET 1
#define RESPONSE 2
#define COMMAND 3
#define ACKNOWLEDGE 4

/* Management TLV IDs - IEEE 1588-2019 */
#define MGMT_ID_NULL_MANAGEMENT                 0x0000
#define MGMT_ID_CLOCK_DESCRIPTION               0x0001
#define MGMT_ID_USER_DESCRIPTION                0x0002
#define MGMT_ID_INITIALIZE                      0x0005
#define MGMT_ID_FAULT_LOG                       0x0006
#define MGMT_ID_DEFAULT_DATA_SET                0x2000
#define MGMT_ID_CURRENT_DATA_SET                0x2001
#define MGMT_ID_PARENT_DATA_SET                 0x2002
#define MGMT_ID_TIME_PROPERTIES_DATA_SET        0x2003
#define MGMT_ID_PORT_DATA_SET                   0x2004
#define MGMT_ID_PRIORITY1                       0x2005
#define MGMT_ID_PRIORITY2                       0x2006
#define MGMT_ID_DOMAIN                          0x2007
#define MGMT_ID_TIME_STATUS_NP                  0xC000
#define MGMT_ID_GRANDMASTER_SETTINGS_NP         0xC001
#define MGMT_ID_PORT_DATA_SET_NP                0xC002
#define MGMT_ID_SUBSCRIBE_EVENTS_NP             0xC003
#define MGMT_ID_PORT_PROPERTIES_NP              0xC004
#define MGMT_ID_PORT_STATS_NP                   0xC005
#define MGMT_ID_GEARSHIFT_NP                    0xC0F0
#define MGMT_ID_GEAR_STATUS_NP                  0xC0F1

/* Gear source identifiers (matches linuxptp gear_source enum) */
#define GEAR_SRC_CONFIG  0
#define GEAR_SRC_PMC     1
#define GEAR_SRC_IPC     2
#define GEAR_SRC_LOCAL   3

static const char * const gear_source_str[] = {
    [GEAR_SRC_CONFIG] = "Config",
    [GEAR_SRC_PMC]    = "PMC",
    [GEAR_SRC_IPC]    = "IPC",
    [GEAR_SRC_LOCAL]  = "Local",
};

/* gear_status_np - response payload for MGMT_ID_GEAR_STATUS_NP GET */
struct gear_status_np {
    uint8_t  gear;    /* enum gear_mode: 0=Park 1=Neutral 2=Drive */
    uint8_t  source;  /* enum gear_source: who last changed the gear */
    uint16_t flags;   /* reserved, always 0 */
};

/* Convert file descriptor to clockid_t for PHC operations */
#ifndef FD_TO_CLOCKID
#define FD_TO_CLOCKID(fd) ((clockid_t) ((((unsigned int) ~fd) << 3) | 3))
#endif

/* Event indices for subscription (matches linuxptp NOTIFY_* definitions)
 * Note: Subscriptions in linuxptp maintain connection but DON'T push data.
 * You must still send periodic GET requests to receive updates.
 */
#define NOTIFY_PORT_STATE                       0
#define NOTIFY_TIME_SYNC                        1
#define NOTIFY_PARENT_DATA_SET                  2
#define NOTIFY_CMLDS                            3

/**
 * PTP Clock Identity - 8 bytes
 */
typedef struct {
    uint8_t id[8];
} ClockIdentity;

/**
 * PTP Timestamp
 */
typedef struct {
    uint16_t seconds_msb;
    uint32_t seconds_lsb;
    uint32_t nanoseconds;
} Timestamp;

/**
 * PTP Header - IEEE 1588-2019
 */
typedef struct __attribute__((packed)) {
    uint8_t  messageType_versionPTP;  /* messageType (4 bits) | transportSpecific (4 bits) */
    uint8_t  versionPTP_messageType;  /* versionPTP (4 bits) | reserved (4 bits) */
    uint16_t messageLength;
    uint8_t  domainNumber;
    uint8_t  minorVersionPTP;
    uint8_t  flags[2];
    uint64_t correctionField;
    uint32_t messageTypeSpecific;
    ClockIdentity sourcePortIdentity;
    uint16_t sourcePortNumber;
    uint16_t sequenceId;
    uint8_t  controlField;
    int8_t   logMessageInterval;
} PTPHeader;

/**
 * Management TLV Header
 */
typedef struct __attribute__((packed)) {
    uint16_t tlvType;
    uint16_t lengthField;
    uint16_t managementId;
} ManagementTLV;

/**
 * Clock parameters structure
 */
typedef struct {
    ClockIdentity gm_identity;
    uint8_t gm_clock_class;
    uint8_t gm_clock_accuracy;
    uint16_t gm_offset_scaled_log_variance;
    uint8_t gm_priority1;
    uint8_t gm_priority2;
    uint16_t steps_removed;
    int64_t phase_offset;  /* in nanoseconds */
    bool gm_present;
    /* TIME_STATUS_NP fields for GRANDMASTER_SETTINGS_NP */
    int16_t current_utc_offset;
    uint8_t leap61;
    uint8_t leap59;
    uint8_t current_utc_offset_valid;
    uint8_t ptp_timescale;
    uint8_t time_traceable;
    uint8_t frequency_traceable;
    uint8_t time_source;
    struct timespec last_update;
} ClockParameters;

/**
 * Remote ptp4l instance configuration
 */
typedef struct {
    char uds_path[256];
    int socket_fd;
    struct sockaddr_un peer_addr;
    bool active;
    uint16_t sequence_id;
} RemoteInstance;

/**
 * Application state
 */
typedef struct {
    char fr_uds_path[256];
    int local_socket_fd;
    struct sockaddr_un local_peer_addr;
    uint16_t local_sequence_id;
    
    RemoteInstance remotes[MAX_REMOTE_INSTANCES];
    int rx_count;
    
    ClockParameters clock_params[PIN_SOURCE_INT_OSC + 1];  /* Clock parameters indexed by pin_source */
    bool subscription_active;
    struct timespec last_subscription;
    
    uint8_t port_state;  /* Current PTP port state (MASTER, SLAVE, etc.) */
    bool is_ptp_connected_to_gm;  /* True if PTP is locked to GM */
    bool ptp_port_down; /* True while port is in FAULTY/DISABLED (sticky across intermediate states) */

    /* PTP liveness detection — detect a dead/wedged ptp4l that
     * sends no PORT_DATA_SET. Updated/consumed by the shared helpers in
     * ptp_protocol.c (ptp_check_liveness / ptp_note_subscription_result). */
    struct timespec last_ptp_rx_time;  /* Monotonic time of last message RX from ptp4l */
    int subscription_fail_count;       /* Consecutive subscription-send failures (any cause: gone socket, EAGAIN, partial send) */

    /* GNSS/ts2phc liveness detection (SW_BASED) — symmetric to the ptp4l/SDP0
     * liveness above. Probe ts2phc over its UDS (ts2_0); on repeated no-reply,
     * disconnect REF4P so the DPLL stops trusting the undisciplined GNSS 1PPS
     * and fails over / drops to holdover. */
    bool ts2phc_down;                   /* Sticky: true while ts2phc is judged dead */
    int  ts2phc_probe_fail_count;       /* Consecutive ts2phc probe failures */
    struct timespec last_ts2phc_probe;  /* Monotonic time of last ts2phc probe */
    
    /* Track current master source */
    enum pin_source current_master;  /* Current master source pin */
    enum pin_source prev_master;     /* Previous master source for transition detection */
    
    struct timespec holdover_start_time;  /* Time when holdover started */
    bool in_holdover;                     /* True if currently in holdover */
    
    enum dpll_lock_status lock_status;  /* DPLL lock status */
    __u32 connected_pin_id;  /* Currently connected DPLL pin ID (when locked) */
    
    __u32 ptp_pin_id;  /* PTP pin ID for phase adjustment */
    enum dpll_pin_state ptp_pin_state;  /* PTP pin state (for selectable check) */
    
    struct ynl_sock *dpll_sock;  /* DPLL netlink socket */
    __u32 eec_dpll_device_id;  /* DPLL EEC device ID */
    __u32 pps_dpll_device_id;  /* DPLL PPS device ID */
    
    int64_t apts_offset;  /* Phase offset from GNSS pin (APTS offset) */
    int64_t master_offset;  /* Master offset from TIME_STATUS_NP (PTP phase offset) */
    
    /* Drift tracking variables */
    int64_t drift_first_offset;  /* First offset for drift calculation */
    struct timespec drift_first_time;  /* First time for drift calculation */
    double drift_rate;  /* Current drift rate in ns/s */
    bool drift_initialized;  /* True if drift tracking initialized */
    
    PinPriorityEntry eec_priority_table[16];  /* DPLL0_FREQ map for EEC device */
    PinPriorityEntry pps_priority_table[16];  /* DPLL1_PHASE map for PPS device */

    /* Per-pin DPLL state cache — updated by update_pin_states().
     * A pin can be parented by BOTH DPLL engines of the same chip:
     *   EEC = DPLL0 (frequency/syntonization)
     *   PPS = DPLL1 (phase/time; drives current_master)
     * The two engines carry independent state and priority (e.g. an SDP
     * backhaul pin is DNU/disconnected on EEC but selectable/connected on
     * PPS), so both are cached and published rather than collapsed into one. */
    struct {
        enum dpll_pin_state eec_state;  /* state on EEC (DPLL0) device */
        enum dpll_pin_state pps_state;  /* state on PPS (DPLL1) device */
        int eec_priority;               /* priority on EEC device (-1=unset) */
        int pps_priority;               /* priority on PPS device (-1=unset) */
        bool valid;                     /* True if this pin was seen in last dump */
    } pin_states[PIN_SOURCE_INT_OSC + 1];

    int ts2phc_socket_fd;                /* Bound socket for ts2phc gearshift (SW_BASED) */
    struct sockaddr_un ts2phc_peer_addr; /* ts2phc UDS peer address (ts2_0 channel) */

    /* Second ts2phc instance (ts2_1) — the E830 fronthaul path on a
     * two-ts2phc GNR-D config. -1 when ts2_1 is not configured (one-instance
     * deployments), in which case all ts2_1 handling is skipped. */
    int ts2phc1_socket_fd;                /* Bound socket for ts2_1 gearshift (SW_BASED) */
    struct sockaddr_un ts2phc1_peer_addr; /* ts2phc UDS peer address (ts2_1 channel) */

    /* Gearshift state tracking (SW_BASED mode) — for status.json */
    uint8_t gear_ptp_bh;   /* Current gear for ptp4l channel */
    uint8_t gear_ts2_0;    /* Current gear for ts2phc channel */
    uint8_t gear_ts2_1;    /* Current gear for second ts2phc (ts2_1) channel */

    /* Previous lock status for transition detection */
    enum dpll_lock_status prev_lock_status;

    /* Boot grace: suppress "unlocked" alarm until first lock achieved */
    bool ever_locked;

    FILE *log_file;  /* Log file handle (NULL = stdout) */
} AppState;

/* Function prototypes */
void monitor_and_adjust_phase_offset(AppState *state);
void read_clock_parameters_from_master(AppState *state, struct ynl_sock *dpll_sock);

/* Global running flag - cleared by signal handler */
extern volatile sig_atomic_t running;

/* Common helpers used by both event and poll loop files */
void determine_current_master(AppState *state, struct ynl_sock *dpll_sock);
const char *pin_source_to_string(enum pin_source source);
void process_dpll_master_state(AppState *state, struct ynl_sock *dpll_sock);

/* Refresh the pin-state cache and rewrite status.json as a unit. Called by the
 * PTP port up/down handlers after a pin change that leaves the master
 * unchanged (which does not otherwise trigger a write). No-op if the DPLL
 * socket is not up. */
void refresh_pin_states_and_write(AppState *state);

/* steady-state pin reconciliation for the event-loop 1 s timeout
 * (observe live pin cache + reconcile_ptp_pins). See definition. */
void reconcile_tick(AppState *state);

/* GNSS/ts2phc liveness tick for the event-loop 1 s timeout (SW_BASED): probes
 * ts2phc on its own cadence and toggles REF4P selectable<->disconnected on a
 * confirmed liveness edge. See definition. */
void ts2phc_liveness_tick(AppState *state);

/**
 * run_main_loop - Main application loop
 * @state:     Application state
 * @dpll_sock: Initialised DPLL netlink socket
 *
 * Implemented in dpll_manager_event.c (BUILD_MODE=event) or
 * dpll_manager_poll.c (BUILD_MODE=poll).  Called from main() after
 * all initialisation is complete.
 */
void run_main_loop(AppState *state, struct ynl_sock *dpll_sock);

#endif /* TIMING_MANAGER_H */
