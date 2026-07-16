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
 * @file dpll_manager_poll.c
 * @brief Polling-based main loop for APTS Manager
 *
 * Compiled when BUILD_MODE=poll (default).
 * Polls DPLL state every 8 ms (~125 Hz) and processes ptp4l management
 * messages on every iteration.  On a master transition, triggers gearshift
 * and clock parameter refresh via process_dpll_master_state().
 */

#define _DEFAULT_SOURCE
#define MODULE "POLL"

#include "../hdr/dpll_manager.h"
#include "../hdr/ptp_protocol.h"
#include "../hdr/dpll_phase_adjust.h"
#include "../hdr/config_parser.h"

/**
 * run_main_loop - Poll-based main loop
 * @state:     Application state
 * @dpll_sock: Initialised DPLL netlink socket
 *
 * Loops until the global `running` flag is cleared by a signal.
 * Each 8 ms iteration:
 *   1. Calls process_dpll_master_state() to detect master transitions and
 *      trigger gearshift / clock parameter refresh as needed.
 *   2. Renews the ptp4l event subscription before it expires (if enabled).
 *   3. Drains all pending messages from the ptp4l UDS socket.
 *   4. (HW_BASED only) Monitors and adjusts PHC phase offset.
 */
void run_main_loop(AppState *state, struct ynl_sock *dpll_sock)
{
    LOG_INFO("=== ENTERING POLLING MAIN LOOP ===\n");
    LOG_INFO("Starting polling loop (Press Ctrl+C to exit)...\n");
    LOG_INFO("Operation Mode: POLLING\n");

    while (running) {
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);

        process_dpll_master_state(state, dpll_sock);

#ifdef ENABLE_PTP_SUBSCRIPTION
        long volatile elapsed = now.tv_sec - state->last_subscription.tv_sec;
        if (elapsed > (SUBSCRIPTION_DURATION - 10)) {
            state->subscription_active = false;
            int ret = send_subscription_request(state->local_socket_fd,
                          &state->local_peer_addr, &state->local_sequence_id);
            if (ret) {
                clock_gettime(CLOCK_MONOTONIC, &state->last_subscription);
            } else {
                LOG_ERROR("Subscription request failed\n");
            }
        }
#endif
        process_ptp_messages(state);

        /* HW_BASED mode only: adjust phase offset */
        if (g_config.manager.operation_mode != OPERATION_MODE_SW_BASED) {
            if (state->ptp_pin_state == DPLL_PIN_STATE_SELECTABLE ||
                state->ptp_pin_state == DPLL_PIN_STATE_CONNECTED) {
                monitor_and_adjust_phase_offset(state);
            } else {
                LOG_DEBUG("Skipping phase adjustment: ptp_pin_state=%d "
                          "(need SELECTABLE=%d or CONNECTED=%d)\n",
                          state->ptp_pin_state,
                          DPLL_PIN_STATE_SELECTABLE,
                          DPLL_PIN_STATE_CONNECTED);
            }
        }

        /* Sleep 8 ms → ~125 iterations per second */
        usleep(8000);
    }
}
