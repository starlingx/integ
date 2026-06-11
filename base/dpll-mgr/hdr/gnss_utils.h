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


#ifndef GNSS_UTILS_H
#define GNSS_UTILS_H

#include <stdint.h>
#include <stdbool.h>
#include <time.h>

/* GNSS Clock Quality Levels based on ITU-T G.8272 */
typedef enum {
    GNSS_CLOCK_QUALITY_UNKNOWN = 0,
    GNSS_CLOCK_QUALITY_PRC = 1,      /* Primary Reference Clock */
    GNSS_CLOCK_QUALITY_SSU_A = 2,    /* Synchronization Supply Unit A */
    GNSS_CLOCK_QUALITY_SSU_B = 3,    /* Synchronization Supply Unit B */
    GNSS_CLOCK_QUALITY_SEC = 4,      /* SDH Equipment Clock */
    GNSS_CLOCK_QUALITY_DNU = 15      /* Do Not Use */
} gnss_clock_quality_t;

/* GNSS Fix Status */
typedef enum {
    GNSS_FIX_NONE = 0,
    GNSS_FIX_2D = 1,
    GNSS_FIX_3D = 2,
    GNSS_FIX_DGPS = 3,
    GNSS_FIX_RTK = 4
} gnss_fix_status_t;

/* GNSS Clock Parameters Structure */
typedef struct {
    /* Connection and validity */
    bool connected;
    bool time_valid;
    bool position_valid;
    
    /* Fix information */
    gnss_fix_status_t fix_status;
    int satellites_used;
    int satellites_visible;
    
    /* Time information */
    struct timespec gnss_time;
    struct timespec system_time;
    double time_offset_ns;       /* GNSS - System time (nanoseconds) */
    double time_uncertainty_ns;  /* Time uncertainty (nanoseconds) */
    
    /* Position information */
    double latitude;
    double longitude;
    double altitude;
    double position_error_m;     /* Position error (meters) */
    
    /* Clock quality assessment */
    gnss_clock_quality_t clock_quality;
    uint8_t ptp_clock_class;     /* PTP Clock Class (6-248) */
    uint8_t ptp_clock_accuracy;  /* PTP Clock Accuracy (0x17-0xFE) */
    uint16_t ptp_offset_scaled_log_variance; /* PTP Offset Scaled Log Variance */
    
    /* PTP time properties */
    uint8_t current_utc_offset;  /* Current UTC offset (leap seconds) */
    bool current_utc_offset_valid;
    bool leap61;                 /* Leap second +1 pending */
    bool leap59;                 /* Leap second -1 pending */
    bool ptp_timescale;         /* Using PTP timescale */
    bool time_traceable;        /* Time traceable to primary reference */
    bool frequency_traceable;   /* Frequency traceable to primary reference */
    uint8_t time_source;        /* Time source identifier */
    
    /* Signal quality metrics */
    double geometric_dilution;   /* GDOP */
    double horizontal_dilution;  /* HDOP */
    double vertical_dilution;    /* VDOP */
    double time_dilution;        /* TDOP */
    
    /* Statistics */
    uint64_t total_readings;
    uint64_t valid_readings;
    uint64_t invalid_readings;
    
    /* Timestamps */
    struct timespec last_update;
    struct timespec first_fix_time;
    
} gnss_clock_params_t;

/* GNSS Configuration */
typedef struct {
    char *gpsd_host;             /* GPSD host (default: localhost) */
    char *gpsd_port;             /* GPSD port (default: 2947) */
    int timeout_ms;              /* Connection timeout in milliseconds */
    bool verbose;                /* Enable verbose logging */
} gnss_config_t;

/* Function prototypes */

/**
 * Initialize GNSS utilities
 * @param config Configuration parameters (can be NULL for defaults)
 * @return 0 on success, negative on error
 */
int gnss_init(const gnss_config_t *config);

/**
 * Cleanup GNSS utilities
 */
void gnss_cleanup(void);

/**
 * Check if GNSS is available and connected
 * @return true if GNSS is available, false otherwise
 */
bool gnss_is_available(void);

/**
 * Read current GNSS clock parameters
 * @param params Pointer to structure to store parameters
 * @return 0 on success, negative on error
 */
int gnss_read_clock_params(gnss_clock_params_t *params);

/**
 * Get a quick status summary
 * @param summary Buffer to store status summary (at least 256 chars)
 * @return 0 on success, negative on error
 */
int gnss_get_status_summary(char *summary, size_t size);

/**
 * Convert fix status to string
 * @param status Fix status
 * @return String representation
 */
const char *gnss_fix_status_str(gnss_fix_status_t status);

/**
 * Convert clock quality to string
 * @param quality Clock quality
 * @return String representation
 */
const char *gnss_clock_quality_str(gnss_clock_quality_t quality);

/**
 * Calculate time offset between GNSS and system time
 * @param gnss_time GNSS timestamp
 * @param system_time System timestamp
 * @return Time offset in nanoseconds (GNSS - System)
 */
double gnss_calculate_time_offset(struct timespec gnss_time, struct timespec system_time);

/**
 * Assess PTP clock parameters from GNSS data
 * @param params GNSS parameters (input/output)
 */
void gnss_assess_ptp_parameters(gnss_clock_params_t *params);

/**
 * Print detailed GNSS parameters (for debugging)
 * @param params GNSS parameters to print
 */
void gnss_print_params(const gnss_clock_params_t *params);

/* Default configuration values */
#define GNSS_DEFAULT_HOST "localhost"
#define GNSS_DEFAULT_PORT "2947"
#define GNSS_DEFAULT_TIMEOUT_MS 5000

/* PTP Clock Class values based on GNSS quality */
#define PTP_CLASS_PRIMARY_REFERENCE 6
#define PTP_CLASS_PRIMARY_REFERENCE_DEGRADED 7
#define PTP_CLASS_SECONDARY_REFERENCE 52
#define PTP_CLASS_DEFAULT_CLOCK 187
#define PTP_CLASS_SLAVE_ONLY 248

/* PTP Time Source values */
#define PTP_TIME_SOURCE_ATOMIC_CLOCK 0x10
#define PTP_TIME_SOURCE_GPS 0x20
#define PTP_TIME_SOURCE_TERRESTRIAL_RADIO 0x30
#define PTP_TIME_SOURCE_PTP 0x40
#define PTP_TIME_SOURCE_NTP 0x50
#define PTP_TIME_SOURCE_HAND_SET 0x60
#define PTP_TIME_SOURCE_OTHER 0x90
#define PTP_TIME_SOURCE_INTERNAL_OSCILLATOR 0xA0

#endif /* GNSS_UTILS_H */
