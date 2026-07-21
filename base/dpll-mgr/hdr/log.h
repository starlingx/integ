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
 * @file log.h
 * @brief Logging System Header
 * 
 * Centralized logging macros and level definitions for the application.
 * All modules should include this header for consistent logging.
 */

#ifndef LOG_H
#define LOG_H

#include <stdio.h>
#include <time.h>

/**
 * Log levels - controls verbosity of output
 */
typedef enum {
    LOG_LEVEL_ERROR = 0,    /* Critical errors only */
    LOG_LEVEL_INFO = 1,     /* Informational messages */
    LOG_LEVEL_DEBUG = 2,    /* Detailed debugging */
    LOG_LEVEL_RAW = 3       /* Raw data dumps */
} LogLevel;

/* Global logging configuration */
extern FILE *g_log_file;        /* Log output file (NULL = stdout/stderr) */
extern LogLevel g_log_level;    /* Current log level threshold */

/**
 * Helper macro to get timestamp in ptp4l format [seconds.microseconds]
 */
#define GET_TIMESTAMP() ({ \
    struct timespec _ts; \
    clock_gettime(CLOCK_MONOTONIC, &_ts); \
    _ts; \
})

/**
 * Logging Macros
 */

#define LOG_INFO(...) do { if (g_log_level >= LOG_LEVEL_INFO) { FILE *out = g_log_file ? g_log_file : stdout; struct timespec _ts = GET_TIMESTAMP(); fprintf(out, "[dpll_mgr][%ld.%03ld] ", _ts.tv_sec, _ts.tv_nsec / 1000000); fprintf(out, __VA_ARGS__); fflush(out); } } while(0)
#define LOG_ERROR(...) do { if (g_log_level >= LOG_LEVEL_ERROR) { FILE *out = g_log_file ? g_log_file : stderr; struct timespec _ts = GET_TIMESTAMP(); fprintf(out, "[dpll_mgr][%ld.%03ld] ", _ts.tv_sec, _ts.tv_nsec / 1000000); fprintf(out, __VA_ARGS__); fflush(out); } } while(0)
#define LOG_DEBUG(...) do { if (g_log_level >= LOG_LEVEL_DEBUG) { FILE *out = g_log_file ? g_log_file : stdout; struct timespec _ts = GET_TIMESTAMP(); fprintf(out, "[dpll_mgr][%ld.%03ld] ", _ts.tv_sec, _ts.tv_nsec / 1000000); fprintf(out, __VA_ARGS__); fflush(out); } } while(0)
#define LOG_RAW(...) do { if (g_log_level >= LOG_LEVEL_RAW) { FILE *out = g_log_file ? g_log_file : stdout; struct timespec _ts = GET_TIMESTAMP(); fprintf(out, "[dpll_mgr][%ld.%03ld] ", _ts.tv_sec, _ts.tv_nsec / 1000000); fprintf(out, __VA_ARGS__); fflush(out); } } while(0)

#endif /* LOG_H */
