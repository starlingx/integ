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
 * @file timing_manager.c
 * @brief Timing Manager Application
 * 
 * This application:
 * 1. Accepts local and remote ptp4l pid files as command line arguments
 * 2. Communicates directly with ptp4l using PMC interface
 * 3. Subscribes to receive GM state info, clock parameters, and phase offset
 * 4. Logs phase offset warnings when > 5 nsec
 * 5. Forwards clock parameters to all remote ptp4l processes
 * 6. Monitors DPLL state and selects clock parameter source based on connected pin:
 *    - REF4P/REF4N (GNSS) -> get_gnss_parameters()
 *    - REF0P/REF0N (SyncE) -> get_synce_parameters()
 *    - Holdover state -> get_holdover_parameters()
 */

#define _DEFAULT_SOURCE
#define MODULE "SM"
#include "../hdr/apts_manager.h"
#include "../hdr/dpll_utils.h"
#include "../hdr/ptp_protocol.h"
#include "../hdr/gnss_utils.h"
#include "../hdr/config_parser.h"
#include "../hdr/phc_utils.h"
#include "../hdr/dpll_phase_adjust.h"
#include "../hdr/gearshift.h"
#include "../hdr/status_writer.h"
#include "../hdr/timing_delays.h"
#include <poll.h>
#include <ynl/ynl.h>

#ifndef APTS_MGR_VERSION
#define APTS_MGR_VERSION "unknown"
#endif

/* Global flag for signal handling - cleared by signal_handler(), read by loop files */
volatile sig_atomic_t running = 1;

/* Global log file pointer */
FILE *g_log_file = NULL;

/* Global log level - defaults to INFO */
LogLevel g_log_level = LOG_LEVEL_INFO;

/* External YNL socket from dpll.c */
extern struct ynl_sock *ys;

/* Forward declarations */
static bool initialize_state(AppState *state, const char *fr_uds_path,
                             char **rx_uds_paths, int rx_count);


/**
 * Signal handler
 */
static void signal_handler(int signum)
{
    (void)signum;
    running = 0;
}

/**
 * Ensure runtime directory exists with secure permissions
 */
/**
 * Ensure runtime directory exists with secure permissions
 */
static int ensure_runtime_directory(void)
{
    const char *runtime_dir = "/var/run/apts_mgr";
    struct stat st;

    /* Try to create directory first (atomic operation) */
    if (mkdir(runtime_dir, 0755) < 0) {
        if (errno == EEXIST) {
            /* Verify it's actually a directory */
            if (stat(runtime_dir, &st) == 0 && S_ISDIR(st.st_mode)) {
                return 0;
            }
            LOG_ERROR("%s exists but is not a directory\n", runtime_dir);
            return -1;
        }
        LOG_ERROR("Failed to create runtime directory\n");
        return -1;
    }

    LOG_DEBUG("Runtime directory created successfully\n");
    return 0;
}

/**
 * Setup signal handlers
 */
static int setup_signals(void)
{
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = signal_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    
    if (sigaction(SIGINT, &sa, NULL) < 0) {
        LOG_ERROR("Failed to setup SIGINT handler\n");
        return -1;
    }
    if (sigaction(SIGTERM, &sa, NULL) < 0) {
        LOG_ERROR("Failed to setup SIGTERM handler\n");
        return -1;
    }
    return 0;
}

/**
 * Create and connect Unix domain socket
 */
static int create_uds_socket(const char *path, struct sockaddr_un *peer_addr)
{
    static int socket_counter = 0;  /* To make each socket unique */
    
    int sockfd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        LOG_ERROR("socket() failed: %s\n", strerror(errno));
        return -1;
    }

    // Bind to a local address so we can receive replies
    // Use socket_counter to make each socket's bind path unique
    struct sockaddr_un local_addr;
    memset(&local_addr, 0, sizeof(local_addr));
    local_addr.sun_family = AF_UNIX;
    int ret = snprintf(local_addr.sun_path, sizeof(local_addr.sun_path), 
             "/var/run/apts_mgr/timing_mgr.%d.%d", getpid(), socket_counter++);
    if (ret < 0 || ret >= (int)sizeof(local_addr.sun_path)) {
        LOG_ERROR("Socket path truncation detected\n");
        close(sockfd);
        return -1;
    }
    
    // Remove any existing socket file
    unlink(local_addr.sun_path);
    
    if (bind(sockfd, (struct sockaddr *)&local_addr, sizeof(local_addr)) < 0) {
        LOG_ERROR("bind() failed for %s: %s\n", local_addr.sun_path, strerror(errno));
        close(sockfd);
        return -1;
    }
    
    /* Set socket file permissions (0660 - owner+group, matching ptp4l) */
    if (chmod(local_addr.sun_path, 0660) < 0) {
        LOG_ERROR("chmod() failed for %s: %s\n", local_addr.sun_path, strerror(errno));
        close(sockfd);
        return -1;
    }

    LOG_DEBUG("Socket bound successfully\n");

    // Set socket to non-blocking mode
    int flags = fcntl(sockfd, F_GETFL, 0);
    if (flags == -1) {
        LOG_ERROR("fcntl(F_GETFL) failed: %s\n", strerror(errno));
        close(sockfd);
        return -1;
    }
    if (fcntl(sockfd, F_SETFL, flags | O_NONBLOCK) == -1) {
        LOG_ERROR("fcntl(F_SETFL) failed: %s\n", strerror(errno));
        close(sockfd);
        return -1;
    }

    // Store peer address for sendto() - don't call connect()
    memset(peer_addr, 0, sizeof(*peer_addr));
    peer_addr->sun_family = AF_UNIX;
    strncpy(peer_addr->sun_path, path, sizeof(peer_addr->sun_path) - 1);

    return sockfd;
}

/**
 * Cleanup application state
 */
static void cleanup_state(AppState *state)
{
    if (state->local_socket_fd >= 0) {
        close(state->local_socket_fd);
        char temp_path[256];
        int ret = snprintf(temp_path, sizeof(temp_path), "/var/run/apts_mgr/timing_mgr.%d.0", getpid());
        if (!(ret < 0 || ret >= (int)sizeof(temp_path))) {
            unlink(temp_path);
        }
    }
    
    for (int i = 0; i < state->rx_count; i++) {
        if (state->remotes[i].socket_fd >= 0) {
            close(state->remotes[i].socket_fd);
            char temp_path[256];
            int ret = snprintf(temp_path, sizeof(temp_path), "/var/run/apts_mgr/timing_mgr.%d.%d", getpid(), i + 1);
            if (!(ret < 0 || ret >= (int)sizeof(temp_path))) {
                unlink(temp_path);
            }
        }
    }

    if (state->ts2phc_socket_fd >= 0) {
        close(state->ts2phc_socket_fd);
        char temp_path[256];
        int ret = snprintf(temp_path, sizeof(temp_path), "/var/run/apts_mgr/timing_mgr.%d.ts2", getpid());
        if (ret > 0 && ret < (int)sizeof(temp_path))
            unlink(temp_path);
        state->ts2phc_socket_fd = -1;
    }
}

/**
 * get_gnss_parameters - Get parameters from GNSS
 * @state: Application state
 * @master_index: Master index (GNSS_REF4P or GNSS_REF4N)
 * 
 * Calls gnss_read_clock_params() to get live GNSS data and overrides
 * dynamically changeable parameters in ClockParameters structure.
 * time_source, ptp_timescale are static parameters, these are preserved from config.
 * gm_identity is copied from PTP index (local clock identity).
 */
static int get_gnss_parameters(AppState *state, enum pin_source master_index)
{
    if (!state) {
        LOG_ERROR("get_gnss_parameters: NULL state pointer\n");
        return -1;
    }
    
    ClockParameters *params = &state->clock_params[master_index];
    
    gnss_clock_params_t gnss_params;
    memset(&gnss_params, 0, sizeof(gnss_params));
    
#ifndef STATIC_PARAMS_FROM_CONFIG
    /* Read current GNSS parameters */
    int ret = gnss_read_clock_params(&gnss_params);
    if (ret != 0) {
        LOG_ERROR("Failed to read GNSS clock parameters: %d\n", ret);
        return -1;
    }
    
    if (!gnss_params.connected) {
        LOG_ERROR("GNSS not connected\n");
        return -1;
    }
    
    LOG_INFO("Getting parameters from GNSS (connected, fix quality: %d)\n", gnss_params.clock_quality);
    
    /* Update ONLY dynamically changeable parameters with live GNSS data */
    /* Static parameters (time_source, ptp_timescale) are preserved from config */
    
    params->gm_clock_class = gnss_params.ptp_clock_class;
    params->gm_clock_accuracy = gnss_params.ptp_clock_accuracy;
    params->gm_offset_scaled_log_variance = gnss_params.ptp_offset_scaled_log_variance;

    
    /* UTC offset and leap second information - from GNSS satellites */
    params->current_utc_offset = gnss_params.current_utc_offset;
    params->current_utc_offset_valid = gnss_params.current_utc_offset_valid ? 1 : 0;
    params->leap61 = gnss_params.leap61 ? 1 : 0;
    params->leap59 = gnss_params.leap59 ? 1 : 0;
    
    /* Traceability - based on current fix status (dynamic) */
    params->time_traceable = gnss_params.time_traceable ? 1 : 0;
    params->frequency_traceable = gnss_params.frequency_traceable ? 1 : 0;
#endif
    /* NOTE: time_source and ptp_timescale are NOT updated here - they remain as 
     * configured in apts_mgr.json since they're static for GNSS (GPS = 0x20) */
    
    /* Copy gm_identity from PTP index (local clock identity) */
    /* When acting as grandmaster (on GNSS), use our local clock identity */
    params->gm_identity = state->clock_params[SDP2_REF0P].gm_identity;
    
    /* Mark GM as present when we have valid GNSS data */
    params->gm_present = 1;
    
    /* Update timestamp */
    clock_gettime(CLOCK_REALTIME, &params->last_update);
    
    LOG_DEBUG("GNSS parameters updated: clockClass=%u, clockAccuracy=0x%02X, UTC offset=%d, timeSource=0x%02X\n",
             params->gm_clock_class, params->gm_clock_accuracy, 
             params->current_utc_offset, params->time_source);
    
    return 0;
}

/**
 * get_synce_parameters - Dummy function to get parameters from SyncE
 * TODO: Implement SyncE parameter retrieval
 */
__attribute__((unused))
static int get_synce_parameters(ClockParameters *params)
{
    (void)params;  /* Unused parameter */
    LOG_INFO("Getting parameters from SyncE (TODO: implement)\n");
    // TODO: Implement SyncE parameter extraction
    return -1;  // Not implemented yet
}

/**
 * pin_name_to_enum - Convert pin name string to pin_source enum
 * @pin_name: Pin name string (e.g., "SDP2_REF0P", "GNSS_REF4P")
 *
 * Returns: pin_source enum value, or PIN_SOURCE_UNKNOWN if not found
 */
static enum pin_source pin_name_to_enum(const char *pin_name)
{
    if (!pin_name || pin_name[0] == '\0') {
        return PIN_SOURCE_UNKNOWN;
    }
    
    /* Map pin name strings to enum values */
    if (strcmp(pin_name, "SDP2_REF0P") == 0) return SDP2_REF0P;
    if (strcmp(pin_name, "SDP0_REF0N") == 0) return SDP0_REF0N;
    if (strcmp(pin_name, "GNSS_REF4P") == 0) return GNSS_REF4P;
    if (strcmp(pin_name, "GNSS_REF4N") == 0) return GNSS_REF4N;
    if (strcmp(pin_name, "RCLKA_REF1P") == 0) return RCLKA_REF1P;
    if (strcmp(pin_name, "RCLKB_REF1N") == 0) return RCLKB_REF1N;
    if (strcmp(pin_name, "SMA1_REF3P") == 0) return SMA1_REF3P;
    if (strcmp(pin_name, "SMA3_REF3N") == 0) return SMA3_REF3N;
    if (strcasecmp(pin_name, "HOLDOVER_0") == 0 || strcasecmp(pin_name, "Holdover_0") == 0) return HOLDOVER_0;
    if (strcasecmp(pin_name, "HOLDOVER_1") == 0 || strcasecmp(pin_name, "Holdover_1") == 0) return HOLDOVER_1;
    if (strcasecmp(pin_name, "HOLDOVER_2") == 0 || strcasecmp(pin_name, "Holdover_2") == 0) return HOLDOVER_2;
    if (strcasecmp(pin_name, "HOLDOVER_3") == 0 || strcasecmp(pin_name, "Holdover_3") == 0) return HOLDOVER_3;
    if (strcmp(pin_name, "PIN_SOURCE_INT_OSC") == 0) return PIN_SOURCE_INT_OSC;
    
    LOG_ERROR("Unknown pin name: %s\n", pin_name);
    return PIN_SOURCE_UNKNOWN;
}

/**
 * pin_source_to_string - Convert pin_source enum to string name
 * @source: pin_source enum value
 *
 * Returns: String name of the pin source
 */
const char* pin_source_to_string(enum pin_source source)
{
    switch (source) {
        case SDP2_REF0P: return "SDP2_REF0P";
        case SDP0_REF0N: return "SDP0_REF0N";
        case GNSS_REF4P: return "GNSS_REF4P";
        case GNSS_REF4N: return "GNSS_REF4N";
        case RCLKA_REF1P: return "RCLKA_REF1P";
        case RCLKB_REF1N: return "RCLKB_REF1N";
        case SMA1_REF3P: return "SMA1_REF3P";
        case SMA3_REF3N: return "SMA3_REF3N";
        case HOLDOVER_0: return "HOLDOVER_0";
        case HOLDOVER_1: return "HOLDOVER_1";
        case HOLDOVER_2: return "HOLDOVER_2";
        case HOLDOVER_3: return "HOLDOVER_3";
        case PIN_SOURCE_INT_OSC: return "PIN_SOURCE_INT_OSC";
        case PIN_SOURCE_UNKNOWN: return "UNKNOWN";
        default: return "INVALID";
    }
}

/**
 * parse_clock_accuracy - Convert clock accuracy string to uint8_t value
 * @accuracy_str: Clock accuracy string (e.g., "0xFE", "254")
 *
 * Returns: Parsed uint8_t value, or 0xFE (unknown) on error
 */
static uint8_t parse_clock_accuracy(const char *accuracy_str)
{
    if (!accuracy_str || accuracy_str[0] == '\0') {
        return 0xFE;  /* Default: unknown */
    }
    
    /* Parse hex (0x prefix) or decimal */
    uint8_t value = 0xFE;
    if (strncmp(accuracy_str, "0x", 2) == 0 || strncmp(accuracy_str, "0X", 2) == 0) {
        /* Hexadecimal */
        value = (uint8_t)strtoul(accuracy_str, NULL, 16);
    } else {
        /* Decimal */
        value = (uint8_t)strtoul(accuracy_str, NULL, 10);
    }
    
    return value;
}

/**
 * parse_time_source - Convert time source string to uint8_t value
 * @time_source_str: Time source string (e.g., "0x20", "GNSS", "GPS")
 *
 * Returns: Parsed uint8_t value per IEEE 1588 spec
 */
static uint8_t parse_time_source(const char *time_source_str)
{
    if (!time_source_str || time_source_str[0] == '\0') {
        return 0xA0;  /* Default: INTERNAL_OSCILLATOR */
    }
    
    /* Check for hex format first */
    if (strncmp(time_source_str, "0x", 2) == 0 || strncmp(time_source_str, "0X", 2) == 0) {
        return (uint8_t)strtoul(time_source_str, NULL, 16);
    }
    
    /* Parse string names per IEEE 1588-2019 Table 7 */
    if (strcasecmp(time_source_str, "ATOMIC_CLOCK") == 0) return 0x10;
    if (strcasecmp(time_source_str, "GNSS") == 0) return 0x20;
    if (strcasecmp(time_source_str, "GPS") == 0) return 0x20;
    if (strcasecmp(time_source_str, "TERRESTRIAL_RADIO") == 0) return 0x30;
    if (strcasecmp(time_source_str, "SERIAL_TIME_CODE") == 0) return 0x39;
    if (strcasecmp(time_source_str, "PTP") == 0) return 0x40;
    if (strcasecmp(time_source_str, "NTP") == 0) return 0x50;
    if (strcasecmp(time_source_str, "HAND_SET") == 0) return 0x60;
    if (strcasecmp(time_source_str, "OTHER") == 0) return 0x90;
    if (strcasecmp(time_source_str, "INTERNAL_OSCILLATOR") == 0) return 0xA0;
    
    /* Try decimal parsing */
    return (uint8_t)strtoul(time_source_str, NULL, 10);
}

/**
 * parse_offset_scaled_log_variance - Convert variance string to uint16_t value
 * @variance_str: Variance string (e.g., "0x4E20", "20000")
 *
 * Returns: Parsed uint16_t value, or 0xFFFF (unknown) on error
 */
static uint16_t parse_offset_scaled_log_variance(const char *variance_str)
{
    if (!variance_str || variance_str[0] == '\0') {
        return 0xFFFF;  /* Default: unknown */
    }

    return (uint16_t)strtoul(variance_str, NULL, 0);
}

/**
 * populate_clock_parameters_from_config - Initialize clock parameters from config
 * @state: Application state containing clock_params array
 *
 * Populates state->clock_params[] array from g_config.ptp_primary_attrs.
 * For each entry in ptp_primary_attrs:
 * 1. Derives pin_source index from pin_name
 * 2. Populates clock parameters for that index
 */
static void populate_clock_parameters_from_config(AppState *state)
{
    if (!state) {
        LOG_ERROR("populate_clock_parameters_from_config: NULL state pointer\n");
        return;
    }
    
    LOG_DEBUG("=== Populating Clock Parameters from Configuration ===\n");
    
    for (int i = 0; i < g_config.ptp_primary_attr_count; i++) {
        const PtpPrimaryAttributes *attrs = &g_config.ptp_primary_attrs[i];
        
        /* Convert pin name to enum index */
        enum pin_source pin_idx = pin_name_to_enum(attrs->pin_name);
        
        if (pin_idx == PIN_SOURCE_UNKNOWN) {
            LOG_ERROR("Skipping unknown pin name: %s\n", attrs->pin_name);
            continue;
        }
        
        LOG_DEBUG("Configuring clock parameters for %s (index=%d):\n", attrs->pin_name, pin_idx);
        
        /* Populate clock parameters */
        ClockParameters *params = &state->clock_params[pin_idx];
        
        /* Initialize to zeros */
        memset(params, 0, sizeof(ClockParameters));
        
        /* Set clock class */
        params->gm_clock_class = (uint8_t)attrs->clockClass;
        LOG_DEBUG("  clockClass: %u\n", params->gm_clock_class);
        
        /* Parse and set clock accuracy */
        params->gm_clock_accuracy = parse_clock_accuracy(attrs->clockAccuracy);
        LOG_DEBUG("  clockAccuracy: 0x%02X\n", params->gm_clock_accuracy);
        
        /* Set time traceable */
        params->time_traceable = (uint8_t)attrs->timeTraceable;
        LOG_DEBUG("  timeTraceable: %u\n", params->time_traceable);
        
        /* Set frequency traceable */
        params->frequency_traceable = (uint8_t)attrs->frequencyTraceable;
        LOG_DEBUG("  frequencyTraceable: %u\n", params->frequency_traceable);
        
        /* Parse and set time source */
        params->time_source = parse_time_source(attrs->timeSource);
        LOG_DEBUG("  timeSource: 0x%02X\n", params->time_source);
        
        /* Set values from secondary defaults / fallback defaults */
        params->gm_offset_scaled_log_variance = parse_offset_scaled_log_variance(
            g_config.ptp_secondary_defaults.offsetScaledLogVariance);
        params->gm_priority1 = 128;  /* Default priority */
        params->gm_priority2 = 128;  /* Default priority */
        params->steps_removed = 0;
        params->phase_offset = 0;
        LOG_DEBUG("  offsetScaledLogVariance: 0x%04X\n", params->gm_offset_scaled_log_variance);
        
        /* For non-PTP sources (GNSS, SMA, holdover), mark GM as present since
         * parameters are pre-configured. For PTP sources, gm_present will be
         * updated dynamically when PARENT_DATA_SET is received. */
        if (pin_idx == GNSS_REF4P || pin_idx == GNSS_REF4N ||
            pin_idx == SMA1_REF3P || pin_idx == SMA3_REF3N ||
            pin_idx >= HOLDOVER_0) {
            params->gm_present = 1;  /* Static configuration available */
        } else {
            params->gm_present = 0;  /* Will be updated from PTP */
        }
        
        /* Set PTP secondary defaults from config */
        params->current_utc_offset = g_config.ptp_secondary_defaults.currentUtcOffset;
        params->leap61 = (uint8_t)g_config.ptp_secondary_defaults.leap61;
        params->leap59 = (uint8_t)g_config.ptp_secondary_defaults.leap59;
        params->current_utc_offset_valid = (uint8_t)g_config.ptp_secondary_defaults.currentUtcOffsetValid;
        params->ptp_timescale = (uint8_t)g_config.ptp_secondary_defaults.ptpTimescale;
        
        /* Set last update timestamp */
        clock_gettime(CLOCK_REALTIME, &params->last_update);
        
        LOG_DEBUG("  Configuration complete for %s\n", attrs->pin_name);
    }
    
    LOG_DEBUG("=== Clock Parameters Population Complete ===\n\n");
}

/**
 * get_holdover_parameters - Get parameters during holdover state
 * @state: Application state
 * @master_index: Master index (HOLDOVER_0, HOLDOVER_1, HOLDOVER_2, or HOLDOVER_3)
 *
 * When in holdover, use the last known good parameters or default values.
 * This allows the system to continue operating with stored clock parameters.
 * gm_identity is copied from PTP index (local clock identity).
 */
static int get_holdover_parameters(AppState *state, enum pin_source master_index)
{
    LOG_DEBUG("Getting parameters from holdover state (using stored/default values)\n");
    
    if (!state) {
        LOG_ERROR("get_holdover_parameters: NULL state pointer\n");
        return -1;
    }
    
    ClockParameters *params = &state->clock_params[master_index];

    /* In holdover, we use the last known good parameters that are already
     * stored in params from initial JSON configuration.
     * We only update timestamp and runtime flags here.
     */
    
    /* Update timestamp to current time */
    clock_gettime(CLOCK_REALTIME, &params->last_update);
    
    /* Keep configured holdover time source from JSON profile */
    
    /* Copy gm_identity from PTP index (local clock identity) */
    /* When in holdover, we still advertise our local clock identity */
    params->gm_identity = state->clock_params[SDP2_REF0P].gm_identity;
    
    /* Mark GM as not present during holdover */
    params->gm_present = 0;
   
    LOG_DEBUG("Holdover level %d parameters: Clock Class=%u, Time Source=0x%02x, GM Present=%d\n",
           master_index - HOLDOVER_0, params->gm_clock_class, params->time_source, params->gm_present);
    
    return 0;  /* Success */
}

/**
 * evaluate_ptp_gm_connection - Evaluate if PTP is connected to grandmaster
 * @state: Application state
 *
 * Checks multiple criteria to determine if PTP is properly locked to a GM:
 * 1. Port state must be SLAVE (9)
 * 2. Grandmaster must be present
 * 3. Steps removed must be > 0 (not the GM itself)
 *
 * Updates state->is_ptp_connected_to_gm with the result.
 */
static void evaluate_ptp_gm_connection(AppState *state)
{
    bool was_connected = state->is_ptp_connected_to_gm;
    
    /* Read current port status */
    int req_ret = send_get_request(state->local_socket_fd, &state->local_peer_addr,
                    MGMT_ID_PORT_DATA_SET, &state->local_sequence_id);
    if (req_ret != 0) {
        LOG_ERROR("Failed to send PORT_DATA_SET GET request (ret=%d)\n", req_ret);
        return;
    }
    usleep(100000);  /* 100ms delay for response */
    process_ptp_messages(state);
    
    /* Read current GM parameters */
    req_ret = send_get_request(state->local_socket_fd, &state->local_peer_addr,
                    MGMT_ID_PARENT_DATA_SET, &state->local_sequence_id);
    if (req_ret != 0) {
        LOG_ERROR("Failed to send PARENT_DATA_SET GET request (ret=%d)\n", req_ret);
        return;
    }
    usleep(100000);  /* 100ms delay for response */
    process_ptp_messages(state);
    
    /* Use canonical PTP index (SDP2_REF0P) for accessing PTP clock parameters */
    enum pin_source ptp_idx = SDP2_REF0P;
    
    /* Check GM presence only: port state is not a reliable indicator because
     * in SW mode ptp4l is in SLAVE (9) but in HW mode it is in UNCALIBRATED (8).
     */
    if (state->clock_params[ptp_idx].gm_present) {
        state->is_ptp_connected_to_gm = true;
    } else {
        state->is_ptp_connected_to_gm = false;
        LOG_INFO("GM check failed: gm_present=false (port_state=%u)\n",
                 state->port_state);
    }
    
    /* Log status change */
    if (was_connected != state->is_ptp_connected_to_gm) {
        if (state->is_ptp_connected_to_gm) {
            LOG_INFO("*** PTP CONNECTED TO GRANDMASTER ***\n");
            LOG_INFO("  Port State: %u\n", state->port_state);
            LOG_INFO("  GM Present: YES\n");
            LOG_INFO("  Phase Offset: %" PRId64 " ns\n", state->clock_params[ptp_idx].phase_offset);
        } else {
            LOG_INFO("*** PTP DISCONNECTED FROM GRANDMASTER ***\n");
            LOG_INFO("  Port State: %u\n", state->port_state);
            LOG_INFO("  GM Present: NO\n");
        }
    }
}

/**
 * Determine current master source based on DPLL connected pin state
 * @state: Application state
 * @dpll_sock: DPLL netlink socket
 *
 * Checks which pin is connected in the DPLL device state and sets
 * state->current_master accordingly:
 * - When locked: current_master = connected_pin_source
 * - When in holdover: HOLDOVER_0/1/2/3 based on duration
 */
void determine_current_master(AppState *state, struct ynl_sock *dpll_sock)
{
    enum dpll_mode mode;
    __u32 connected_pin_id;
    enum pin_source connected_pin_source;
    
    LOG_DEBUG("Determining current master from DPLL state...\n");
    
    if (dpll_sock == NULL) {
        state->current_master = PIN_SOURCE_UNKNOWN;
        state->lock_status = DPLL_LOCK_STATUS_UNLOCKED;
        LOG_INFO("Warning: DPLL not available, current master is UNKNOWN\n");
        return;
    }
    
    int ret = dpll_get_device_state_and_connected_pin(dpll_sock, state->pps_dpll_device_id, 
                                                      &state->lock_status, &mode,
                                                      &connected_pin_id, &connected_pin_source,
                                                      &state->ptp_pin_id, &state->ptp_pin_state);
    
    /* Check lock status */
    if (state->lock_status == DPLL_LOCK_STATUS_HOLDOVER) {
        /* Enter or continue holdover state */
        if (!state->in_holdover) {
            /* Just entered holdover - mark start time */
            clock_gettime(CLOCK_MONOTONIC, &state->holdover_start_time);
            state->in_holdover = true;
            state->current_master = HOLDOVER_0;
            LOG_INFO("Entered HOLDOVER state (HOLDOVER_0)\n");
        } else {
            /* Already in holdover - calculate duration and set appropriate level */
            struct timespec now;
            clock_gettime(CLOCK_MONOTONIC, &now);
            
            /* Calculate duration in minutes */
            int64_t duration_min = (now.tv_sec - state->holdover_start_time.tv_sec) / 60;
            
            /* Get holdover thresholds from configuration (in minutes) */
            int ho_0_min = g_config.holdover_config[0].ho_duration_min;
            int ho_1_min = g_config.holdover_config[1].ho_duration_min;
            int ho_2_min = g_config.holdover_config[2].ho_duration_min;
            
            if (duration_min < ho_0_min) {
                if (state->current_master != HOLDOVER_0) {
                    LOG_INFO("Transitioned to HOLDOVER_0 (duration: %ld min < %d min)\n", duration_min, ho_0_min);
                }
                state->current_master = HOLDOVER_0;
            } else if (duration_min < ho_1_min) {
                if (state->current_master != HOLDOVER_1) {
                    LOG_INFO("Transitioned to HOLDOVER_1 (duration: %ld min < %d min)\n", duration_min, ho_1_min);
                }
                state->current_master = HOLDOVER_1;
            } else if (duration_min < ho_2_min) {
                if (state->current_master != HOLDOVER_2) {
                    LOG_INFO("Transitioned to HOLDOVER_2 (duration: %ld min < %d min)\n", duration_min, ho_2_min);
                }
                state->current_master = HOLDOVER_2;
            } else {
                if (state->current_master != HOLDOVER_3) {
                    LOG_INFO("Transitioned to HOLDOVER_3 (duration: %ld min >= %d min)\n", duration_min, ho_2_min);
                }
                state->current_master = HOLDOVER_3;
            }
        }
    }
    /* If we have a connected pin (ret == 0), set master from pin source */
    else if (ret == 0) {
        /* Clear holdover state */
        if (state->in_holdover) {
            LOG_INFO("Exited HOLDOVER state\n");
            state->in_holdover = false;
        }
        
        /* Only check connected pin source if lock status is LOCKED or LOCKED_HO_ACQ */
        if (state->lock_status == DPLL_LOCK_STATUS_LOCKED || 
            state->lock_status == DPLL_LOCK_STATUS_LOCKED_HO_ACQ) {
            /* Assign connected pin source directly to current_master */
            state->current_master = connected_pin_source;
            state->connected_pin_id = connected_pin_id;  /* Store connected pin ID */
            LOG_DEBUG("determine_current_master: LOCKED to pin_id %u -> source %d (%s)\n",
                   connected_pin_id, state->current_master,
                   pin_source_to_string(state->current_master));
        }
        else {
            /* Lock status is UNLOCKED or other - set to UNKNOWN */
            state->current_master = PIN_SOURCE_UNKNOWN;
            LOG_INFO("Current master: UNKNOWN (lock status: UNLOCKED or other)\n");
        }
    } 
    else {
        /* Failed to get DPLL state or no pin found (but not holdover) */
        state->current_master = PIN_SOURCE_UNKNOWN;
        LOG_INFO("Current master: UNKNOWN (no connected pin, lock status: %d)\n", state->lock_status);
    }
}

/**
 * dump_clock_parameters - Debug function to dump all clock parameters
 * @params: Pointer to ClockParameters structure
 * @pin_index: Pin source index for identification
 *
 * Prints all clock parameter fields for debugging purposes.
 */
static void dump_clock_parameters(const ClockParameters *params, enum pin_source pin_index)
{
    if (!params) {
        LOG_ERROR("dump_clock_parameters: NULL pointer\n");
        return;
    }
    
    LOG_DEBUG("========== Clock Parameters Dump (Pin Source: %d) ==========\n", pin_index);
    LOG_DEBUG("GM Identity: %02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x\n",
           params->gm_identity.id[0], params->gm_identity.id[1], 
           params->gm_identity.id[2], params->gm_identity.id[3],
           params->gm_identity.id[4], params->gm_identity.id[5], 
           params->gm_identity.id[6], params->gm_identity.id[7]);
    LOG_DEBUG("GM Clock Class: %u\n", params->gm_clock_class);
    LOG_DEBUG("GM Clock Accuracy: 0x%02x\n", params->gm_clock_accuracy);
    LOG_DEBUG("GM Offset Scaled Log Variance: %u\n", params->gm_offset_scaled_log_variance);
    LOG_DEBUG("GM Priority1: %u\n", params->gm_priority1);
    LOG_DEBUG("GM Priority2: %u\n", params->gm_priority2);
    LOG_DEBUG("Steps Removed: %u\n", params->steps_removed);
    LOG_DEBUG("Phase Offset: %" PRId64 " ns\n", params->phase_offset);
    LOG_DEBUG("GM Present: %s\n", params->gm_present ? "YES" : "NO");
    LOG_DEBUG("Current UTC Offset: %d\n", params->current_utc_offset);
    LOG_DEBUG("Leap61: %u\n", params->leap61);
    LOG_DEBUG("Leap59: %u\n", params->leap59);
    LOG_DEBUG("Current UTC Offset Valid: %u\n", params->current_utc_offset_valid);
    LOG_DEBUG("PTP Timescale: %u\n", params->ptp_timescale);
    LOG_DEBUG("Time Traceable: %u\n", params->time_traceable);
    LOG_DEBUG("Frequency Traceable: %u\n", params->frequency_traceable);
    LOG_DEBUG("Time Source: 0x%02x\n", params->time_source);
    LOG_DEBUG("Last Update: %ld.%09ld\n", 
           params->last_update.tv_sec, params->last_update.tv_nsec);
    LOG_DEBUG("==========================================\n\n");
}

/**
 * read_clock_parameters_from_master - Determine current master and read clock parameters
 * @state: Application state
 * @dpll_sock: DPLL netlink socket
 *
 * This function:
 * 1. Determines who is the current master (PTP, GNSS, SyncE, etc.)
 * 2. Reads clock parameters based on the master type:
 *    - PTP: Uses send_get_request to query ptp4l with usleep and process_ptp_messages
 *    - GNSS: Uses GNSS utilities to read parameters
 *    - SyncE: Uses dummy function (to be implemented)
 *    - Unknown: No action taken
 *
 * Called periodically from main loop.
 */
void read_clock_parameters_from_master(AppState *state, struct ynl_sock *dpll_sock)
{
    /* Determine current master based on DPLL state */
    determine_current_master(state, dpll_sock);
#ifndef STATIC_PARAMS_FROM_CONFIG
    int req_ret = 0;
#endif

    enum pin_source master_index = state->current_master;
    
    /* Read clock parameters based on current master */
    /* Check if current master is a holdover state */
    if (master_index >= HOLDOVER_0 && master_index <= HOLDOVER_3) {
        LOG_DEBUG("Reading clock parameters from holdover state (master_index: %d)\n", master_index);
        /* Update clock parameters for holdover state (uses existing parameters) */
        if (get_holdover_parameters(state, master_index) == 0) {
            LOG_DEBUG("Successfully updated holdover clock parameters\n");
            dump_clock_parameters(&state->clock_params[master_index], master_index);
        } else {
            LOG_ERROR("Failed to update holdover clock parameters\n");
        }
    }
    /* Check if current master is GNSS */
    else if (master_index == GNSS_REF4P || master_index == GNSS_REF4N) {
        LOG_INFO("Reading clock parameters from GNSS master (index %d)\n", master_index);
        if (get_gnss_parameters(state, master_index) == 0) {
            LOG_INFO("Successfully read GNSS clock parameters\n");
            dump_clock_parameters(&state->clock_params[master_index], master_index);
        } else {
            LOG_ERROR("Failed to read GNSS clock parameters\n");
        }
    }
    /* Check if current master is PTP (SDP2_REF0P or SDP0_REF0N) */
    else if (master_index == SDP2_REF0P || master_index == SDP0_REF0N) {
        enum pin_source ptp_idx = master_index;
        LOG_INFO("Reading clock parameters from PTP master (index: %s)\n",
                 pin_source_to_string(ptp_idx));
#ifndef STATIC_PARAMS_FROM_CONFIG
        /* Dynamic mode: query ptp4l via PMC GET requests to update clock_params */
        req_ret = send_get_request(state->local_socket_fd, &state->local_peer_addr,
                       MGMT_ID_PARENT_DATA_SET, &state->local_sequence_id);
        if (req_ret != 0) {
            LOG_ERROR("Failed to send PARENT_DATA_SET GET request (ret=%d)\n", req_ret);
            goto last;
        }
        usleep(100000);  /* 100ms delay */
        process_ptp_messages(state);
        
        req_ret = send_get_request(state->local_socket_fd, &state->local_peer_addr,
                       MGMT_ID_TIME_STATUS_NP, &state->local_sequence_id);
        if (req_ret != 0) {
            LOG_ERROR("Failed to send TIME_STATUS_NP GET request (ret=%d)\n", req_ret);
            goto last;
        }
        usleep(100000);  /* 100ms delay */
        process_ptp_messages(state);
        
        req_ret = send_get_request(state->local_socket_fd, &state->local_peer_addr,
                       MGMT_ID_PORT_DATA_SET, &state->local_sequence_id);
        if (req_ret != 0) {
            LOG_ERROR("Failed to send PORT_DATA_SET GET request (ret=%d)\n", req_ret);
            goto last;
        }
        usleep(100000);  /* 100ms delay */
        process_ptp_messages(state);
#else
        /* Static mode: clock_params already populated from config — skip PTP queries */
        LOG_DEBUG("STATIC_PARAMS_FROM_CONFIG: using config-loaded parameters for PTP source %s\n",
                 pin_source_to_string(ptp_idx));
#endif  /* STATIC_PARAMS_FROM_CONFIG */
        dump_clock_parameters(&state->clock_params[ptp_idx], ptp_idx);
    }
    else if (master_index == PIN_SOURCE_UNKNOWN) {
        LOG_DEBUG("Current master is UNKNOWN, skipping clock parameter read\n");
        goto last;
    }
    else {
        LOG_INFO("Reading clock parameters from pin source %d\n", master_index);
        /* For other pin sources, could add specific handling here */
    }
    
    forward_clock_parameters(state);

last:
    return ;
}

/**
 * process_dpll_master_state - Determine current master and handle failover
 * @state: Application state
 * @dpll_sock: DPLL netlink socket
 *
 * Shared helper called from both the polling loop and the event-based loop.
 * Calls determine_current_master(), detects a master transition, triggers
 * gearshift / clock parameter refresh on transition, and saves prev_master.
 */
void process_dpll_master_state(AppState *state, struct ynl_sock *dpll_sock)
{
    determine_current_master(state, dpll_sock);

    /* Detect lock status change (independent of master change) */
    if (state->lock_status != state->prev_lock_status) {
        LOG_INFO("Lock status changed: %s -> %s\n",
                 lock_status_to_string(state->prev_lock_status),
                 lock_status_to_string(state->lock_status));
        state->prev_lock_status = state->lock_status;
        /* Track first lock for boot grace period */
        if (!state->ever_locked &&
            (state->lock_status == DPLL_LOCK_STATUS_LOCKED ||
             state->lock_status == DPLL_LOCK_STATUS_LOCKED_HO_ACQ)) {
            state->ever_locked = true;
            LOG_INFO("First lock achieved — alarm suppression lifted\n");
        }
        write_status_json(state);
    }

    if (state->prev_master != state->current_master) {
        LOG_INFO("FAILOVER DETECTED: %s -> %s\n",
                 pin_source_to_string(state->prev_master),
                 pin_source_to_string(state->current_master));
        if (g_config.manager.operation_mode == OPERATION_MODE_SW_BASED)
            handle_sw_based_failover(state, state->current_master);
        read_clock_parameters_from_master(state, dpll_sock);
        /* Note: on holdover entry, both lock_status and master change —
         * this results in two writes (harmless on tmpfs, idempotent). */
        write_status_json(state);
    }
    state->prev_master = state->current_master;
}

/**
 * Print usage information
 */
static void print_usage(const char *prog_name) 
{
    printf("Usage: %s [-c <config_file>] [-o <log_file>] [-h] [-v]\n", prog_name);
    printf("\nOptions:\n");
    printf("  -c, --config <file>    Configuration file path (default: config/apts_mgr.json)\n");
    printf("  -o, --output <file>    Log output file (default: stdout)\n");
    printf("  -h, --help             Show this help message\n");
    printf("  -v, --version          Show application version\n");
    printf("\nExamples:\n");
    printf("  %s\n", prog_name);
    printf("      (Uses default config: config/apts_mgr.json, logs to stdout)\n\n");
    printf("  %s -c /etc/apts_mgr.json -o /var/log/apts.log\n", prog_name);
    printf("      (Uses specified configuration file and log file)\n");
}

/**
 * Initialize logging subsystem
 * @log_file_path: Path to log file (NULL for stdout only)
 * @fr_uds_path: Free-running UDS path for logging
 * @rx_count: Number of receiver instances for logging
 * 
 * Opens log file if specified and prints initial banner messages.
 */
/**
 * initialize_logging_early - Open log file before config is loaded
 * @log_file_path: Path to log file (from command line)
 *
 * Opens the log file early so all subsequent logs go to file.
 * Call this before config_init() to capture all logs.
 */
static void initialize_logging_early(const char *log_file_path)
{
    /* Open log file if specified */
    if (log_file_path) {
        /* Create log file with restrictive permissions (0600 - owner only) */
        int log_fd = open(log_file_path, O_CREAT | O_WRONLY | O_TRUNC, 0600);
        if (log_fd < 0) {
            fprintf(stderr, "Error: Failed to open log file '%s': %s\n", log_file_path, strerror(errno));
            fprintf(stderr, "Continuing with stdout...\n");
        } else {
            g_log_file = fdopen(log_fd, "w");
            if (!g_log_file) {
                fprintf(stderr, "Error: Failed to create FILE stream: %s\n", strerror(errno));
                fprintf(stderr, "Continuing with stdout...\n");
                close(log_fd);
            } else {
                /* Log successfully opened file */
                LOG_INFO("Log file opened successfully\n");
            }
        }
    }
    
    /* Print application banner */
    LOG_INFO("APTS Manager Version: %s\n", APTS_MGR_VERSION);
    LOG_INFO("Timing Manager Starting...\n");
}

/**
 * apply_pin_priorities - Set DPLL pin priorities from priority table
 * @dpll_sock: DPLL netlink socket
 * @device_id: DPLL device ID
 * @priority_table: Array of PinPriorityEntry structures indexed by pin_source enum
 * @table_size: Size of priority_table array
 *
 * Iterates through the priority table and sets each pin's priority
 * using dpll_pin_set_priority. Uses package_label from the structure.
 */
static void apply_pin_priorities(struct ynl_sock *dpll_sock, 
                                 __u32 device_id,
                                 PinPriorityEntry *priority_table, 
                                 size_t table_size)
{
    if (!dpll_sock || !priority_table) {
        LOG_ERROR("apply_pin_priorities: Invalid parameters\n");
        return;
    }
    
    LOG_INFO("=== Applying Pin Priorities ===\n");
    
    /* Iterate through priority table */
    for (size_t i = 0; i < table_size; i++) {
        /* Skip entries with no priority set (-1), no pin name, or unknown pins */
        if (priority_table[i].priority == -1 || 
            priority_table[i].pin_name[0] == '\0' || 
            i == PIN_SOURCE_UNKNOWN) {
            continue;
        }
        
        const char *pin_name = priority_table[i].pin_name;
        const char *package_label = priority_table[i].package_label;
        int priority = priority_table[i].priority;
        
        LOG_DEBUG("Setting priority for %s (package_label: %s) to %d\n", 
               pin_name, package_label, priority);
        
        /* Set the priority using DPLL API */
        int old_priority = dpll_pin_set_priority(dpll_sock, device_id, (char*)package_label, priority);
        if (old_priority >= 0) {
            int readback_priority = dpll_pin_get_priority(dpll_sock, device_id, (char*)package_label);
            if (readback_priority == priority) {
                LOG_INFO("  Success: old_priority=%d, new_priority=%d\n",
                       old_priority, priority);
            } else {
                LOG_ERROR("  Priority mismatch for %s (package_label: %s): requested=%d, readback=%d\n",
                         pin_name, package_label, priority, readback_priority);
            }
        } else {
            LOG_ERROR("  Failed to set priority for %s (package_label: %s)\n", 
                     pin_name, package_label);
        }
    }
    
    LOG_INFO("=== Pin Priorities Applied ===\n\n");
}

/**
 * Initialize all interfaces (PTP, GNSS, DPLL)
 * @state: Application state for PTP checking and storing DPLL socket
 * 
 * Returns: DPLL socket pointer on success, NULL if DPLL initialization failed
 *          (but continues execution). Exits program if PTP check fails.
 */
static struct ynl_sock* initialize_interfaces(AppState *state)
{
    /* Check if ptp4l is in free running mode (SW_BASED only) */
    if (g_config.manager.operation_mode == OPERATION_MODE_HW_BASED) {
        if (!check_free_running_mode(state->local_socket_fd, &state->local_peer_addr, &state->local_sequence_id)) {
            LOG_ERROR("ERROR: ptp4l is NOT running in free running mode!\n");
            LOG_ERROR("Please restart ptp4l with free running mode enabled.\n");
            LOG_ERROR("Example: ptp4l -i <interface> -m --free_running\n");
            exit(EXIT_FAILURE);
        } else {
            LOG_INFO("GNRD ptp4l running in free running mode - Proceeding \n");
        }
    }

    /* Evaluate initial PTP GM connection status (reads port status and GM parameters).
     * Retry a few times since ptp4l responses may be delayed at startup.
     */
    LOG_INFO("Evaluating initial PTP-GM connection status...\n");
    for (int _try = 0; _try < 5 && !state->is_ptp_connected_to_gm; _try++) {
        if (_try > 0) {
            LOG_DEBUG("Retrying PTP-GM check (%d/5)...\n", _try + 1);
            usleep(500000);  /* 500ms between retries */
        }
        evaluate_ptp_gm_connection(state);
    }
    LOG_INFO("Initial PTP-GM connection status: %s\n",
           state->is_ptp_connected_to_gm ? "CONNECTED" : "NOT CONNECTED");

    if (!state->is_ptp_connected_to_gm) {
        LOG_ERROR("Grandmaster not connected. Cannot proceed with initialization.\n");
        return NULL;
    }

#if 0
    /* Verify that the TSPLL is configured in TIME_REF mode.
     * Both "SW conf" and "TSPLL" lines in tspll_cfg must contain "TIME_REF".
     */
    char tspll_path[256];
    snprintf(tspll_path, sizeof(tspll_path),
             "/sys/class/net/%s/device/tspll_cfg",
             g_config.manager.phc_interface);

    FILE *fp = fopen(tspll_path, "r");
    if (!fp) {
        LOG_ERROR("Cannot open %s: %s\n", tspll_path, strerror(errno));
        return NULL;
    }

    bool sw_conf_ok = false;
    bool tspll_ok = false;
    char tspll_line[256];

    while (fgets(tspll_line, sizeof(tspll_line), fp)) {
        if (strstr(tspll_line, "SW conf") && strstr(tspll_line, "TIME_REF"))
            sw_conf_ok = true;
        if (strstr(tspll_line, "TSPLL") && strstr(tspll_line, "TIME_REF"))
            tspll_ok = true;
    }
    fclose(fp);

    if (!sw_conf_ok || !tspll_ok) {
        LOG_ERROR("TSPLL is NOT in TIME_REF mode (sw_conf_ok=%d, tspll_ok=%d). "
                  "Cannot proceed.\n", sw_conf_ok, tspll_ok);
        return NULL;
    }
    LOG_INFO("TSPLL TIME_REF mode verified for %s\n", g_config.manager.phc_interface);
#endif

    /* Explicitly enable PTP DPLL pins at startup if GM is already connected.
     * handle_ptp_port_up() in process_port_data_set() fires only on port
     * recovery (FAULTY/DISABLED -> UNCALIBRATED/SLAVE), so it never fires at
     * startup when the port is already UP.  Call it directly here instead.
     */
    if (state->is_ptp_connected_to_gm)
        handle_ptp_port_up(state);

    /* Initialize GNSS module */
    if (gnss_init(NULL) == 0) {
        LOG_INFO("GNSS initialized successfully\n");
    } else {
        LOG_ERROR("Warning: GNSS initialization failed, continuing without GNSS support\n");
    }

    /* Initialize DPLL netlink socket */
    struct ynl_sock *dpll_sock = NULL;
    LOG_INFO("Initializing DPLL netlink socket...\n");
    if (init_dpll() == 0) {
        dpll_sock = ys;
        state->dpll_sock = dpll_sock;  /* Store in AppState */
        LOG_INFO("DPLL netlink initialized successfully (socket=%p)\n", (void*)dpll_sock);
        
        /* Discover PPS device dynamically */
        LOG_DEBUG("Discovering DPLL PPS device...\n");
        int pps_device_id = dpll_find_device_id_by_type(dpll_sock, DPLL_TYPE_PPS);
        if (pps_device_id >= 0) {
            state->pps_dpll_device_id = (__u32)pps_device_id;
            LOG_DEBUG("Using DPLL PPS device ID: %u\n", state->pps_dpll_device_id);
        } else {
            LOG_ERROR("Failed to find PPS device\n");
            return NULL;
        }

        /* Discover EEC device dynamically (used for pre-loop priority application) */
        LOG_DEBUG("Discovering DPLL EEC device...\n");
        int eec_device_id = dpll_find_device_id_by_type(dpll_sock, DPLL_TYPE_EEC);
        if (eec_device_id >= 0) {
            state->eec_dpll_device_id = (__u32)eec_device_id;
            LOG_DEBUG("Using DPLL EEC device ID: %u\n", state->eec_dpll_device_id);
        } else {
            LOG_ERROR("Failed to find EEC device\n");
            return NULL;
        }
    } else {
        state->dpll_sock = NULL;
        LOG_ERROR("Warning: DPLL initialization failed, continuing without DPLL support\n");
        LOG_ERROR("DPLL features will not be available. Check if DPLL kernel module is loaded.\n");
        return NULL;
    }
    
    return dpll_sock;
}

/**
 * Parse and validate command line arguments
 * @argc: Argument count
 * @argv: Argument vector
 * @config_file_path: Output pointer for config file path
 * @log_file_path: Output pointer for log file path
 * 
 * Returns: 0 on success, -1 on error, 1 if help was shown
 */
static int parse_and_validate_arguments(int argc, char *argv[],
                                       char **config_file_path,
                                       char **log_file_path)
{
    /* Parse command line arguments */
    static struct option long_options[] = {
        {"config",    required_argument, 0, 'c'},
        {"output",    required_argument, 0, 'o'},
        {"help",      no_argument,       0, 'h'},
        {"version",   no_argument,       0, 'v'},
        {0, 0, 0, 0}
    };
    
    int opt;
    *config_file_path = NULL;
    *log_file_path = NULL;
    
    while ((opt = getopt_long(argc, argv, "c:o:hv", long_options, NULL)) != -1) {
        switch (opt) {
            case 'c': {
                /* Validate config file path */
                if (strstr(optarg, "..")) {
                    fprintf(stderr, "Error: Config path contains '..' (path traversal not allowed)\n");
                    return -1;
                }
                /* Verify .json extension */
                const char *ext = strrchr(optarg, '.');
                if (!ext || strcmp(ext, ".json") != 0) {
                    fprintf(stderr, "Error: Config file must have .json extension\n");
                    return -1;
                }
                *config_file_path = optarg;
                break;
            }
            case 'o': {
                /* Validate log file path */
                if (strstr(optarg, "..")) {
                    fprintf(stderr, "Error: Log path contains '..' (path traversal not allowed)\n");
                    return -1;
                }
                *log_file_path = optarg;
                break;
            }
            case 'h':
                print_usage(argv[0]);
                return 1;  /* Help shown, exit gracefully */
            case 'v':
                printf("%s\n", APTS_MGR_VERSION);
                return 1;  /* Version shown, exit gracefully */
            default:
                print_usage(argv[0]);
                return -1;
        }
    }
    
    /* Set default config path if not provided */
    if (*config_file_path == NULL) {
        *config_file_path = "config/apts_mgr.json";
    }
    
    return 0;  /* Success */
}

/**
 * parse_log_level - Convert log level string to LogLevel enum
 * @level_str: Log level string ("ERROR", "INFO", "DEBUG", "RAW")
 *
 * Returns: LogLevel enum value, defaults to LOG_LEVEL_INFO if invalid
 */
static LogLevel parse_log_level(const char *level_str)
{
    if (!level_str || level_str[0] == '\0') {
        return LOG_LEVEL_INFO;  /* Default */
    }
    
    if (strcasecmp(level_str, "ERROR") == 0) return LOG_LEVEL_ERROR;
    if (strcasecmp(level_str, "INFO") == 0) return LOG_LEVEL_INFO;
    if (strcasecmp(level_str, "DEBUG") == 0) return LOG_LEVEL_DEBUG;
    if (strcasecmp(level_str, "RAW") == 0) return LOG_LEVEL_RAW;
    
    fprintf(stderr, "Warning: Unknown log level '%s', defaulting to INFO\n", level_str);
    return LOG_LEVEL_INFO;
}

/**
 * load_uds_paths_from_config - Load FR/RX UDS paths from configuration
 * @fr_uds_path_out: Output pointer to resolved FR UDS path
 * @fr_uds_buf: Storage buffer for FR UDS path
 * @fr_uds_buf_size: Size of FR UDS buffer
 * @rx_uds_bufs: Storage buffers for RX UDS paths
 * @rx_uds_paths: Output array of RX UDS path pointers
 * @rx_count_out: Output count of RX UDS paths
 *
 * Returns: true on success, false on error
 */
static bool load_uds_paths_from_config(char **fr_uds_path_out,
                                       char *fr_uds_buf,
                                       size_t fr_uds_buf_size,
                                       char rx_uds_bufs[MAX_REMOTE_INSTANCES][MAX_PATH_LEN],
                                       char *rx_uds_paths[MAX_REMOTE_INSTANCES],
                                       int *rx_count_out)
{
    if (!fr_uds_path_out || !fr_uds_buf || !rx_uds_bufs || !rx_uds_paths || !rx_count_out) {
        LOG_ERROR("load_uds_paths_from_config: Invalid parameter(s)\n");
        return false;
    }

    /* Get local UDS path from config (ptp_bh channel) */
    const ChannelConfig *ch = config_get_channel("ptp_bh");
    if (!ch || ch->call_channel[0] == '\0') {
        LOG_ERROR("Error: ptp_bh not found in config\n");
        return false;
    }

    /* Extract UDS path from "uds:/path" format */
    const char *fr_path = ch->call_channel;
    if (strncmp(fr_path, "uds:", 4) == 0) {
        fr_path += 4;  /* Skip "uds:" prefix */
    }
    snprintf(fr_uds_buf, fr_uds_buf_size, "%s", fr_path);
    *fr_uds_path_out = fr_uds_buf;
    LOG_DEBUG("Using local UDS path from config: %s\n", *fr_uds_path_out);

    /* Get remote UDS paths from config (ptp_0, ptp_1, ptp_2, etc.) */
    int rx_count = 0;
    for (int i = 0; i < MAX_REMOTE_INSTANCES; i++) {
        char channel_name[32];
        snprintf(channel_name, sizeof(channel_name), "ptp_%d", i);
        const ChannelConfig *ch_remote = config_get_channel(channel_name);
        if (ch_remote && ch_remote->call_channel[0] != '\0') {
            const char *rx_path = ch_remote->call_channel;
            if (strncmp(rx_path, "uds:", 4) == 0) {
                rx_path += 4;  /* Skip "uds:" prefix */
            }
            snprintf(rx_uds_bufs[rx_count], sizeof(rx_uds_bufs[rx_count]), "%s", rx_path);
            rx_uds_paths[rx_count] = rx_uds_bufs[rx_count];
            LOG_DEBUG("Using receiver UDS path from config [%d]: %s\n", rx_count, rx_uds_paths[rx_count]);
            rx_count++;
        }
    }

    *rx_count_out = rx_count;
    if (*rx_count_out == 0) {
        LOG_INFO("No remote instances configured\n");
    }

    return true;
}

/**
 * Initialize application state
 */
static bool initialize_state(AppState *state, const char *fr_uds_path,
                            char **rx_uds_paths, int rx_count)
{
    memset(state, 0, sizeof(AppState));
    
    /* Setup local ptp4l connection - direct UDS path */
    int ret = snprintf(state->fr_uds_path, sizeof(state->fr_uds_path), "%s", fr_uds_path);
    if (ret < 0 || ret >= (int)sizeof(state->fr_uds_path)) {
        LOG_ERROR("Path truncation detected\n");
        return false;
    }

    state->local_socket_fd = create_uds_socket(state->fr_uds_path, &state->local_peer_addr);
    if (state->local_socket_fd < 0) {
        LOG_ERROR("Failed to create socket for local ptp4l\n");
        return false;
    }

    LOG_DEBUG("Connected to local ptp4l at %s\n", state->fr_uds_path);

    /* Setup remote ptp4l connections - only store valid remotes */
    int valid_index = 0;
    int invalid_remotes = 0;
    
    for (int i = 0; i < rx_count && valid_index < MAX_REMOTE_INSTANCES; i++) {
        int temp_socket_fd = create_uds_socket(rx_uds_paths[i], &state->remotes[valid_index].peer_addr);
        if (temp_socket_fd < 0) {
            LOG_ERROR("Warning: Failed to connect to remote %d (%s)\n", i, rx_uds_paths[i]);
            invalid_remotes++;
            continue;
        }

        /* Store valid remote */
        int ret = snprintf(state->remotes[valid_index].uds_path, 
                          sizeof(state->remotes[valid_index].uds_path),
                          "%s", rx_uds_paths[i]);
        if (ret < 0 || ret >= (int)sizeof(state->remotes[valid_index].uds_path)) {
            LOG_ERROR("Path truncation detected\n");
            close(temp_socket_fd);
            invalid_remotes++;
            continue;
        }
        state->remotes[valid_index].socket_fd = temp_socket_fd;
        state->remotes[valid_index].active = true;
        LOG_DEBUG("Connected to remote ptp4l %d at %s\n", valid_index, state->remotes[valid_index].uds_path);
        valid_index++;
    }
    
    /* Update receiver count to reflect only valid remotes */
    state->rx_count = valid_index;
    
    /* Print UDS validation summary */
    LOG_DEBUG("========== Remote UDS Validation Summary ==========\n");
    LOG_DEBUG("Total remotes attempted: %d\n", rx_count);
    LOG_DEBUG("Valid remotes: %d\n", valid_index);
    LOG_DEBUG("Invalid remotes: %d\n", invalid_remotes);
    LOG_DEBUG("===================================================\n\n");
    
    LOG_DEBUG("Initialization done successfully\n");

    /* Setup ts2phc socket for gearshift (SW_BASED mode) */
    state->ts2phc_socket_fd = -1;
    const ChannelConfig *ts2_ch = config_get_channel("ts2_0");
    if (ts2_ch && ts2_ch->call_channel[0] != '\0') {
        const char *ts2_path = ts2_ch->call_channel;
        if (strncmp(ts2_path, "uds:", 4) == 0)
            ts2_path += 4;

        char ts2_local[108];
        int lret = snprintf(ts2_local, sizeof(ts2_local),
                            "/var/run/apts_mgr/timing_mgr.%d.ts2", getpid());
        if (lret > 0 && lret < (int)sizeof(ts2_local)) {
            unlink(ts2_local);
            int ts2_fd = socket(AF_UNIX, SOCK_DGRAM, 0);
            if (ts2_fd >= 0) {
                struct sockaddr_un la;
                memset(&la, 0, sizeof(la));
                la.sun_family = AF_UNIX;
                snprintf(la.sun_path, sizeof(la.sun_path), "%s", ts2_local);
                if (bind(ts2_fd, (struct sockaddr *)&la, sizeof(la)) == 0 &&
                    chmod(ts2_local, 0660) == 0) {
                    int flags = fcntl(ts2_fd, F_GETFL, 0);
                    if (flags >= 0) {
                        if (fcntl(ts2_fd, F_SETFL, flags | O_NONBLOCK) < 0) {
                            LOG_ERROR("Failed to set O_NONBLOCK on ts2phc socket: %s\n",
                                      strerror(errno));
                            close(ts2_fd);
                            unlink(ts2_local);
                            return -1;
                        }
                    }
                    size_t ts2_path_len = strlen(ts2_path);
                    if (ts2_path_len >= sizeof(state->ts2phc_peer_addr.sun_path)) {
                        LOG_ERROR("ts2phc peer path too long: %s\n", ts2_path);
                        close(ts2_fd);
                        unlink(ts2_local);
                    } else {
                        state->ts2phc_socket_fd = ts2_fd;
                        memset(&state->ts2phc_peer_addr, 0, sizeof(state->ts2phc_peer_addr));
                        state->ts2phc_peer_addr.sun_family = AF_UNIX;
                        memcpy(state->ts2phc_peer_addr.sun_path, ts2_path, ts2_path_len + 1);
                        LOG_DEBUG("ts2phc socket bound: local=%s peer=%s\n", ts2_local, ts2_path);
                    }
                } else {
                    LOG_ERROR("Failed to bind ts2phc socket: %s\n", strerror(errno));
                    close(ts2_fd);
                    unlink(ts2_local);
                }
            } else {
                LOG_ERROR("Failed to create ts2phc socket: %s\n", strerror(errno));
            }
        }
    } else {
        LOG_INFO("ts2_0 channel not configured, ts2phc gearshift unavailable\n");
    }

    /* Initialize status tracking fields */
    state->gear_ptp_bh = GEAR_IDLE;
    state->gear_ts2_0 = GEAR_DRIVE;
    state->prev_lock_status = DPLL_LOCK_STATUS_UNLOCKED;
    state->ever_locked = false;

    return true;
}

/**
 * Main function
 */
int main(int argc, char *argv[]) 
{
    char *config_path = NULL;
    char *log_file_path = NULL;
    
    /* Parse and validate command line arguments */
    int parse_result = parse_and_validate_arguments(argc, argv, &config_path, &log_file_path);
    if (parse_result != 0) {
        return (parse_result > 0) ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    
    /* Initialize logging early (before config) so all logs go to file */
    initialize_logging_early(log_file_path);
    
    /* Initialize configuration from JSON file */
    if (config_init(config_path) != 0) {
        LOG_ERROR("Failed to load configuration from %s\n", config_path);
        return EXIT_FAILURE;
    }

    /* Load timing delay table from timing_delays.json */
#ifdef DPLL_ZL3073X_TIMING_DELAYS
    timing_delays_init("config/timing_delays.json");
#endif
    
    /* Load UDS paths from config */
    static char fr_uds_buf[MAX_PATH_LEN];
    char *fr_uds_path = NULL;
    static char remote_uds_bufs[MAX_REMOTE_INSTANCES][MAX_PATH_LEN];
    char *rx_uds_paths[MAX_REMOTE_INSTANCES];
    int rx_count = 0;
    if (!load_uds_paths_from_config(&fr_uds_path,
                                    fr_uds_buf,
                                    sizeof(fr_uds_buf),
                                    remote_uds_bufs,
                                    rx_uds_paths,
                                    &rx_count)) {
        return EXIT_FAILURE;
    }
    
    /* Set log level from config */
    if (g_config.manager.log_level[0] != '\0') {
        /* Use config file setting */
        g_log_level = parse_log_level(g_config.manager.log_level);
        LOG_INFO("Log level set from config: %s\n", g_config.manager.log_level);
    } else {
        /* Default to INFO */
        g_log_level = LOG_LEVEL_INFO;
        LOG_INFO("Log level defaulting to: INFO\n");
    }
    
    /* Print loaded configuration - only if DEBUG is enabled */
    if (g_log_level >= LOG_LEVEL_DEBUG) {
        config_print();
    }

    /* Setup signal handlers */
    if (setup_signals() < 0) {
        LOG_ERROR("Failed to setup signal handlers\n");
        return EXIT_FAILURE;
    }

    /* Ensure runtime directory exists */
    if (ensure_runtime_directory() < 0) {
        LOG_ERROR("Failed to setup runtime directory\n");
        return EXIT_FAILURE;
    }

    /* Create status file directory for external consumers */
    if (mkdir(STATUS_FILE_DIR, 0755) < 0 && errno != EEXIST) {
        LOG_ERROR("Failed to create status directory %s: %s\n",
                  STATUS_FILE_DIR, strerror(errno));
    }

    /* Initialize application state */
    AppState state;
    if (!initialize_state(&state, fr_uds_path, rx_uds_paths, rx_count)) {
        LOG_ERROR("Failed to initialize application\n");
        return EXIT_FAILURE;
    }

    /* Parse and populate priority table for EEC (DPLL0_FREQ) */
    LOG_DEBUG("Parsing EEC pin priority map from dpll0 configuration...\n");
    if (config_parse_priority_map(g_config.dpll0.pin_priority_map,
                                   state.eec_priority_table,
                                   sizeof(state.eec_priority_table) / sizeof(state.eec_priority_table[0])) == 0) {
        LOG_DEBUG("EEC priority table populated successfully\n");
    } else {
        LOG_ERROR("Failed to parse EEC priority map from dpll0.pin_priority_map\n");
    }

    /* Parse and populate priority table for PPS (DPLL1_PHASE) */
    LOG_DEBUG("Parsing PPS pin priority map from dpll1 configuration...\n");
    if (config_parse_priority_map(g_config.dpll1.pin_priority_map,
                                   state.pps_priority_table,
                                   sizeof(state.pps_priority_table) / sizeof(state.pps_priority_table[0])) == 0) {
        LOG_DEBUG("PPS priority table populated successfully\n");
    } else {
        LOG_ERROR("Failed to parse PPS priority map from dpll1.pin_priority_map\n");
    }
    
    /* Populate clock parameters from configuration */
    populate_clock_parameters_from_config(&state);
    
    /* Initialize all interfaces (PTP, GNSS, DPLL) */
    struct ynl_sock *dpll_sock = initialize_interfaces(&state);
    if (!dpll_sock) {
        LOG_ERROR("Interface initialization failed (no GM or DPLL unavailable). Exiting.\n");
        cleanup_state(&state);
        config_cleanup();
        if (g_log_file) {
            fclose(g_log_file);
            g_log_file = NULL;
        }
        return EXIT_FAILURE;
    }

    /* Apply pin priorities to DPLL after interface initialization */
    /* Apply dpll0 map to EEC device */
    LOG_INFO("Applying pin priorities to EEC device (device %u)...\n", state.eec_dpll_device_id);
    apply_pin_priorities(dpll_sock, state.eec_dpll_device_id, state.eec_priority_table,
                        sizeof(state.eec_priority_table) / sizeof(state.eec_priority_table[0]));

    /* Apply dpll1 map to PPS device */
    LOG_INFO("Applying pin priorities to PPS device (device %u)...\n", state.pps_dpll_device_id);
    apply_pin_priorities(dpll_sock, state.pps_dpll_device_id, state.pps_priority_table,
                        sizeof(state.pps_priority_table) / sizeof(state.pps_priority_table[0]));

    /* Apply timing-delay phase compensation from timing_delays.json */
#ifdef DPLL_ZL3073X_TIMING_DELAYS
    LOG_INFO("Applying timing-delay phase compensation from timing_delays.json\n");
    if (apply_timing_delays_phase_adjust(dpll_sock) != 0)
        LOG_ERROR("Some timing-delay phase adjustments failed; continuing\n");
#endif

    /* Initialize local context by reading clock parameters from current master */
    LOG_DEBUG("Initializing local context with current clock data\n");
    read_clock_parameters_from_master(&state, dpll_sock);
    LOG_INFO("Local context initialized.\n");
    
    /* Initialize previous master for transition detection */
    state.prev_master = state.current_master;
    
    /* Print initial master before entering main loop */
    LOG_INFO("=== Initial Master Status ===\n");
    LOG_INFO("Current Master: %s (index=%d)\n", 
             pin_source_to_string(state.current_master), state.current_master);
    LOG_INFO("Lock Status: %s\n", 
             state.lock_status == DPLL_LOCK_STATUS_LOCKED ?
              "LOCKED" :
             state.lock_status == DPLL_LOCK_STATUS_LOCKED_HO_ACQ ? "LOCKED_HO_ACQ" :
             state.lock_status == DPLL_LOCK_STATUS_UNLOCKED ? "UNLOCKED" :
             state.lock_status == DPLL_LOCK_STATUS_HOLDOVER ? "HOLDOVER" : "UNKNOWN");
    
    /* Align gear to initial master before entering main loop (SW_BASED only) */
    if (g_config.manager.operation_mode == OPERATION_MODE_SW_BASED) {
        LOG_INFO("Applying initial gearshift for current master: %s\n",
                 pin_source_to_string(state.current_master));
        handle_sw_based_failover(&state, state.current_master);
    }

    /* Perform initial clock adjustment before entering main loop */
    if (g_config.manager.operation_mode != OPERATION_MODE_SW_BASED) {
       LOG_DEBUG("Initial Clock Adjustment\n");
       if (perform_clock_phase_adjust(&state, -state.master_offset) != 0) {
           LOG_ERROR("Initial clock phase adjustment failed. Exiting application.\n");
           cleanup_state(&state);
           config_cleanup();
           if (g_log_file) {
              fclose(g_log_file);
              g_log_file = NULL;
           }
           return EXIT_FAILURE;
       }
    }
    
    /* Main loop - dispatches to the event-based or poll-based implementation
     * selected at build time (BUILD_MODE=event or BUILD_MODE=poll). */
    /* Set ever_locked if DPLL is already locked at startup */
    if (state.lock_status == DPLL_LOCK_STATUS_LOCKED ||
        state.lock_status == DPLL_LOCK_STATUS_LOCKED_HO_ACQ) {
        state.ever_locked = true;
    }
    state.prev_lock_status = state.lock_status;

    write_status_json(&state);
    LOG_INFO("Initial status.json written to %s\n", STATUS_FILE_PATH);

    run_main_loop(&state, dpll_sock);

    LOG_INFO("Shutting down...\n");
    cleanup_state(&state);
    
    /* Cleanup configuration */
    config_cleanup();
    
    /* Close log file */
    if (g_log_file) {
        fclose(g_log_file);
        g_log_file = NULL;
    }
    
    return EXIT_SUCCESS;
}
