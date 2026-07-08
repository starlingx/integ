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
 * @file timing_delays.c
 * @brief Timing delay table — parses timing_delays.json into g_timing_delays[]
 *
 * The JSON file is a flat array of objects, each with a "DPLL" key that
 * holds the pin label (e.g. "REF0P", "REF4P").  We map those labels to
 * enum pin_source values and store the delay components indexed by that
 * enum so callers get O(1) access.
 *
 * Mapping (JSON "DPLL" field → enum pin_source → hardware package-label):
 *   "REF0P"  → SDP2_REF0P    package-label: REF0P
 *   "REF0N"  → SDP0_REF0N    package-label: REF0N
 *   "REF1P"  → RCLKA_REF1P   package-label: REF1P
 *   "REF1N"  → RCLKB_REF1N   package-label: REF1N
 *   "REF2N"  → DPLL_REF2N    package-label: REF2N
 *   "REF3P"  → SMA1_REF3P    package-label: REF3P
 *   "REF3N"  → SMA3_REF3N    package-label: REF3N
 *   "REF4P"  → GNSS_REF4P    package-label: REF4P
 *   "REF4N"  → GNSS_REF4N    package-label: REF4N
 *   "OUT0P"  → DPLL_OUT0P    package-label: OUT0P  (differential)
 *   "OUT0N"  → DPLL_OUT0N    package-label: OUT0N  (differential)
 *   "OUT1P"  → DPLL_OUT1P    package-label: OUT1P  (differential)
 *   "OUT1N"  → DPLL_OUT1N    package-label: OUT1N  (differential)
 *   "OUT2P"  → DPLL_OUT2P    package-label: OUT2P  (differential)
 *   "OUT2N"  → DPLL_OUT2N    package-label: OUT2N  (differential)
 *   "OUT3"   → DPLL_OUT3     package-label: OUT3   (single-ended)
 *   "OUT4"   → DPLL_OUT4     package-label: OUT4   (single-ended)
 *   "OUT5"   → DPLL_OUT5     package-label: OUT5   (single-ended)
 *   "OUT6P"  → DPLL_OUT6P    package-label: OUT6P  (differential)
 *   "OUT6N"  → DPLL_OUT6N    package-label: OUT6N  (differential)
 *   "OUT7P"  → DPLL_OUT7P    package-label: OUT7P  (differential)
 *   "OUT7N"  → DPLL_OUT7N    package-label: OUT7N  (differential)
 *   "OUT8P"  → DPLL_OUT8P    package-label: OUT8P  (differential)
 *   "OUT8N"  → DPLL_OUT8N    package-label: OUT8N  (differential)
 *   "OUT9"   → DPLL_OUT9     package-label: OUT9   (single-ended)
 *
 * Note: timing_delays.json may contain OUT3P/OUT3N etc. entries that do not
 * match any hardware package-label; those are silently skipped.
 */

#define MODULE "TDL"
#include "../hdr/timing_delays.h"
#include "../hdr/dpll_utils.h"
#include "../hdr/log.h"
#include <cjson/cJSON.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Global table indexed by enum pin_source */
struct timing_delay_entry g_timing_delays[PIN_SOURCE_INT_OSC + 1];

/* ---------------------------------------------------------------------------
 * Internal: mapping from JSON "DPLL" label to enum pin_source
 * ---------------------------------------------------------------------------
 */
struct pin_label_map {
	const char      *json_label;  /* "DPLL" field value in JSON          */
	const char      *hw_label;    /* hardware package-label passed to DPLL API */
	enum pin_source  source;      /* corresponding enum pin_source value  */
};

static const struct pin_label_map label_map[] = {
	/* Input REF pins */
	{ "REF0P", "REF0P", SDP2_REF0P   },
	{ "REF0N", "REF0N", SDP0_REF0N   },
	{ "REF1P", "REF1P", RCLKA_REF1P  },
	{ "REF1N", "REF1N", RCLKB_REF1N  },
	{ "REF2N", "REF2N", DPLL_REF2N   },
	{ "REF3P", "REF3P", SMA1_REF3P   },
	{ "REF3N", "REF3N", SMA3_REF3N   },
	{ "REF4P", "REF4P", GNSS_REF4P   },
	{ "REF4N", "REF4N", GNSS_REF4N   },
	/* Output pins — differential */
	{ "OUT0P", "OUT0P", DPLL_OUT0P   },
	{ "OUT0N", "OUT0N", DPLL_OUT0N   },
	{ "OUT1P", "OUT1P", DPLL_OUT1P   },
	{ "OUT1N", "OUT1N", DPLL_OUT1N   },
	{ "OUT2P", "OUT2P", DPLL_OUT2P   },
	{ "OUT2N", "OUT2N", DPLL_OUT2N   },
	{ "OUT6P", "OUT6P", DPLL_OUT6P   },
	{ "OUT6N", "OUT6N", DPLL_OUT6N   },
	{ "OUT7P", "OUT7P", DPLL_OUT7P   },
	{ "OUT7N", "OUT7N", DPLL_OUT7N   },
	{ "OUT8P", "OUT8P", DPLL_OUT8P   },
	{ "OUT8N", "OUT8N", DPLL_OUT8N   },
	/* Output pins — single-ended (JSON has OUTxP/OUTxN but HW pin is OUTx).
	 * Map only the P (first) variant; the N entry will be silently skipped. */
	{ "OUT3P", "OUT3",  DPLL_OUT3    },
	{ "OUT4P", "OUT4",  DPLL_OUT4    },
	{ "OUT5P", "OUT5",  DPLL_OUT5    },
	{ "OUT9P", "OUT9",  DPLL_OUT9    },
};

#define LABEL_MAP_LEN  (int)(sizeof(label_map) / sizeof(label_map[0]))

/**
 * json_label_lookup - find the label_map entry for a JSON "DPLL" string
 *
 * @param label  Value of the "DPLL" field from the JSON array element
 * @return       Pointer to matching entry, or NULL if not found
 */
static const struct pin_label_map *json_label_lookup(const char *label)
{
	int    i;
	size_t label_len;

	if (!label)
		return NULL;

	label_len = strlen(label);
	for (i = 0; i < LABEL_MAP_LEN; i++) {
		size_t map_len = strlen(label_map[i].json_label);

		if (label_len == map_len &&
		    strncmp(label, label_map[i].json_label, map_len) == 0)
			return &label_map[i];
	}
	return NULL;
}

/* ---------------------------------------------------------------------------
 * Internal: file reader (same pattern as config_parser.c)
 * ---------------------------------------------------------------------------
 */
static char *read_file_to_string(const char *filename)
{
	FILE *fp = fopen(filename, "r");
	char *buf;
	long size;

	if (!fp) {
		LOG_ERROR("timing_delays: cannot open %s\n", filename);
		return NULL;
	}

	fseek(fp, 0, SEEK_END);
	size = ftell(fp);
	fseek(fp, 0, SEEK_SET);

	if (size <= 0) {
		LOG_ERROR("timing_delays: invalid file size %ld\n", size);
		fclose(fp);
		return NULL;
	}

	buf = malloc((size_t)size + 1);
	if (!buf) {
		LOG_ERROR("timing_delays: malloc failed\n");
		fclose(fp);
		return NULL;
	}

	if (fread(buf, 1, (size_t)size, fp) != (size_t)size) {
		LOG_ERROR("timing_delays: read error on %s\n", filename);
		free(buf);
		fclose(fp);
		return NULL;
	}

	buf[size] = '\0';
	fclose(fp);
	return buf;
}

/* ---------------------------------------------------------------------------
 * Internal: parse one JSON object into a timing_delay_entry
 * ---------------------------------------------------------------------------
 */
static int parse_entry(cJSON *obj, struct timing_delay_entry *out)
{
	cJSON *field;

	memset(out, 0, sizeof(*out));

	field = cJSON_GetObjectItemCaseSensitive(obj, "DPLL");
	if (!cJSON_IsString(field) || !field->valuestring)
		return -1;
	strncpy(out->pin_name, field->valuestring, TIMING_DELAY_NAME_LEN - 1);

#define GET_INT(key, member) \
	do { \
		field = cJSON_GetObjectItemCaseSensitive(obj, key); \
		if (cJSON_IsNumber(field)) \
			out->member = (int32_t)field->valuedouble; \
	} while (0)

	GET_INT("Timing Module (ps)",        timing_module_ps);
	GET_INT("Motherboard (ps)",          motherboard_ps);
	GET_INT("System (ps)",               system_ps);
	GET_INT("Add-in Card (ps)",          addin_card_ps);
	GET_INT("Integrator Adjustment (ps)", integrator_adj_ps);
	GET_INT("Total (ps)",                total_ps);

#undef GET_INT

	return 0;
}

/* ---------------------------------------------------------------------------
 * Public API
 * ---------------------------------------------------------------------------
 */

/**
 * timing_delay_compute_total - compute total_ps by summing all delay components
 * @e: pointer to a timing_delay_entry whose component fields are populated
 *
 * total_ps = timing_module_ps + motherboard_ps + system_ps
 *          + addin_card_ps + integrator_adj_ps
 *
 * This replaces reading "Total (ps)" from the JSON, so the computed value
 * always reflects the actual sum of the individual fields.
 */
void timing_delay_compute_total(struct timing_delay_entry *e)
{
	if (!e)
		return;
	e->total_ps = e->timing_module_ps
		    + e->motherboard_ps
		    + e->system_ps
		    + e->addin_card_ps
		    + e->integrator_adj_ps;
}

int timing_delays_init(const char *path)
{
	char   *json_str;
	cJSON  *root, *elem;
	int     idx = 0;

	/* Zero-initialise the indexed table */
	memset(g_timing_delays, 0, sizeof(g_timing_delays));

	json_str = read_file_to_string(path);
	if (!json_str) {
		/* File absent — not fatal; table stays zeroed */
		LOG_ERROR("timing_delays: file not found: %s — delays set to 0\n",
			 path);
		return 0;
	}

	root = cJSON_Parse(json_str);
	free(json_str);

	if (!root) {
		LOG_ERROR("timing_delays: JSON parse error in %s\n", path);
		return -1;
	}

	if (!cJSON_IsArray(root)) {
		LOG_ERROR("timing_delays: expected JSON array in %s\n", path);
		cJSON_Delete(root);
		return -1;
	}

	cJSON_ArrayForEach(elem, root) {
		struct timing_delay_entry entry;
		const struct pin_label_map *m;
		enum pin_source src;

		if (!cJSON_IsObject(elem))
			continue;

		if (parse_entry(elem, &entry) != 0)
			continue;

		timing_delay_compute_total(&entry);

		/* Map JSON label → hw_label + enum and store in indexed table */
		m = json_label_lookup(entry.pin_name);
		if (!m) {
			LOG_INFO("timing_delays: skip %-12s — not in label_map"
				 " (no hardware pin match)\n",
				  entry.pin_name);
			if (++idx >= MAX_TIMING_DELAY_ENTRIES)
				break;
			continue;
		}
		src = m->source;
		/* Replace JSON label with the real HW package-label */
		strncpy(entry.pin_name, m->hw_label, TIMING_DELAY_NAME_LEN - 1);
		entry.pin_name[TIMING_DELAY_NAME_LEN - 1] = '\0';

		if ((int)src <= PIN_SOURCE_INT_OSC) {
#ifndef DPLL_IP_TIMING_DELAY
			/* Input (REF) compensation disabled — skip */
			if (strncmp(entry.pin_name, "REF", 3) == 0) {
				LOG_DEBUG("timing_delays: skip %-12s — IP compensation disabled\n",
					  entry.pin_name);
				continue;
			}
#endif
#ifndef DPLL_OP_TIMING_DELAY
			/* Output (OUT) compensation disabled — skip */
			if (strncmp(entry.pin_name, "OUT", 3) == 0) {
				LOG_DEBUG("timing_delays: skip %-12s — OP compensation disabled\n",
					  entry.pin_name);
				continue;
			}
#endif
			g_timing_delays[src] = entry;
			LOG_DEBUG("timing_delays: [%d] %-12s total=%d ps\n",
				  src, entry.pin_name, entry.total_ps);
		}

		if (++idx >= MAX_TIMING_DELAY_ENTRIES)
			break;
	}

	cJSON_Delete(root);
	LOG_INFO("timing_delays: loaded %d entries from %s\n", idx, path);
	return 0;
}

void timing_delays_print(void)
{
	int i;

	LOG_INFO("--- Timing Delay Table (indexed by pin_source) ---\n");
	for (i = 0; i <= PIN_SOURCE_INT_OSC; i++) {
		const struct timing_delay_entry *e = &g_timing_delays[i];

		if (e->pin_name[0] == '\0')
			continue;
		LOG_INFO("  [%2d] %-12s  module=%5d  mb=%5d  sys=%5d"
			 "  aic=%5d  adj=%5d  total=%5d  (ps)\n",
			 i, e->pin_name,
			 e->timing_module_ps, e->motherboard_ps,
			 e->system_ps, e->addin_card_ps,
			 e->integrator_adj_ps, e->total_ps);
	}
}

const struct timing_delay_entry *timing_delays_get(enum pin_source src)
{
	static const struct timing_delay_entry zero_entry;

	if ((int)src < 0 || (int)src > PIN_SOURCE_INT_OSC)
		return &zero_entry;
	return &g_timing_delays[src];
}

/* Round @value to the nearest multiple of @gran (>= 1), half-up. */
static int32_t round_to_granularity(int32_t value, __u32 gran)
{
	__u64 rounded;

	if (gran <= 1u || value <= 0)
		return value;
	rounded = ((__u64)(__u32)value + gran / 2u) / gran * gran;
	return (rounded <= (__u64)INT32_MAX) ? (int32_t)rounded : INT32_MAX;
}

/**
 * apply_timing_delays_phase_adjust - Apply hardware timing-delay compensation
 * @dpll_sock: DPLL netlink socket
 *
 * Called once at initialization.  For every pin in g_timing_delays[] that has
 * a non-zero total_ps value, writes the total path delay (picoseconds) as the
 * DPLL pin phase_adjust so the hardware compensates for board trace lengths.
 *
 * The pin_name field stored in g_timing_delays[] (e.g. "REF0P") is used
 * directly as the package_label for dpll_pin_set_phase_adjust().
 *
 * For output pins (OUT*) the value is first rounded to the nearest
 * multiple of the pin's phase_adjust_gran before being applied.
 *
 * Returns: 0 on success, -1 if any adjustment call fails
 */
int apply_timing_delays_phase_adjust(struct ynl_sock *dpll_sock)
{
	int i;
	int rc = 0;

	if (!dpll_sock) {
		LOG_ERROR("apply_timing_delays: DPLL socket not available\n");
		return -1;
	}

	LOG_INFO("=== Applying timing-delay phase compensation ===\n");

	for (i = 0; i <= PIN_SOURCE_INT_OSC; i++) {
		const struct timing_delay_entry *e = &g_timing_delays[i];
		int32_t apply_ps;

		if (e->pin_name[0] == '\0')
			continue;  /* no entry for this pin_source */

		if (e->total_ps == 0) {
			LOG_DEBUG("timing_delay: skip %-8s  total=0 ps\n",
				  e->pin_name);
			continue;
		}

		apply_ps = e->total_ps;

		/* Output pins: read granularity, round to nearest multiple, then apply */
		if (strncmp(e->pin_name, "OUT", 3) == 0) {
			__u32 gran = dpll_pin_get_phase_adjust_gran(dpll_sock,
							    e->pin_name);
			if (gran == 0) {
				/* Pin not found or gran not reported — cannot safely
				 * apply an unrounded value; skip this pin. */
				LOG_ERROR("timing_delay: pin %-8s  phase_adjust_gran"
					  " unavailable — skipping phase adjust\n",
					  e->pin_name);
				rc = -1;
				continue;
			}
			apply_ps = round_to_granularity(e->total_ps, gran);
			LOG_INFO("timing_delay: pin %-8s  module=%5d  mb=%5d"
				 "  adj=%5d  total=%5d  gran=%u  apply=%5d ps\n",
				 e->pin_name,
				 e->timing_module_ps, e->motherboard_ps,
				 e->integrator_adj_ps, e->total_ps,
				 gran, apply_ps);
		} else {
			LOG_INFO("timing_delay: pin %-8s  module=%5d  mb=%5d"
				 "  adj=%5d  total=%5d  apply=%5d ps\n",
				 e->pin_name,
				 e->timing_module_ps, e->motherboard_ps,
				 e->integrator_adj_ps, e->total_ps, apply_ps);
		}

		if (dpll_pin_set_phase_adjust(dpll_sock,
					      (char *)e->pin_name,
					      (__s64)apply_ps) == (__s64)-1) {
			LOG_ERROR("timing_delay: failed to set phase adjust "
				  "for pin %s (%d ps)\n",
				  e->pin_name, apply_ps);
			rc = -1;
			/* continue — apply remaining pins even if one fails */
		}
	}

	LOG_INFO("=== Timing-delay phase compensation complete ===\n");
	return rc;
}
