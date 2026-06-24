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
 * @file config_parser.c
 * @brief JSON Configuration Parser Implementation
 * 
 * This module parses the apts_mgr.json configuration file using cJSON
 * and populates global configuration structures.
 */

#define MODULE "CFG"
#include "../hdr/config_parser.h"
#include "../hdr/dpll_utils.h"
#include <cjson/cJSON.h>

/* Global configuration instance */
GlobalConfig g_config;

/* Static helper functions */
static int parse_manager_config(cJSON *json);
static int parse_channels_config(cJSON *json);
static int parse_dpll_config(cJSON *json);
static int parse_dpll_policy_config(cJSON *json);
static int parse_ptp_profiles_config(cJSON *json);
static int parse_ptp_primary_attributes(cJSON *json);
static int parse_ptp_secondary_defaults(cJSON *json);
static int parse_synce_config(cJSON *json);
static int parse_ql_map_config(cJSON *json);
static int parse_inputs_ql_config(cJSON *json);

/**
 * Read entire file into a string
 */
static char* read_file_to_string(const char *filename)
{
    FILE *file = fopen(filename, "r");
    if (!file) {
        LOG_ERROR("Cannot open config file: %s\n", filename);
        return NULL;
    }

    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    fseek(file, 0, SEEK_SET);

    if (file_size <= 0) {
        LOG_ERROR("Invalid file size: %ld\n", file_size);
        fclose(file);
        return NULL;
    }

    char *content = (char*)malloc(file_size + 1);
    if (!content) {
        LOG_ERROR("Memory allocation failed\n");
        fclose(file);
        return NULL;
    }

    size_t read_size = fread(content, 1, (size_t)file_size, file);
    content[read_size] = '\0';
    fclose(file);

    return content;
}

/**
 * Parse manager configuration section
 */
static int parse_manager_config(cJSON *json)
{
    cJSON *manager = cJSON_GetObjectItem(json, "global");
    if (!manager) {
        manager = cJSON_GetObjectItem(json, "manager");
    }
    if (!manager) {
        LOG_ERROR("'global'/'manager' section not found in config\n");
        return 0;
    }

    cJSON *item;
    
    item = cJSON_GetObjectItem(manager, "poll_interval_ms");
    if (item) g_config.manager.poll_interval_ms = item->valueint;
    
    item = cJSON_GetObjectItem(manager, "prefer_phc");
    if (item) g_config.manager.prefer_phc = cJSON_IsTrue(item);
    
    item = cJSON_GetObjectItem(manager, "guard_time_ms");
    if (item) g_config.manager.guard_time_ms = item->valueint;
    
    item = cJSON_GetObjectItem(manager, "hysteresis_ns");
    if (item) g_config.manager.hysteresis_ns = item->valueint;
    
    item = cJSON_GetObjectItem(manager, "min_holdover_s");
    if (item) g_config.manager.min_holdover_s = item->valueint;
    
    item = cJSON_GetObjectItem(manager, "max_step_ns");
    if (item) g_config.manager.max_step_ns = (int64_t)item->valuedouble;
    
    item = cJSON_GetObjectItem(manager, "phase_adjust_factor");
    if (item) {
        g_config.manager.phase_offset_factor = item->valueint;
    }
    
    item = cJSON_GetObjectItem(manager, "force_same_ql_on_fronthaul");
    if (item) g_config.manager.force_same_ql_on_fronthaul = cJSON_IsTrue(item);
    
    item = cJSON_GetObjectItem(manager, "log_level");
    if (item && item->valuestring) {
        strncpy(g_config.manager.log_level, item->valuestring, MAX_NAME_LEN - 1);
        g_config.manager.log_level[MAX_NAME_LEN - 1] = '\0';
    } else {
        /* Default to INFO if not specified */
        strncpy(g_config.manager.log_level, "INFO", MAX_NAME_LEN - 1);
    }

    item = cJSON_GetObjectItem(manager, "phc_interface");
    if (item && item->valuestring) {
        strncpy(g_config.manager.phc_interface, item->valuestring, MAX_NAME_LEN - 1);
        g_config.manager.phc_interface[MAX_NAME_LEN - 1] = '\0';
    }
    item = cJSON_GetObjectItem(manager, "operation_mode");
    if (item && item->valuestring &&
        strcasecmp(item->valuestring, "SW_BASED") == 0) {
        g_config.manager.operation_mode = OPERATION_MODE_SW_BASED;
    } else {
        g_config.manager.operation_mode = OPERATION_MODE_HW_BASED;
    }

    item = cJSON_GetObjectItem(manager, "ptp_domain_number");
    if (item) g_config.manager.ptp_domain_number = item->valueint;

    return 0;
}

/**
 * Parse channels configuration section
 */
static int parse_channels_config(cJSON *json)
{
    cJSON *channels = cJSON_GetObjectItem(json, "channels");
    if (!channels) {
        LOG_ERROR("'channels' section not found in config\n");
        return 0;
    }

    g_config.channel_count = 0;
    cJSON *channel = NULL;
    
    cJSON_ArrayForEach(channel, channels) {
        if (g_config.channel_count >= MAX_CHANNELS) {
            LOG_ERROR("Maximum channel count exceeded\n");
            break;
        }

        const char *name = channel->string;
        cJSON *call_channel = cJSON_GetObjectItem(channel, "call_channel");
        
        if (name && call_channel) {
            strncpy(g_config.channels[g_config.channel_count].name, 
                    name, MAX_NAME_LEN - 1);
            strncpy(g_config.channels[g_config.channel_count].call_channel, 
                    call_channel->valuestring, MAX_PATH_LEN - 1);
            g_config.channel_count++;
        }
    }

    return 0;
}

/**
 * Parse DPLL configuration section
 */
static int parse_dpll_config(cJSON *json)
{
    cJSON *dpll = cJSON_GetObjectItem(json, "dpll");
    if (!dpll) {
        LOG_ERROR("'dpll' section not found in config\n");
        return 0;
    }

    // Parse DPLL0
    cJSON *dpll0 = cJSON_GetObjectItem(dpll, "dpll0");
    if (dpll0) {
        cJSON *name = cJSON_GetObjectItem(dpll0, "name");
        cJSON *pin_priority = cJSON_GetObjectItem(dpll0, "pin_priority_map");
        
        if (name) {
            strncpy(g_config.dpll0.name, name->valuestring, MAX_NAME_LEN - 1);
        }
        if (pin_priority) {
            strncpy(g_config.dpll0.pin_priority_map, pin_priority->valuestring, 511);
        }
    }

    // Parse DPLL1
    cJSON *dpll1 = cJSON_GetObjectItem(dpll, "dpll1");
    if (dpll1) {
        cJSON *name = cJSON_GetObjectItem(dpll1, "name");
        cJSON *pin_priority = cJSON_GetObjectItem(dpll1, "pin_priority_map");
        
        if (name) {
            strncpy(g_config.dpll1.name, name->valuestring, MAX_NAME_LEN - 1);
        }
        if (pin_priority) {
            strncpy(g_config.dpll1.pin_priority_map, pin_priority->valuestring, 511);
        }
    }

    // Parse holdover_config
    cJSON *holdover_config = cJSON_GetObjectItem(dpll, "holdover_config");
    if (holdover_config) {
        g_config.holdover_config_count = 0;
        
        cJSON *ho_0 = cJSON_GetObjectItem(holdover_config, "ho_0");
        if (ho_0) {
            cJSON *duration = cJSON_GetObjectItem(ho_0, "ho_duration");
            if (duration) {
                strncpy(g_config.holdover_config[0].name, "ho_0", MAX_NAME_LEN - 1);
                g_config.holdover_config[0].ho_duration_min = (int)duration->valuedouble;
                g_config.holdover_config_count++;
            }
        }
        
        cJSON *ho_1 = cJSON_GetObjectItem(holdover_config, "ho_1");
        if (ho_1) {
            cJSON *duration = cJSON_GetObjectItem(ho_1, "ho_duration");
            if (duration) {
                strncpy(g_config.holdover_config[1].name, "ho_1", MAX_NAME_LEN - 1);
                g_config.holdover_config[1].ho_duration_min = (int)duration->valuedouble;
                g_config.holdover_config_count++;
            }
        }
        
        cJSON *ho_2 = cJSON_GetObjectItem(holdover_config, "ho_2");
        if (ho_2) {
            cJSON *duration = cJSON_GetObjectItem(ho_2, "ho_duration");
            if (duration) {
                strncpy(g_config.holdover_config[2].name, "ho_2", MAX_NAME_LEN - 1);
                g_config.holdover_config[2].ho_duration_min = (int)duration->valuedouble;
                g_config.holdover_config_count++;
            }
        }
        
        LOG_DEBUG("Parsed %d holdover configurations\n", g_config.holdover_config_count);
    }

    return 0;
}

/**
 * Parse DPLL policy configuration section
 */
static int parse_dpll_policy_config(cJSON *json)
{
    cJSON *dpll = cJSON_GetObjectItem(json, "dpll");
    cJSON *dpll_policy = NULL;
    if (dpll) {
        dpll_policy = cJSON_GetObjectItem(dpll, "dpll_policy");
    }
    if (!dpll_policy) {
        dpll_policy = cJSON_GetObjectItem(json, "dpll_policy");
    }
    if (!dpll_policy) {
        LOG_ERROR("'dpll_policy' section not found in config\n");
        return 0;
    }

    cJSON *rclkb = cJSON_GetObjectItem(dpll_policy, "rclkb");
    if (rclkb) {
        cJSON *item;
        
        item = cJSON_GetObjectItem(rclkb, "low_prio");
        if (item) g_config.dpll_policy.low_prio = item->valueint;
        
        item = cJSON_GetObjectItem(rclkb, "high_prio");
        if (item) g_config.dpll_policy.high_prio = item->valueint;
        
        item = cJSON_GetObjectItem(rclkb, "compare_source");
        if (item) strncpy(g_config.dpll_policy.compare_source, 
                         item->valuestring, MAX_NAME_LEN - 1);
        
        item = cJSON_GetObjectItem(rclkb, "tie_break");
        if (item) strncpy(g_config.dpll_policy.tie_break, 
                         item->valuestring, MAX_NAME_LEN - 1);
    }

    return 0;
}

/**
 * Parse PTP profiles configuration section
 */
static int parse_ptp_profiles_config(cJSON *json)
{
    cJSON *ptp = cJSON_GetObjectItem(json, "ptp");
    cJSON *ptp_profiles = NULL;
    if (ptp) {
        ptp_profiles = cJSON_GetObjectItem(ptp, "ptp_profiles");
    }
    if (!ptp_profiles) {
        LOG_ERROR("'ptp_profiles' section not found in config\n");
        return 0;
    }

    g_config.ptp_profile_count = 0;
    cJSON *profile = NULL;
    
    cJSON_ArrayForEach(profile, ptp_profiles) {
        if (g_config.ptp_profile_count >= MAX_PTP_PROFILES) {
            LOG_ERROR("Maximum PTP profile count exceeded\n");
            break;
        }

        const char *instance_name = profile->string;
        cJSON *profile_value = cJSON_GetObjectItem(profile, "profile");
        
        if (instance_name && profile_value) {
            strncpy(g_config.ptp_profiles[g_config.ptp_profile_count].instance_name, 
                    instance_name, MAX_NAME_LEN - 1);
            strncpy(g_config.ptp_profiles[g_config.ptp_profile_count].profile, 
                    profile_value->valuestring, MAX_NAME_LEN - 1);
            g_config.ptp_profile_count++;
        }
    }

    return 0;
}

/**
 * Parse PTP primary attributes configuration section
 */
static int parse_ptp_primary_attributes(cJSON *json)
{
    cJSON *ptp = cJSON_GetObjectItem(json, "ptp");
    cJSON *ptp_primary_attrs = NULL;
    if (ptp) {
        ptp_primary_attrs = cJSON_GetObjectItem(ptp, "ptp_primary_attributes");
    }
    if (!ptp_primary_attrs) {
        ptp_primary_attrs = cJSON_GetObjectItem(json, "ptp_primary_attributes");
    }
    if (!ptp_primary_attrs) {
        LOG_ERROR("'ptp_primary_attributes' section not found in config\n");
        return 0;
    }

    g_config.ptp_primary_attr_count = 0;
    cJSON *attrs = NULL;
    
    cJSON_ArrayForEach(attrs, ptp_primary_attrs) {
        if (g_config.ptp_primary_attr_count >= MAX_PTP_ATTRIBUTES) {
            LOG_ERROR("Maximum PTP attributes count exceeded\n");
            break;
        }

        const char *pin_name = attrs->string;
        if (!pin_name) continue;

        PtpPrimaryAttributes *attr = &g_config.ptp_primary_attrs[g_config.ptp_primary_attr_count];
        strncpy(attr->pin_name, pin_name, MAX_NAME_LEN - 1);
        
        cJSON *item;
        item = cJSON_GetObjectItem(attrs, "clockClass");
        if (item) attr->clockClass = item->valueint;
        
        item = cJSON_GetObjectItem(attrs, "clockAccuracy");
        if (item) strncpy(attr->clockAccuracy, item->valuestring, 15);
        
        item = cJSON_GetObjectItem(attrs, "timeTraceable");
        if (item) attr->timeTraceable = item->valueint;
        
        item = cJSON_GetObjectItem(attrs, "frequencyTraceable");
        if (item) attr->frequencyTraceable = item->valueint;
        
        item = cJSON_GetObjectItem(attrs, "timeSource");
        if (item) strncpy(attr->timeSource, item->valuestring, 15);
        
        g_config.ptp_primary_attr_count++;
    }

    return 0;
}

/**
 * Parse PTP secondary defaults configuration section
 */
static int parse_ptp_secondary_defaults(cJSON *json)
{
    cJSON *ptp = cJSON_GetObjectItem(json, "ptp");
    cJSON *ptp_secondary = NULL;
    if (ptp) {
        ptp_secondary = cJSON_GetObjectItem(ptp, "ptp_secondary_attributes");
        if (!ptp_secondary) {
            ptp_secondary = cJSON_GetObjectItem(ptp, "ptp_secondary_defaults");
        }
    }
    if (!ptp_secondary) {
        ptp_secondary = cJSON_GetObjectItem(json, "ptp_secondary_defaults");
        if (!ptp_secondary) {
            ptp_secondary = cJSON_GetObjectItem(json, "ptp_secondary_attributes");
        }
    }
    if (!ptp_secondary) {
        LOG_ERROR("'ptp_secondary_attributes'/'ptp_secondary_defaults' section not found in config\n");
        return 0;
    }

    cJSON *item;
    
    item = cJSON_GetObjectItem(ptp_secondary, "offsetScaledLogVariance");
    if (item) strncpy(g_config.ptp_secondary_defaults.offsetScaledLogVariance, 
                     item->valuestring, 15);
    
    item = cJSON_GetObjectItem(ptp_secondary, "currentUtcOffset");
    if (item) g_config.ptp_secondary_defaults.currentUtcOffset = item->valueint;
    
    item = cJSON_GetObjectItem(ptp_secondary, "leap61");
    if (item) g_config.ptp_secondary_defaults.leap61 = item->valueint;
    
    item = cJSON_GetObjectItem(ptp_secondary, "leap59");
    if (item) g_config.ptp_secondary_defaults.leap59 = item->valueint;
    
    item = cJSON_GetObjectItem(ptp_secondary, "currentUtcOffsetValid");
    if (item) g_config.ptp_secondary_defaults.currentUtcOffsetValid = item->valueint;
    
    item = cJSON_GetObjectItem(ptp_secondary, "ptpTimescale");
    if (item) g_config.ptp_secondary_defaults.ptpTimescale = item->valueint;

    return 0;
}

/**
 * Parse SyncE configuration section
 */
static int parse_synce_config(cJSON *json)
{
    cJSON *synce = cJSON_GetObjectItem(json, "synce");
    if (!synce) {
        LOG_ERROR("'synce' section not found in config\n");
        return 0;
    }

    cJSON *item;
    
    item = cJSON_GetObjectItem(synce, "ql_type");
    if (item) g_config.synce.ql_type = item->valueint;
    
    item = cJSON_GetObjectItem(synce, "use_extended_ql");
    if (item) g_config.synce.use_extended_ql = cJSON_IsTrue(item);

    return 0;
}

/**
 * Parse quality level map for a specific option
 */
static int parse_ql_option(cJSON *ql_map, const char *option_name, QualityLevelMap *map)
{
    cJSON *option = cJSON_GetObjectItem(ql_map, option_name);
    if (!option) {
        return -1;
    }

    strncpy(map->option_name, option_name, MAX_NAME_LEN - 1);
    map->entry_count = 0;

    cJSON *level = NULL;
    cJSON_ArrayForEach(level, option) {
        if (map->entry_count >= MAX_QL_LEVELS) {
            LOG_ERROR("Maximum QL level count exceeded for %s\n", option_name);
            break;
        }

        const char *level_name = level->string;
        if (!level_name) continue;

        QualityLevelEntry *entry = &map->entries[map->entry_count];
        strncpy(entry->level_name, level_name, MAX_NAME_LEN - 1);

        cJSON *ql = cJSON_GetObjectItem(level, "QL");
        if (ql) strncpy(entry->QL, ql->valuestring, 15);

        cJSON *extql = cJSON_GetObjectItem(level, "extQL");
        if (extql) strncpy(entry->extQL, extql->valuestring, 15);

        map->entry_count++;
    }

    return 0;
}

/**
 * Parse quality level map configuration section
 */
static int parse_ql_map_config(cJSON *json)
{
    cJSON *ql_map = cJSON_GetObjectItem(json, "ql_map");
    if (!ql_map) {
        LOG_ERROR("'ql_map' section not found in config\n");
        return 0;
    }

    parse_ql_option(ql_map, "option1", &g_config.ql_map_option1);
    parse_ql_option(ql_map, "option2", &g_config.ql_map_option2);

    return 0;
}

/**
 * Parse inputs quality level configuration section
 */
static int parse_inputs_ql_config(cJSON *json)
{
    cJSON *inputs_ql = cJSON_GetObjectItem(json, "inputs_ql");
    if (!inputs_ql) {
        LOG_ERROR("'inputs_ql' section not found in config\n");
        return 0;
    }

    g_config.inputs_ql_count = 0;
    cJSON *input = NULL;
    
    cJSON_ArrayForEach(input, inputs_ql) {
        if (g_config.inputs_ql_count >= MAX_INPUT_QL) {
            LOG_ERROR("Maximum input QL count exceeded\n");
            break;
        }

        const char *pin_name = input->string;
        if (!pin_name || !cJSON_IsString(input)) continue;

        strncpy(g_config.inputs_ql[g_config.inputs_ql_count].pin_name, 
                pin_name, MAX_NAME_LEN - 1);
        strncpy(g_config.inputs_ql[g_config.inputs_ql_count].ql_level, 
                input->valuestring, MAX_NAME_LEN - 1);
        g_config.inputs_ql_count++;
    }

    return 0;
}

/**
 * Initialize and parse the JSON configuration file
 */
int config_init(const char *config_file_path)
{
    if (!config_file_path) {
        LOG_ERROR("Config file path is NULL\n");
        return -1;
    }

    // Initialize global config to zero
    memset(&g_config, 0, sizeof(GlobalConfig));

    // Read file content
    char *json_content = read_file_to_string(config_file_path);
    if (!json_content) {
        return -1;
    }

    // Parse JSON
    cJSON *json = cJSON_Parse(json_content);
    free(json_content);

    if (!json) {
        const char *error_ptr = cJSON_GetErrorPtr();
        if (error_ptr) {
            LOG_ERROR("JSON parse error before: %s\n", error_ptr);
        }
        return -1;
    }

    // Parse each configuration section
    int result = 0;
    result |= parse_manager_config(json);
    result |= parse_channels_config(json);
    result |= parse_dpll_config(json);
    result |= parse_dpll_policy_config(json);
    result |= parse_ptp_profiles_config(json);
    result |= parse_ptp_primary_attributes(json);
    result |= parse_ptp_secondary_defaults(json);
    result |= parse_synce_config(json);
    result |= parse_ql_map_config(json);
    result |= parse_inputs_ql_config(json);

    cJSON_Delete(json);

    if (result == 0) {
        LOG_INFO("Configuration loaded successfully from: %s\n", config_file_path);
    }

    return result;
}

/**
 * Free any resources allocated during configuration parsing
 */
void config_cleanup(void)
{
    // Currently no dynamic allocations, but placeholder for future use
    memset(&g_config, 0, sizeof(GlobalConfig));
}

/**
 * Print the current configuration (for debugging)
 */
void config_print(void)
{
    LOG_INFO("=== Configuration Summary ===\n");
    LOG_INFO("Global/Manager:\n");
    LOG_INFO("  poll_interval_ms: %d\n", g_config.manager.poll_interval_ms);
    LOG_INFO("  prefer_phc: %s\n", g_config.manager.prefer_phc ? "true" : "false");
    LOG_INFO("  guard_time_ms: %d\n", g_config.manager.guard_time_ms);
    LOG_INFO("  hysteresis_ns: %d\n", g_config.manager.hysteresis_ns);
    LOG_INFO("  min_holdover_s: %d\n", g_config.manager.min_holdover_s);
    LOG_INFO("  max_step_ns: %ld\n", g_config.manager.max_step_ns);
    LOG_INFO("  phase_offset_factor: %d\n", g_config.manager.phase_offset_factor);
    LOG_INFO("  force_same_ql_on_fronthaul: %s\n", g_config.manager.force_same_ql_on_fronthaul ? "true" : "false");
    LOG_INFO("  phc_interface: %s\n", g_config.manager.phc_interface);
    LOG_INFO("  operation_mode: %s\n",
             g_config.manager.operation_mode == OPERATION_MODE_SW_BASED ? "SW_BASED" : "HW_BASED");
    
    LOG_INFO("Channels: %d\n", g_config.channel_count);
    for (int i = 0; i < g_config.channel_count; i++) {
        LOG_INFO("  %s: %s\n", g_config.channels[i].name, 
               g_config.channels[i].call_channel);
    }
    
    LOG_INFO("DPLL0:\n");
    LOG_INFO("  name: %s\n", g_config.dpll0.name);
    LOG_INFO("  pin_priority_map: %s\n", g_config.dpll0.pin_priority_map);
    
    LOG_INFO("DPLL1:\n");
    LOG_INFO("  name: %s\n", g_config.dpll1.name);
    LOG_INFO("  pin_priority_map: %s\n", g_config.dpll1.pin_priority_map);
    
    LOG_INFO("DPLL Policy (rclkb):\n");
    LOG_INFO("  low_prio: %d\n", g_config.dpll_policy.low_prio);
    LOG_INFO("  high_prio: %d\n", g_config.dpll_policy.high_prio);
    LOG_INFO("  compare_source: %s\n", g_config.dpll_policy.compare_source);
    LOG_INFO("  tie_break: %s\n", g_config.dpll_policy.tie_break);
    
    LOG_INFO("PTP Profiles: %d\n", g_config.ptp_profile_count);
    for (int i = 0; i < g_config.ptp_profile_count; i++) {
        LOG_INFO("  %s: %s\n", g_config.ptp_profiles[i].instance_name,
               g_config.ptp_profiles[i].profile);
    }
    
    LOG_INFO("PTP Primary Attributes: %d\n", g_config.ptp_primary_attr_count);
    for (int i = 0; i < g_config.ptp_primary_attr_count; i++) {
        PtpPrimaryAttributes *attr = &g_config.ptp_primary_attrs[i];
        LOG_INFO("  %s:\n", attr->pin_name);
        LOG_INFO("    clockClass: %d\n", attr->clockClass);
        LOG_INFO("    clockAccuracy: %s\n", attr->clockAccuracy);
        LOG_INFO("    timeTraceable: %d\n", attr->timeTraceable);
        LOG_INFO("    frequencyTraceable: %d\n", attr->frequencyTraceable);
        LOG_INFO("    timeSource: %s\n", attr->timeSource);
    }
    
    LOG_INFO("PTP Secondary Defaults:\n");
    LOG_INFO("  offsetScaledLogVariance: %s\n", g_config.ptp_secondary_defaults.offsetScaledLogVariance);
    LOG_INFO("  currentUtcOffset: %d\n", g_config.ptp_secondary_defaults.currentUtcOffset);
    LOG_INFO("  leap61: %d\n", g_config.ptp_secondary_defaults.leap61);
    LOG_INFO("  leap59: %d\n", g_config.ptp_secondary_defaults.leap59);
    LOG_INFO("  currentUtcOffsetValid: %d\n", g_config.ptp_secondary_defaults.currentUtcOffsetValid);
    LOG_INFO("  ptpTimescale: %d\n", g_config.ptp_secondary_defaults.ptpTimescale);
    
    LOG_INFO("SyncE:\n");
    LOG_INFO("  ql_type: %d\n", g_config.synce.ql_type);
    LOG_INFO("  use_extended_ql: %s\n", g_config.synce.use_extended_ql ? "true" : "false");
    
    LOG_INFO("Input Quality Levels: %d\n", g_config.inputs_ql_count);
    for (int i = 0; i < g_config.inputs_ql_count; i++) {
        LOG_INFO("  %s: %s\n", g_config.inputs_ql[i].pin_name,
               g_config.inputs_ql[i].ql_level);
    }
    
    LOG_INFO("============================\n\n");
}

/**
 * Get a channel configuration by name
 */
const ChannelConfig* config_get_channel(const char *name)
{
    if (!name) return NULL;
    
    for (int i = 0; i < g_config.channel_count; i++) {
        if (strcmp(g_config.channels[i].name, name) == 0) {
            return &g_config.channels[i];
        }
    }
    return NULL;
}

/**
 * Get PTP profile for an instance
 */
const char* config_get_ptp_profile(const char *instance_name)
{
    if (!instance_name) return NULL;
    
    for (int i = 0; i < g_config.ptp_profile_count; i++) {
        if (strcmp(g_config.ptp_profiles[i].instance_name, instance_name) == 0) {
            return g_config.ptp_profiles[i].profile;
        }
    }
    return NULL;
}

/**
 * Get PTP primary attributes for a pin
 */
const PtpPrimaryAttributes* config_get_ptp_primary_attrs(const char *pin_name)
{
    if (!pin_name) return NULL;
    
    for (int i = 0; i < g_config.ptp_primary_attr_count; i++) {
        if (strcmp(g_config.ptp_primary_attrs[i].pin_name, pin_name) == 0) {
            return &g_config.ptp_primary_attrs[i];
        }
    }
    return NULL;
}

/**
 * Get input quality level for a pin
 */
const char* config_get_input_ql(const char *pin_name)
{
    if (!pin_name) return NULL;
    
    for (int i = 0; i < g_config.inputs_ql_count; i++) {
        if (strcmp(g_config.inputs_ql[i].pin_name, pin_name) == 0) {
            return g_config.inputs_ql[i].ql_level;
        }
    }
    return NULL;
}

/**
 * Get master source ID for a pin name
 */
int config_get_master_id(const char *pin_name)
{
    (void)pin_name;
    // TODO: Implement master source mapping
    return -1;
}

/**
 * Get pin name for a master source ID
 */
const char* config_get_master_name(int master_id)
{
    (void)master_id;
    // TODO: Implement master source mapping
    return "UNKNOWN";
}

/**
 * Get total number of master sources defined
 */
int config_get_master_count(void)
{
    // TODO: Implement master source count
    return 0;
}

/**
 * Parse pin priority map and populate priority table
 */
/**
 * extract_package_label_from_pin - Extract package label from pin name
 * @pin_name: Pin name (e.g., "GNSS_REF4P")
 * @label_buf: Output buffer for package label
 * @label_buf_size: Size of output buffer
 */
static void extract_package_label_from_pin(const char *pin_name, char *label_buf, size_t label_buf_size)
{
    if (!pin_name || !label_buf || label_buf_size == 0) {
        return;
    }
    
    // Find the first underscore
    const char *underscore = strchr(pin_name, '_');
    if (underscore && *(underscore + 1) != '\0') {
        // Copy everything after the underscore
        strncpy(label_buf, underscore + 1, label_buf_size - 1);
        label_buf[label_buf_size - 1] = '\0';
    } else {
        // No underscore found, use the original name
        strncpy(label_buf, pin_name, label_buf_size - 1);
        label_buf[label_buf_size - 1] = '\0';
    }
}

int config_parse_priority_map(const char *pin_priority_map, PinPriorityEntry *priority_table, int table_size)
{
    if (!pin_priority_map || !priority_table || table_size <= 0) {
        LOG_ERROR("Invalid parameters for priority map parsing\n");
        return -1;
    }
    
    // Initialize all entries
    for (int i = 0; i < table_size; i++) {
        priority_table[i].pin_name[0] = '\0';
        priority_table[i].package_label[0] = '\0';
        priority_table[i].priority = -1;
    }
    
    // Make a copy of the string for parsing (strtok modifies the string)
    char *map_copy = strdup(pin_priority_map);
    if (!map_copy) {
        LOG_ERROR("Memory allocation failed\n");
        return -1;
    }
    
    // Parse the priority map: "PIN_NAME:priority, PIN_NAME:priority, ..."
    char *saveptr;
    char *pair = strtok_r(map_copy, ",", &saveptr);
    
    while (pair) {
        // Trim leading whitespace
        while (*pair == ' ' || *pair == '\t') pair++;
        
        // Find the colon separator
        char *colon = strchr(pair, ':');
        if (!colon) {
            LOG_ERROR("Invalid priority pair format: %s\n", pair);
            pair = strtok_r(NULL, ",", &saveptr);
            continue;
        }
        
        // Split into pin name and priority value
        *colon = '\0';
        char *pin_name = pair;
        char *priority_str = colon + 1;
        
        // Trim trailing whitespace from pin name
        char *end = pin_name + strlen(pin_name) - 1;
        while (end > pin_name && (*end == ' ' || *end == '\t')) {
            *end = '\0';
            end--;
        }
        
        // Convert pin name to enum
        enum pin_source pin_src = pin_name_to_source(pin_name);
        
        // Parse priority value
        int priority = atoi(priority_str);
        
        // Store in table if valid
        if (pin_src != PIN_SOURCE_UNKNOWN && (pin_src >= 0)  && (size_t)pin_src < (size_t)table_size) {
            // Store pin name
            strncpy(priority_table[pin_src].pin_name, pin_name, sizeof(priority_table[pin_src].pin_name) - 1);
            priority_table[pin_src].pin_name[sizeof(priority_table[pin_src].pin_name) - 1] = '\0';
            
            // Extract and store package label
            extract_package_label_from_pin(pin_name, priority_table[pin_src].package_label, 
                                          sizeof(priority_table[pin_src].package_label));
            
            // Store priority
            priority_table[pin_src].priority = priority;
            
            LOG_DEBUG("  Priority: %s (package_label: %s, index %d) = %d\n", 
                   pin_name, priority_table[pin_src].package_label, pin_src, priority);
        } else if (pin_src == PIN_SOURCE_UNKNOWN) {
            LOG_ERROR("Unknown pin name: %s\n", pin_name);
        }
        
        pair = strtok_r(NULL, ",", &saveptr);
    }
    
    free(map_copy);
    return 0;
}
