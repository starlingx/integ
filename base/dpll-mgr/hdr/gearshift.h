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
 * @file gearshift.h
 * @brief Gearshift control for SW_BASED operation mode
 *
 * Provides socket lifecycle management and PTP management message sending
 * for MID_GEARSHIFT_NP SET commands to ptp4l and ts2phc daemons on failover.
 */

#ifndef GEARSHIFT_H
#define GEARSHIFT_H

#include "dpll_manager.h"

/* Gear mode values matching linuxptp enum gear_mode */
#define GEAR_PARK     0
#define GEAR_NEUTRAL  1
#define GEAR_DRIVE    2

/*
 * GEAR_IDLE is the "non-active" gear used on failover for the daemon being
 * demoted.  By default it maps to PARK.  Build with -UUSE_GEAR_PARK to
 * map it to NEUTRAL instead:
 */
#ifdef USE_GEAR_PARK
#define GEAR_IDLE      GEAR_PARK
#define GEAR_IDLE_STR  "PARK"
#else
#define GEAR_IDLE      GEAR_NEUTRAL
#define GEAR_IDLE_STR  "NEUTRAL"
#endif

/**
 * handle_sw_based_failover - Send gearshift SET messages on failover
 * @state: Application state
 * @new_master: New master source after failover
 *
 * Failover to GNSS: ptp4l(ptp_bh) -> NEUTRAL, ts2phc(ts2_0) -> DRIVE
 * Failover to PTP:  ts2phc(ts2_0) -> NEUTRAL, ptp4l(ptp_bh)  -> DRIVE
 */
void handle_sw_based_failover(AppState *state, enum pin_source new_master);

#endif /* GEARSHIFT_H */
