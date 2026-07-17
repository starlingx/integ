/*
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Copyright (c) 2026, Wind River Systems, Inc.
 */

/**
 * @file status_writer.c
 * @brief Status file writer for external monitoring consumers
 *
 * Serializes AppState to JSON and writes /var/run/dpll_mgr/status.json
 * atomically (write .tmp + rename). Called on discrete state transitions.
 */

#define MODULE "STATUS"

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <time.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <cjson/cJSON.h>

#include "../hdr/status_writer.h"
#include "../hdr/dpll_utils.h"
#include "../hdr/gearshift.h"
#include "../hdr/config_parser.h"
#include "../hdr/log.h"

/* External config (defined in config_parser.c) */
extern GlobalConfig g_config;

const char *lock_status_to_string(enum dpll_lock_status status)
{
    switch (status) {
    case DPLL_LOCK_STATUS_LOCKED:        return "locked";
    case DPLL_LOCK_STATUS_UNLOCKED:      return "unlocked";
    case DPLL_LOCK_STATUS_HOLDOVER:      return "holdover";
    case DPLL_LOCK_STATUS_LOCKED_HO_ACQ: return "locked_ho_acq";
    default:                             return "unknown";
    }
}

static const char *gear_to_string(uint8_t gear)
{
    switch (gear) {
    case GEAR_DRIVE:   return "DRIVE";
    case GEAR_NEUTRAL: return "NEUTRAL";
    case GEAR_PARK:    return "PARK";
    default:           return "UNKNOWN";
    }
}

static const char *port_state_to_string(uint8_t state)
{
    /* Values from IEEE 1588 / linuxptp port_state enum */
    switch (state) {
    case 6: return "MASTER";       /* PS_MASTER */
    case 9: return "SLAVE";        /* PS_SLAVE */
    case 7: return "PASSIVE";      /* PS_PASSIVE */
    case 3: return "LISTENING";    /* PS_LISTENING */
    case 2: return "FAULTY";       /* PS_FAULTY */
    case 1: return "INITIALIZING"; /* PS_INITIALIZING */
    default: return "UNKNOWN";
    }
}

static int get_holdover_level(const AppState *state)
{
    if (!state->in_holdover)
        return -1;
    if (state->current_master >= HOLDOVER_0 && state->current_master <= HOLDOVER_3)
        return (int)(state->current_master - HOLDOVER_0);
    return -1;
}

static int64_t get_holdover_duration_s(const AppState *state)
{
    if (!state->in_holdover)
        return 0;
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (int64_t)(now.tv_sec - state->holdover_start_time.tv_sec);
}

void write_status_json(const AppState *state)
{
    cJSON *root = cJSON_CreateObject();
    if (!root) {
        LOG_ERROR("Failed to create JSON object for status file\n");
        return;
    }

    /* Timestamp in ISO 8601 UTC with milliseconds */
    struct timespec ts;
    struct tm tm_utc;
    char timestamp[64];
    clock_gettime(CLOCK_REALTIME, &ts);
    gmtime_r(&ts.tv_sec, &tm_utc);
    snprintf(timestamp, sizeof(timestamp),
             "%04d-%02d-%02dT%02d:%02d:%02d.%03ldZ",
             tm_utc.tm_year + 1900, tm_utc.tm_mon + 1, tm_utc.tm_mday,
             tm_utc.tm_hour, tm_utc.tm_min, tm_utc.tm_sec,
             ts.tv_nsec / 1000000);

    /* Core fields */
    cJSON_AddNumberToObject(root, "format_version", 1);
    cJSON_AddStringToObject(root, "timestamp", timestamp);
    cJSON_AddStringToObject(root, "operation_mode",
        g_config.manager.operation_mode == OPERATION_MODE_SW_BASED
            ? "SW_BASED" : "HW_BASED");
    cJSON_AddStringToObject(root, "dpll_lock_status",
                            lock_status_to_string(state->lock_status));
    cJSON_AddStringToObject(root, "current_master",
                            pin_source_to_string(state->current_master));
    cJSON_AddStringToObject(root, "previous_master",
                            pin_source_to_string(state->prev_master));
    cJSON_AddBoolToObject(root, "in_holdover", state->in_holdover);
    cJSON_AddNumberToObject(root, "holdover_duration_s",
                            (double)get_holdover_duration_s(state));
    cJSON_AddNumberToObject(root, "holdover_level",
                            get_holdover_level(state));
    cJSON_AddNumberToObject(root, "clock_class",
                            (double)state->clock_params[state->current_master].gm_clock_class);

    /* Gearshift — SW_BASED only; empty object in HW_BASED */
    cJSON *gear = cJSON_CreateObject();
    if (g_config.manager.operation_mode == OPERATION_MODE_SW_BASED) {
        cJSON_AddStringToObject(gear, "ptp_bh",
                                gear_to_string(state->gear_ptp_bh));
        cJSON_AddStringToObject(gear, "ts2_0",
                                gear_to_string(state->gear_ts2_0));
    }
    cJSON_AddItemToObject(root, "gearshift", gear);

    /* Analog snapshots (captured at time of transition write) */
    cJSON_AddNumberToObject(root, "phase_offset_ns",
                            (double)state->apts_offset);
    cJSON_AddNumberToObject(root, "drift_rate_ns_per_s",
                            state->drift_rate);
    cJSON_AddStringToObject(root, "ptp_port_state",
                            port_state_to_string(state->port_state));

    /* connected_pin: actual pin when locked, "none" in holdover/unlocked */
    if (state->lock_status == DPLL_LOCK_STATUS_LOCKED ||
        state->lock_status == DPLL_LOCK_STATUS_LOCKED_HO_ACQ) {
        cJSON_AddStringToObject(root, "connected_pin",
                                pin_source_to_string(state->current_master));
    } else {
        cJSON_AddStringToObject(root, "connected_pin", "none");
    }

    /* Boot grace: consumers suppress "unlocked" alarm until ever_locked=true */
    cJSON_AddBoolToObject(root, "ever_locked", state->ever_locked);

    /* Atomic write: .tmp -> rename */
    char *json_str = cJSON_PrintUnformatted(root);
    if (json_str) {
        FILE *f = fopen(STATUS_FILE_TMP, "w");
        if (f) {
            fputs(json_str, f);
            fputc('\n', f);
            fclose(f);
            if (rename(STATUS_FILE_TMP, STATUS_FILE_PATH) != 0) {
                LOG_ERROR("Failed to rename status file: %s\n",
                          strerror(errno));
            }
        } else {
            LOG_ERROR("Failed to open status tmp file: %s\n",
                      strerror(errno));
        }
        cJSON_free(json_str);
    }

    cJSON_Delete(root);
}
