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

/* GNSS Clock Parameters Structure */
typedef struct {
    /* Connection and validity */
    bool connected;
    
    /* Time information */
    struct timespec gnss_time;
    struct timespec system_time;
    double time_offset_ns;       /* GNSS - System time (nanoseconds) */
    double time_uncertainty_ns;  /* Time uncertainty (nanoseconds) */
    
    /* Clock quality assessment */
    gnss_clock_quality_t clock_quality; /* Can be derived */
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

/**
 * Initialize GNSS utilities
 */
int gnss_init(const gnss_config_t *config);

/**
 * Cleanup GNSS utilities
 */
void gnss_cleanup(void);

/**
 * Check if GNSS is available and connected
 */
bool gnss_is_available(void);

int gnss_read_clock_params(gnss_clock_params_t *params);

/**
 * Calculate time offset between GNSS and system time
 */
double gnss_calculate_time_offset(struct timespec gnss_time, struct timespec system_time);

/**
 * Derives PTP clock parameters from GNSS data
 */
void gnss_assess_ptp_parameters(gnss_clock_params_t *params);

/**
 * Print detailed GNSS parameters (for debugging)
 */
void gnss_print_params(const gnss_clock_params_t *params);

#endif /* GNSS_UTILS_H */
