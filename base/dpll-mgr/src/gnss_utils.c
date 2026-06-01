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


#define _DEFAULT_SOURCE
#define MODULE "GNSS"

#include "../hdr/gnss_utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <math.h>
#include <sys/time.h>
#include <time.h>
#include <gps.h>

/* Static variables for GNSS context */
static struct gps_data_t gnss_gps_data;
static bool gnss_initialized = false;
static bool gnss_connected = false;
static gnss_config_t current_config;
static gnss_clock_params_t last_params;

/* Default configuration */
static const gnss_config_t default_config = {
    .gpsd_host = GNSS_DEFAULT_HOST,
    .gpsd_port = GNSS_DEFAULT_PORT,
    .timeout_ms = GNSS_DEFAULT_TIMEOUT_MS,
    .verbose = false
};

/* Internal function prototypes */
static int gnss_connect(void);
static void gnss_disconnect(void);
static gnss_fix_status_t convert_gps_fix_mode(int mode);
static void calculate_dilution_of_precision(gnss_clock_params_t *params);
static void assess_clock_quality(gnss_clock_params_t *params);

int gnss_init(const gnss_config_t *config)
{
    if (gnss_initialized) {
        gnss_cleanup();
    }
    
    /* Use provided config or defaults */
    if (config) {
        current_config = *config;
        /* Allocate and copy strings if provided */
        if (config->gpsd_host) {
            current_config.gpsd_host = strdup(config->gpsd_host);
        } else {
            current_config.gpsd_host = strdup(default_config.gpsd_host);
        }
        if (config->gpsd_port) {
            current_config.gpsd_port = strdup(config->gpsd_port);
        } else {
            current_config.gpsd_port = strdup(default_config.gpsd_port);
        }
    } else {
        current_config = default_config;
        current_config.gpsd_host = strdup(default_config.gpsd_host);
        current_config.gpsd_port = strdup(default_config.gpsd_port);
    }
    
    if (!current_config.gpsd_host || !current_config.gpsd_port) {
        if (current_config.verbose) {
            fprintf(stderr, "GNSS: Failed to allocate memory for configuration\n");
        }
        return -ENOMEM;
    }
    
    /* Initialize last_params structure */
    memset(&last_params, 0, sizeof(last_params));
    clock_gettime(CLOCK_REALTIME, &last_params.last_update);
    
    gnss_initialized = true;
    
    if (current_config.verbose) {
        printf("GNSS: Initialized with host=%s, port=%s, timeout=%dms\n",
               current_config.gpsd_host, current_config.gpsd_port, current_config.timeout_ms);
    }
    
    return 0;
}

void gnss_cleanup(void)
{
    if (gnss_connected) {
        gnss_disconnect();
    }
    
    if (current_config.gpsd_host) {
        free(current_config.gpsd_host);
        current_config.gpsd_host = NULL;
    }
    if (current_config.gpsd_port) {
        free(current_config.gpsd_port);
        current_config.gpsd_port = NULL;
    }
    
    gnss_initialized = false;
    
    if (current_config.verbose) {
        printf("GNSS: Cleanup completed\n");
    }
}

bool gnss_is_available(void)
{
    if (!gnss_initialized) {
        return false;
    }
    
    if (!gnss_connected) {
        if (gnss_connect() != 0) {
            return false;
        }
    }
    
    return gnss_connected;
}

static int gnss_connect(void)
{
    int ret;
    
    if (gnss_connected) {
        return 0;
    }
    
    /* Open connection to GPSD */
    ret = gps_open(current_config.gpsd_host, current_config.gpsd_port, &gnss_gps_data);
    if (ret != 0) {
        if (current_config.verbose) {
            fprintf(stderr, "GNSS: Failed to connect to GPSD at %s:%s - %s\n",
                    current_config.gpsd_host, current_config.gpsd_port, gps_errstr(ret));
        }
        return -1;
    }
    
    /* Start watching for updates */
    ret = gps_stream(&gnss_gps_data, WATCH_ENABLE | WATCH_JSON, NULL);
    if (ret != 0) {
        if (current_config.verbose) {
            fprintf(stderr, "GNSS: Failed to start GPS stream - %s\n", gps_errstr(ret));
        }
        gps_close(&gnss_gps_data);
        return -1;
    }
    
    gnss_connected = true;
    
    if (current_config.verbose) {
        printf("GNSS: Connected to GPSD at %s:%s\n",
               current_config.gpsd_host, current_config.gpsd_port);
    }
    
    return 0;
}

static void gnss_disconnect(void)
{
    if (gnss_connected) {
        gps_stream(&gnss_gps_data, WATCH_DISABLE, NULL);
        gps_close(&gnss_gps_data);
        gnss_connected = false;
        
        if (current_config.verbose) {
            printf("GNSS: Disconnected from GPSD\n");
        }
    }
}

int gnss_read_clock_params(gnss_clock_params_t *params)
{
    int ret;
    struct timespec current_time;
    
    if (!params) {
        return -EINVAL;
    }
    
    if (!gnss_initialized) {
        return -ENOTCONN;
    }
    
    if (!gnss_connected) {
        ret = gnss_connect();
        if (ret != 0) {
            return ret;
        }
    }
    
    /* Initialize parameters structure */
    memset(params, 0, sizeof(*params));
    clock_gettime(CLOCK_REALTIME, &current_time);
    params->system_time = current_time;
    params->last_update = current_time;
    
    /* Wait for GPS data with timeout */
    if (gps_waiting(&gnss_gps_data, current_config.timeout_ms * 1000)) {
        ret = gps_read(&gnss_gps_data, NULL, 0);
        if (ret < 0) {
            if (current_config.verbose) {
                fprintf(stderr, "GNSS: Failed to read GPS data - %s\n", gps_errstr(ret));
            }
            params->connected = false;
            return -1;
        }
        
        params->connected = true;
        
        /* Extract basic fix information */
        params->fix_status = convert_gps_fix_mode(gnss_gps_data.fix.mode);
        params->satellites_used = gnss_gps_data.satellites_used;
        params->satellites_visible = gnss_gps_data.satellites_visible;
        
        /* Time information */
        if (gnss_gps_data.set & TIME_SET) {
            params->time_valid = true;
            params->gnss_time.tv_sec = (time_t)gnss_gps_data.fix.time.tv_sec;
            params->gnss_time.tv_nsec = gnss_gps_data.fix.time.tv_nsec;
            params->time_offset_ns = gnss_calculate_time_offset(params->gnss_time, params->system_time);
            
            /* Time uncertainty (estimate based on fix quality) */
            if (gnss_gps_data.set & TIMERR_SET) {
                params->time_uncertainty_ns = gnss_gps_data.fix.ept * 1e9; /* Convert seconds to nanoseconds */
            } else {
                /* Estimate based on fix type */
                switch (params->fix_status) {
                    case GNSS_FIX_3D:
                        params->time_uncertainty_ns = 100; /* ~100ns for good 3D fix */
                        break;
                    case GNSS_FIX_2D:
                        params->time_uncertainty_ns = 1000; /* ~1μs for 2D fix */
                        break;
                    default:
                        params->time_uncertainty_ns = 10000; /* ~10μs for poor fix */
                        break;
                }
            }
        }
        
        /* Position information */
        if (gnss_gps_data.set & LATLON_SET) {
            params->position_valid = true;
            params->latitude = gnss_gps_data.fix.latitude;
            params->longitude = gnss_gps_data.fix.longitude;
            
            if (gnss_gps_data.set & ALTITUDE_SET) {
                params->altitude = gnss_gps_data.fix.altHAE; /* Height Above Ellipsoid */
            }
            
            /* Position error estimate */
            if (gnss_gps_data.set & HERR_SET) {
                params->position_error_m = gnss_gps_data.fix.eph;
            }
        }
        
        /* Calculate dilution of precision values */
        calculate_dilution_of_precision(params);
        
        /* UTC offset information */
        if (gnss_gps_data.set & SUBFRAME_SET) {
            /* This would require decoding subframe data for precise UTC offset */
            /* For now, use a reasonable default */
            params->current_utc_offset = 37; /* Current GPS-UTC offset (as of 2024) */
            params->current_utc_offset_valid = true;
        }
        
        /* Set PTP time properties */
        params->ptp_timescale = true; /* We're using GNSS/GPS time */
        params->time_traceable = (params->fix_status >= GNSS_FIX_3D);
        params->frequency_traceable = (params->fix_status >= GNSS_FIX_3D);
        params->time_source = PTP_TIME_SOURCE_GPS;
        
        /* Assess clock quality and PTP parameters */
        assess_clock_quality(params);
        gnss_assess_ptp_parameters(params);
        
        /* Update statistics */
        last_params.total_readings++;
        if (params->time_valid && params->position_valid) {
            last_params.valid_readings++;
            if (last_params.first_fix_time.tv_sec == 0) {
                last_params.first_fix_time = current_time;
            }
        } else {
            last_params.invalid_readings++;
        }
        
        /* Copy statistics to current params */
        params->total_readings = last_params.total_readings;
        params->valid_readings = last_params.valid_readings;
        params->invalid_readings = last_params.invalid_readings;
        params->first_fix_time = last_params.first_fix_time;
        
    } else {
        /* No data available within timeout */
        params->connected = gnss_connected;
        params->time_valid = false;
        params->position_valid = false;
        
        if (current_config.verbose) {
            printf("GNSS: No data received within timeout (%dms)\n", current_config.timeout_ms);
        }
        
        return -ETIMEDOUT;
    }
    
    return 0;
}

int gnss_get_status_summary(char *summary, size_t size)
{
    gnss_clock_params_t params;
    int ret;
    
    if (!summary || size < 256) {
        return -EINVAL;
    }
    
    ret = gnss_read_clock_params(&params);
    if (ret != 0) {
        snprintf(summary, size, "GNSS: Not available or error reading data");
        return ret;
    }
    
    snprintf(summary, size,
             "GNSS: %s, Fix=%s, Sats=%d/%d, Quality=%s, Time=%s, Position=%s, Offset=%.0fns",
             params.connected ? "Connected" : "Disconnected",
             gnss_fix_status_str(params.fix_status),
             params.satellites_used, params.satellites_visible,
             gnss_clock_quality_str(params.clock_quality),
             params.time_valid ? "Valid" : "Invalid",
             params.position_valid ? "Valid" : "Invalid",
             params.time_offset_ns);
    
    return 0;
}

const char *gnss_fix_status_str(gnss_fix_status_t status)
{
    switch (status) {
        case GNSS_FIX_NONE: return "No Fix";
        case GNSS_FIX_2D: return "2D Fix";
        case GNSS_FIX_3D: return "3D Fix";
        case GNSS_FIX_DGPS: return "DGPS";
        case GNSS_FIX_RTK: return "RTK";
        default: return "Unknown";
    }
}

const char *gnss_clock_quality_str(gnss_clock_quality_t quality)
{
    switch (quality) {
        case GNSS_CLOCK_QUALITY_PRC: return "Primary Reference";
        case GNSS_CLOCK_QUALITY_SSU_A: return "SSU-A";
        case GNSS_CLOCK_QUALITY_SSU_B: return "SSU-B";
        case GNSS_CLOCK_QUALITY_SEC: return "SEC";
        case GNSS_CLOCK_QUALITY_DNU: return "Do Not Use";
        default: return "Unknown";
    }
}

double gnss_calculate_time_offset(struct timespec gnss_time, struct timespec system_time)
{
    double gnss_ns = gnss_time.tv_sec * 1e9 + gnss_time.tv_nsec;
    double system_ns = system_time.tv_sec * 1e9 + system_time.tv_nsec;
    return gnss_ns - system_ns;
}

void gnss_assess_ptp_parameters(gnss_clock_params_t *params)
{
    if (!params) {
        return;
    }
    
    /* Assess PTP Clock Class based on GNSS quality */
    switch (params->clock_quality) {
        case GNSS_CLOCK_QUALITY_PRC:
            params->ptp_clock_class = PTP_CLASS_PRIMARY_REFERENCE;
            params->ptp_clock_accuracy = 0x17; /* Better than 1μs */
            params->ptp_offset_scaled_log_variance = 0x436A; /* ~1000ns variance */
            break;
            
        case GNSS_CLOCK_QUALITY_SSU_A:
            params->ptp_clock_class = PTP_CLASS_PRIMARY_REFERENCE_DEGRADED;
            params->ptp_clock_accuracy = 0x18; /* Better than 2.5μs */
            params->ptp_offset_scaled_log_variance = 0x4E5D; /* ~10μs variance */
            break;
            
        case GNSS_CLOCK_QUALITY_SSU_B:
        case GNSS_CLOCK_QUALITY_SEC:
            params->ptp_clock_class = PTP_CLASS_SECONDARY_REFERENCE;
            params->ptp_clock_accuracy = 0x19; /* Better than 10μs */
            params->ptp_offset_scaled_log_variance = 0x5A62; /* ~100μs variance */
            break;
            
        case GNSS_CLOCK_QUALITY_DNU:
            params->ptp_clock_class = PTP_CLASS_SLAVE_ONLY;
            params->ptp_clock_accuracy = 0xFE; /* Unknown/worst case */
            params->ptp_offset_scaled_log_variance = 0xFFFF; /* Maximum variance */
            break;
            
        default:
            params->ptp_clock_class = PTP_CLASS_DEFAULT_CLOCK;
            params->ptp_clock_accuracy = 0x20; /* Better than 25μs */
            params->ptp_offset_scaled_log_variance = 0x6265; /* ~1ms variance */
            break;
    }
}

void gnss_print_params(const gnss_clock_params_t *params)
{
    if (!params) {
        return;
    }
    
    printf("\n=== GNSS Clock Parameters ===\n");
    printf("Connection: %s\n", params->connected ? "Connected" : "Disconnected");
    printf("Fix Status: %s\n", gnss_fix_status_str(params->fix_status));
    printf("Satellites: %d used, %d visible\n", params->satellites_used, params->satellites_visible);
    
    if (params->time_valid) {
        printf("GNSS Time: %ld.%09ld\n", params->gnss_time.tv_sec, params->gnss_time.tv_nsec);
        printf("System Time: %ld.%09ld\n", params->system_time.tv_sec, params->system_time.tv_nsec);
        printf("Time Offset: %.0f ns\n", params->time_offset_ns);
        printf("Time Uncertainty: %.0f ns\n", params->time_uncertainty_ns);
    } else {
        printf("Time: Invalid\n");
    }
    
    if (params->position_valid) {
        printf("Position: %.6f°, %.6f°, %.1fm\n", params->latitude, params->longitude, params->altitude);
        printf("Position Error: %.1f m\n", params->position_error_m);
    } else {
        printf("Position: Invalid\n");
    }
    
    printf("Clock Quality: %s\n", gnss_clock_quality_str(params->clock_quality));
    printf("PTP Clock Class: %d\n", params->ptp_clock_class);
    printf("PTP Clock Accuracy: 0x%02X\n", params->ptp_clock_accuracy);
    printf("UTC Offset: %d%s\n", params->current_utc_offset, 
           params->current_utc_offset_valid ? "" : " (estimated)");
    
    printf("Dilution of Precision: GDOP=%.2f, HDOP=%.2f, VDOP=%.2f, TDOP=%.2f\n",
           params->geometric_dilution, params->horizontal_dilution, 
           params->vertical_dilution, params->time_dilution);
    
    printf("Statistics: %lu total, %lu valid, %lu invalid readings\n",
           params->total_readings, params->valid_readings, params->invalid_readings);
    
    printf("Time Properties: Traceable=%s, Frequency Traceable=%s, Source=0x%02X\n",
           params->time_traceable ? "Yes" : "No",
           params->frequency_traceable ? "Yes" : "No",
           params->time_source);
    printf("==============================\n\n");
}

/* Internal helper functions */

static gnss_fix_status_t convert_gps_fix_mode(int mode)
{
    switch (mode) {
        case MODE_NO_FIX: return GNSS_FIX_NONE;
        case MODE_2D: return GNSS_FIX_2D;
        case MODE_3D: return GNSS_FIX_3D;
        default: return GNSS_FIX_NONE;
    }
}

static void calculate_dilution_of_precision(gnss_clock_params_t *params)
{
    /* Extract DOP values from GPS data if available */
    if (gnss_gps_data.set & DOP_SET) {
        params->geometric_dilution = gnss_gps_data.dop.gdop;
        params->horizontal_dilution = gnss_gps_data.dop.hdop;
        params->vertical_dilution = gnss_gps_data.dop.vdop;
        params->time_dilution = gnss_gps_data.dop.tdop;
    } else {
        /* Estimate based on satellite count and fix type */
        if (params->satellites_used >= 8) {
            params->geometric_dilution = 2.0;
            params->horizontal_dilution = 1.5;
            params->vertical_dilution = 2.5;
            params->time_dilution = 1.8;
        } else if (params->satellites_used >= 6) {
            params->geometric_dilution = 3.0;
            params->horizontal_dilution = 2.0;
            params->vertical_dilution = 3.5;
            params->time_dilution = 2.5;
        } else if (params->satellites_used >= 4) {
            params->geometric_dilution = 5.0;
            params->horizontal_dilution = 3.0;
            params->vertical_dilution = 5.5;
            params->time_dilution = 4.0;
        } else {
            params->geometric_dilution = 10.0;
            params->horizontal_dilution = 8.0;
            params->vertical_dilution = 12.0;
            params->time_dilution = 8.0;
        }
    }
}

static void assess_clock_quality(gnss_clock_params_t *params)
{
    /* Assess clock quality based on multiple factors */
    
    if (!params->time_valid || !params->position_valid) {
        params->clock_quality = GNSS_CLOCK_QUALITY_DNU;
        return;
    }
    
    /* Primary factors: fix type, satellite count, DOP values, time uncertainty */
    int quality_score = 0;
    
    /* Fix type contribution */
    switch (params->fix_status) {
        case GNSS_FIX_3D:
            quality_score += 40;
            break;
        case GNSS_FIX_2D:
            quality_score += 20;
            break;
        default:
            quality_score += 0;
            break;
    }
    
    /* Satellite count contribution */
    if (params->satellites_used >= 8) {
        quality_score += 30;
    } else if (params->satellites_used >= 6) {
        quality_score += 20;
    } else if (params->satellites_used >= 4) {
        quality_score += 10;
    }
    
    /* GDOP contribution */
    if (params->geometric_dilution <= 2.0) {
        quality_score += 20;
    } else if (params->geometric_dilution <= 4.0) {
        quality_score += 10;
    } else if (params->geometric_dilution <= 6.0) {
        quality_score += 5;
    }
    
    /* Time uncertainty contribution */
    if (params->time_uncertainty_ns <= 100) {
        quality_score += 10;
    } else if (params->time_uncertainty_ns <= 1000) {
        quality_score += 5;
    }
    
    /* Determine quality level based on total score */
    if (quality_score >= 90) {
        params->clock_quality = GNSS_CLOCK_QUALITY_PRC;
    } else if (quality_score >= 70) {
        params->clock_quality = GNSS_CLOCK_QUALITY_SSU_A;
    } else if (quality_score >= 50) {
        params->clock_quality = GNSS_CLOCK_QUALITY_SSU_B;
    } else if (quality_score >= 30) {
        params->clock_quality = GNSS_CLOCK_QUALITY_SEC;
    } else {
        params->clock_quality = GNSS_CLOCK_QUALITY_DNU;
    }
}
