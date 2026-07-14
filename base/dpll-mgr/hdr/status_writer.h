/*
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Copyright (c) 2026, Wind River Systems, Inc.
 */

/**
 * @file status_writer.h
 * @brief Status file writer for external monitoring consumers
 *
 * Writes dpll-mgr state to /var/run/dpll_mgr/status.json on discrete
 * state transitions. Consumers (collectd, ptp-notification) poll the file.
 */

#ifndef STATUS_WRITER_H
#define STATUS_WRITER_H

#include "apts_manager.h"

#define STATUS_FILE_DIR  "/var/run/dpll_mgr"
#define STATUS_FILE_PATH "/var/run/dpll_mgr/status.json"
#define STATUS_FILE_TMP  "/var/run/dpll_mgr/.status.json.tmp"

/**
 * write_status_json - Write current state to status.json atomically.
 * @state: Pointer to the application state
 *
 * Serializes the current AppState to JSON and writes it to the status file
 * using atomic rename (write to .tmp, then rename). Safe to call from any
 * trigger point. Idempotent — multiple calls with same state produce same file.
 */
void write_status_json(const AppState *state);

/**
 * lock_status_to_string - Convert dpll_lock_status enum to JSON string.
 * @status: DPLL lock status enum value
 *
 * Returns: "locked", "unlocked", "holdover", "locked_ho_acq", or "unknown"
 * Also used for logging in apts_manager.c.
 */
const char *lock_status_to_string(enum dpll_lock_status status);

#endif /* STATUS_WRITER_H */
