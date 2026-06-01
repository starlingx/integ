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
 * DPLL utility functions header
 */

#ifndef _DPLL_UTILS_H
#define _DPLL_UTILS_H

/* Highest DPLL pin priority (numerically lowest value = highest priority) */
#define DPLL_HIGHEST_PRIORITY  0

#include <linux/types.h>
#include <linux/dpll.h>

#include <ynl/dpll-user.h>
#include "log.h"

/**
 * enum pin_source - Application-specific pin identification
 * Maps hardware pin labels to application clock sources
 */
enum pin_source {
	PIN_SOURCE_UNKNOWN = 0,
	SDP2_REF0P,        // PTP via SDP2
	SDP0_REF0N,        // PTP via SDP0
	GNSS_REF4P,        // GNSS via REF4P
	GNSS_REF4N,        // GNSS via REF4N (unused)
	RCLKA_REF1P,       // SyncE via RCLKA
	RCLKB_REF1N,       // SyncE via RCLKB
	SMA1_REF3P,        // SMA1 via REF3P
	SMA3_REF3N,        // SMA3 via REF3N
	HOLDOVER_0,        // Holdover state < max_step_ns
	HOLDOVER_1,        // Holdover state > max_step_ns
	HOLDOVER_2,        // Holdover state > 2*max_step_ns
	HOLDOVER_3,        // Holdover state > 3*max_step_ns
	PIN_SOURCE_INT_OSC,         // Internal oscillator
};

/**
 * pin_label_to_source - Convert pin label string to enum
 * @label: Pin label string (board_label from DPLL)
 *
 * Returns: pin_source enum value
 */
static inline enum pin_source pin_label_to_source(const char *label) {
	if (!label)
		return PIN_SOURCE_UNKNOWN;
	
	if (strstr(label, "ETH01_SDP_TIMESYNC_2"))
		return SDP2_REF0P;
	if (strstr(label, "ETH01_SDP_TIMESYNC_0"))
		return SDP0_REF0N;
	if (strstr(label, "GNSS_1PPS_IN_4N"))
		return GNSS_REF4N;
	if (strstr(label, "GNSS_1PPS_IN"))
		return GNSS_REF4P;
	if (strstr(label, "CLK_78M125_NAC0_SYNCE0"))
		return RCLKA_REF1P;
	if (strstr(label, "CLK_78M125_NAC0_SYNCE1"))
		return RCLKB_REF1N;
	
	return PIN_SOURCE_UNKNOWN;
}

/**
 * is_ptp_pin - Check if pin source is PTP
 * @source: pin_source enum value
 *
 * Returns: 1 if PTP, 0 otherwise
 */
static inline int is_ptp_pin(enum pin_source source) {
	return (source == SDP2_REF0P || 
	        source == SDP0_REF0N);
}

/**
 * is_gnss_pin - Check if pin source is GNSS
 * @source: pin_source enum value
 *
 * Returns: 1 if GNSS, 0 otherwise
 */
static inline int is_gnss_pin(enum pin_source source) {
	return (source == GNSS_REF4P || 
	        source == GNSS_REF4N);
}

/**
 * is_synce_pin - Check if pin source is SyncE
 * @source: pin_source enum value
 *
 * Returns: 1 if SyncE, 0 otherwise
 */
static inline int is_synce_pin(enum pin_source source) {
	return (source == RCLKA_REF1P || 
	        source == RCLKB_REF1N);
}

/**
 * pin_name_to_source - Convert pin name string to enum
 * @pin_name: Pin name string (e.g., "GNSS_REF4P", "SDP0_REF0N")
 *
 * Returns: pin_source enum value
 */
static inline enum pin_source pin_name_to_source(const char *pin_name) {
	if (!pin_name)
		return PIN_SOURCE_UNKNOWN;
	
	if (strcmp(pin_name, "SDP2_REF0P") == 0)
		return SDP2_REF0P;
	if (strcmp(pin_name, "SDP0_REF0N") == 0)
		return SDP0_REF0N;
	if (strcmp(pin_name, "GNSS_REF4P") == 0)
		return GNSS_REF4P;
	if (strcmp(pin_name, "GNSS_REF4N") == 0)
		return GNSS_REF4N;
	if (strcmp(pin_name, "RCLKA_REF1P") == 0)
		return RCLKA_REF1P;
	if (strcmp(pin_name, "RCLKB_REF1N") == 0)
		return RCLKB_REF1N;
	if (strcmp(pin_name, "SMA1_REF3P") == 0)
		return SMA1_REF3P;
	if (strcmp(pin_name, "SMA3_REF3N") == 0)
		return SMA3_REF3N;
	
	return PIN_SOURCE_UNKNOWN;
}

/**
 * dpll_find_device_id_by_type - Find the DPLL device of specified type
 * @ys: YNL socket
 * @device_type: DPLL device type to search for (e.g., DPLL_TYPE_EEC, DPLL_TYPE_PPS)
 *
 * Dynamically discovers the DPLL device with specified type instead of
 * assuming a fixed device ID.
 *
 * Returns: Device ID on success, -1 if not found or on error
 */
int dpll_find_device_id_by_type(struct ynl_sock *ys, enum dpll_type device_type);

/**
 * dpll_get_device_state_and_connected_pin - Get DPLL device state and connected pin info
 * @ys: YNL socket
 * @device_id: DPLL device ID
 * @lock_status: Output pointer for lock status (can be NULL)
 * @mode: Output pointer for device mode (can be NULL)
 * @connected_pin_id: Output pointer for connected pin ID (can be NULL)
 * @connected_pin_source: Output pointer for connected pin source enum (can be NULL)
 * @ptp_pin_id: Output pointer for PTP pin ID (REF0N) - only updated when REF0N found (can be NULL)
 * @ptp_pin_state: Output pointer for PTP pin state (REF0N) - only updated when REF0N found (can be NULL)
 *
 * This function retrieves the DPLL device state (lock status and mode) and
 * identifies which pin is currently in the connected state.
 *
 * Returns: 0 on success, -1 on error or if no connected pin found
 */
int dpll_get_device_state_and_connected_pin(struct ynl_sock *ys,
					    __u32 device_id,
					    enum dpll_lock_status *lock_status,
					    enum dpll_mode *mode,
					    __u32 *connected_pin_id,
					    enum pin_source *connected_pin_source,
					    __u32 *ptp_pin_id,
					    enum dpll_pin_state *ptp_pin_state);

/**
 * init_dpll - Initialize DPLL netlink socket
 *
 * Returns: 0 on success, non-zero on error
 */
int init_dpll(void);

/**
 * dpll_pin_set_state - Set pin state
 * @ys: YNL socket
 * @device_id: DPLL device ID
 * @package_label: Pin package label
 * @state: Desired pin state
 *
 * Returns: Old state on success, -1 on error
 */
int dpll_pin_set_state(struct ynl_sock *ys, __u32 device_id, char *package_label, int state);

/**
 * dpll_pin_set_priority - Set pin priority
 * @ys: YNL socket
 * @device_id: DPLL device ID
 * @package_label: Pin package label
 * @prio: Desired priority
 *
 * Returns: Old priority on success, -1 on error
 */
int dpll_pin_set_priority(struct ynl_sock *ys, __u32 device_id, char *package_label, int prio);

/**
 * dpll_pin_get_priority - Get pin priority
 * @ys: YNL socket
 * @device_id: DPLL device ID
 * @package_label: Pin package label
 *
 * Returns: Current priority on success, -1 on error
 */
int dpll_pin_get_priority(struct ynl_sock *ys, __u32 device_id, char *package_label);

/**
 * dpll_pin_set_phase_adjust - Set pin phase adjustment
 * @ys: YNL socket
 * @package_label: Pin package label
 * @phase_adjust: Desired phase adjustment value in femtoseconds (raw netlink format)
 *               Must be within __s32 range: -2,147,483,648 to 2,147,483,647 fs
 *
 * Returns: Old phase adjustment value on success, -1 on error
 */
__s64 dpll_pin_set_phase_adjust(struct ynl_sock *ys, char *package_label, 
				 __s64 phase_adjust);

#endif /* _DPLL_UTILS_H */
