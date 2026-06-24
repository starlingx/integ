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
 * @file config_parser.h
 * @brief JSON Configuration Parser Header
 * 
 * This module parses the apts_mgr.json configuration file and
 * stores settings in global structures for access throughout
 * the application.
 */

#ifndef CONFIG_PARSER_H
#define CONFIG_PARSER_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>

/**
 * Priority entry structure for pin priority table
 * Defined here so both config_parser and apts_manager can use it
 */
typedef struct {
    char pin_name[32];       /* Pin name (e.g., "GNSS_REF4P") */
    char package_label[32];  /* Package label (e.g., "REF4P") */
    int priority;            /* Priority value (-1 = unset) */
} PinPriorityEntry;

/* Maximum array sizes */
#define MAX_CHANNELS 16
#define MAX_PIN_PRIORITY 32
#define MAX_PTP_PROFILES 8
#define MAX_PTP_ATTRIBUTES 16
#define MAX_QL_LEVELS 16
#define MAX_INPUT_QL 16
#define MAX_NAME_LEN 64
#define MAX_PATH_LEN 256

/**
 * Operation mode for APTS manager
 */
typedef enum {
    OPERATION_MODE_HW_BASED = 0,  /* Hardware-based (default): DPLL drives switching + phase adjust */
    OPERATION_MODE_SW_BASED = 1,  /* Software-based: PMC gearshift on failover, no phase adjust */
} OperationMode;

/* Manager Configuration */
typedef struct {
    int poll_interval_ms;
    bool prefer_phc;
    int guard_time_ms;
    int hysteresis_ns;
    int min_holdover_s;
    int64_t max_step_ns;
    int phase_offset_factor;
    bool force_same_ql_on_fronthaul;
    char log_level[MAX_NAME_LEN];  /* Log level: ERROR, INFO, DEBUG, RAW */
    char phc_interface[MAX_NAME_LEN];  /* Network interface for PHC device discovery */
    OperationMode operation_mode;          /* HW_BASED (default) or SW_BASED */
    int ptp_domain_number;             /* PTP domain number for ptp4l instances */
} ManagerConfig;

/* Channel Configuration */
typedef struct {
    char name[MAX_NAME_LEN];
    char call_channel[MAX_PATH_LEN];
} ChannelConfig;

/* DPLL Configuration */
typedef struct {
    char name[MAX_NAME_LEN];
    char pin_priority_map[512];
} DpllConfig;

/* Holdover Configuration Entry */
typedef struct {
    char name[MAX_NAME_LEN];       /* ho_0, ho_1, ho_2 */
    int ho_duration_min;           /* Duration in minutes */
} HoldoverConfigEntry;

/* DPLL Policy Configuration */
typedef struct {
    int low_prio;
    int high_prio;
    char compare_source[MAX_NAME_LEN];
    char tie_break[MAX_NAME_LEN];
} DpllPolicyConfig;

/* PTP Profile Configuration */
typedef struct {
    char instance_name[MAX_NAME_LEN];
    char profile[MAX_NAME_LEN];
} PtpProfileConfig;

/* PTP Primary Attributes */
typedef struct {
    char pin_name[MAX_NAME_LEN];
    int clockClass;
    char clockAccuracy[16];
    int timeTraceable;
    int frequencyTraceable;
    char timeSource[16];
} PtpPrimaryAttributes;

/* PTP Secondary Defaults */
typedef struct {
    char offsetScaledLogVariance[16];
    int currentUtcOffset;
    int leap61;
    int leap59;
    int currentUtcOffsetValid;
    int ptpTimescale;
} PtpSecondaryDefaults;

/* SyncE Configuration */
typedef struct {
    int ql_type;
    bool use_extended_ql;
} SynceConfig;

/* Quality Level Entry */
typedef struct {
    char level_name[MAX_NAME_LEN];
    char QL[16];
    char extQL[16];
} QualityLevelEntry;

/* Quality Level Map */
typedef struct {
    char option_name[MAX_NAME_LEN];
    QualityLevelEntry entries[MAX_QL_LEVELS];
    int entry_count;
} QualityLevelMap;

/* Input Quality Level */
typedef struct {
    char pin_name[MAX_NAME_LEN];
    char ql_level[MAX_NAME_LEN];
} InputQualityLevel;

/* Global Configuration Structure */
typedef struct {
    ManagerConfig manager;
    
    ChannelConfig channels[MAX_CHANNELS];
    int channel_count;
    
    DpllConfig dpll0;
    DpllConfig dpll1;
    DpllPolicyConfig dpll_policy;
    
    HoldoverConfigEntry holdover_config[3];  /* ho_0, ho_1, ho_2 */
    int holdover_config_count;
    
    PtpProfileConfig ptp_profiles[MAX_PTP_PROFILES];
    int ptp_profile_count;
    
    PtpPrimaryAttributes ptp_primary_attrs[MAX_PTP_ATTRIBUTES];
    int ptp_primary_attr_count;
    
    PtpSecondaryDefaults ptp_secondary_defaults;
    
    SynceConfig synce;
    
    QualityLevelMap ql_map_option1;
    QualityLevelMap ql_map_option2;
    
    InputQualityLevel inputs_ql[MAX_INPUT_QL];
    int inputs_ql_count;
} GlobalConfig;

/* Global configuration instance - accessible throughout the application */
extern GlobalConfig g_config;

/**
 * Initialize and parse the JSON configuration file
 * 
 * @param config_file_path Path to the JSON configuration file
 * @return 0 on success, -1 on failure
 */
int config_init(const char *config_file_path);

/**
 * Free any resources allocated during configuration parsing
 */
void config_cleanup(void);

/**
 * Print the current configuration (for debugging)
 */
void config_print(void);

/**
 * Get a channel configuration by name
 * 
 * @param name Channel name to search for
 * @return Pointer to ChannelConfig if found, NULL otherwise
 */
const ChannelConfig* config_get_channel(const char *name);

/**
 * Get PTP profile for an instance
 * 
 * @param instance_name Instance name to search for
 * @return Pointer to profile string if found, NULL otherwise
 */
const char* config_get_ptp_profile(const char *instance_name);

/**
 * Get PTP primary attributes for a pin
 * 
 * @param pin_name Pin name to search for
 * @return Pointer to PtpPrimaryAttributes if found, NULL otherwise
 */
const PtpPrimaryAttributes* config_get_ptp_primary_attrs(const char *pin_name);

/**
 * Get input quality level for a pin
 * 
 * @param pin_name Pin name to search for
 * @return Pointer to quality level string if found, NULL otherwise
 */
const char* config_get_input_ql(const char *pin_name);

/**
 * Get master source ID for a pin name
 * 
 * @param pin_name Pin name to search for
 * @return Master ID if found, -1 otherwise
 */
int config_get_master_id(const char *pin_name);

/**
 * Get pin name for a master source ID
 * 
 * @param master_id Master ID to search for
 * @return Pointer to pin name if found, NULL otherwise
 */
const char* config_get_master_name(int master_id);

/**
 * Get total number of master sources defined
 * 
 * @return Number of master sources
 */
int config_get_master_count(void);

/**
 * Parse pin priority map and populate priority table
 * 
 * @param pin_priority_map String containing pin:priority pairs (e.g., "GNSS_REF4P:0, SDP0_REF0N:15")
 * @param priority_table Output array of PinPriorityEntry structures indexed by enum pin_source
 * @param table_size Size of the priority_table array
 * @return 0 on success, -1 on error
 */
int config_parse_priority_map(const char *pin_priority_map, PinPriorityEntry *priority_table, int table_size);

#endif /* CONFIG_PARSER_H */
