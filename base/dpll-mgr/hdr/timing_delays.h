/*
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Copyright (c) 2026, Intel Corporation
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
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
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

/**
 * @file timing_delays.h
 * @brief Timing delay table parsed from timing_delays.json
 *
 * Each entry in the JSON array maps a DPLL pin name to its constituent
 * delay components (picoseconds).  The parsed table is stored in a global
 * array indexed by enum pin_source so callers can do O(1) look-up:
 *
 *   int32_t total = g_timing_delays[SDP2_REF0P].total_ps;
 *
 * Pins not present in the JSON keep all fields at 0 and pin_name empty.
 */

#ifndef TIMING_DELAYS_H
#define TIMING_DELAYS_H

#include <stdint.h>
#include "dpll_utils.h"   /* enum pin_source, PIN_SOURCE_INT_OSC; pulls in ynl/dpll-user.h */

/* Maximum number of raw entries read from the JSON array */
#define MAX_TIMING_DELAY_ENTRIES 64

/* Maximum length of the "DPLL" key string */
#define TIMING_DELAY_NAME_LEN 32

/**
 * struct timing_delay_entry - delay components for one DPLL pin (ps)
 *
 * All values are in picoseconds.  "integrator_adj_ps" is the
 * user-configurable "Integrator Adjustment (ps)" field from the JSON and
 * may be modified at runtime before the table is committed.
 */
struct timing_delay_entry {
	char    pin_name[TIMING_DELAY_NAME_LEN]; /* "DPLL" key, e.g. "REF0P" */
	int32_t timing_module_ps;   /* Timing Module (ps)        */
	int32_t motherboard_ps;     /* Motherboard (ps)          */
	int32_t system_ps;          /* System (ps)               */
	int32_t addin_card_ps;      /* Add-in Card (ps)          */
	int32_t integrator_adj_ps;  /* Integrator Adjustment (ps)*/
	int32_t total_ps;           /* Computed sum of all above */
};

/**
 * g_timing_delays[] — table indexed by enum pin_source
 *
 * Size is PIN_SOURCE_INT_OSC + 1 (the last defined enumerator + 1).
 * Entries for pin_source values that have no matching JSON entry are
 * zero-initialised.  Access pattern:
 *
 *   g_timing_delays[GNSS_REF4P].total_ps
 */
extern struct timing_delay_entry g_timing_delays[PIN_SOURCE_INT_OSC + 1];

/**
 * timing_delay_compute_total - compute total_ps from the delay components
 * @e: entry to update
 *
 * Sets e->total_ps = sum of all five component fields.
 * Called automatically by timing_delays_init() after parsing each entry.
 */
void timing_delay_compute_total(struct timing_delay_entry *e);

/**
 * timing_delays_init - parse timing_delays.json and populate g_timing_delays
 *
 * @param path  Path to timing_delays.json (e.g. "config/timing_delays.json")
 * @return      0 on success, -1 on parse error or missing file
 *
 * Calling this function is optional; if the file is absent the table stays
 * zero-initialised and the function logs a warning and returns 0.
 */
int timing_delays_init(const char *path);

/**
 * timing_delays_print - log the parsed table at INFO level (debug helper)
 */
void timing_delays_print(void);

/**
 * timing_delays_get - get delay entry for a pin source (safe accessor)
 *
 * @param src  pin_source enum value
 * @return     pointer to the entry; never NULL (returns zero entry for
 *             out-of-range or unknown values)
 */
const struct timing_delay_entry *timing_delays_get(enum pin_source src);

/**
 * apply_timing_delays_phase_adjust - Apply timing-delay compensation at init
 * @dpll_sock: DPLL netlink socket
 *
 * Iterates g_timing_delays[] and writes total_ps for each pin as the DPLL
 * pin phase_adjust to compensate for board trace path lengths.
 * Call once after initialize_interfaces() and timing_delays_init().
 *
 * Returns: 0 on success, -1 if any pin adjustment fails
 */
int apply_timing_delays_phase_adjust(struct ynl_sock *dpll_sock);

#endif /* TIMING_DELAYS_H */
