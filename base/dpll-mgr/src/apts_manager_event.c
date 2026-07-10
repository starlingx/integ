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
 * @file apts_manager_event.c
 * @brief Event-based main loop for APTS Manager
 *
 * Compiled when BUILD_MODE=event.
 * Subscribes to the DPLL "monitor" multicast group so the kernel pushes
 * DPLL_CMD_DEVICE_CHANGE_NTF notifications; all other notification types are
 * discarded at the handler level.
 * A poll() call blocks on both the DPLL netlink socket and the local PTP
 * UDS socket; master transitions are therefore detected within one kernel
 * notification latency rather than at a fixed 8 ms polling interval.
 */

#define _DEFAULT_SOURCE
#define MODULE "EVENT"

#include <poll.h>
#include <ynl/ynl.h>
#include "../hdr/apts_manager.h"
#include "../hdr/ptp_protocol.h"
#include "../hdr/dpll_phase_adjust.h"
#include "../hdr/dpll_utils.h"
#include "../hdr/config_parser.h"

/**
 * dpll_subscribe_events - Subscribe to the DPLL "monitor" multicast group
 * @dpll_sock: Open YNL socket bound to the dpll generic netlink family
 *
 * Joins DPLL_MCGRP_MONITOR so the kernel pushes DPLL notifications without
 * polling.  Only DPLL_CMD_DEVICE_CHANGE_NTF events are acted upon; all other
 * notification types received on this group are discarded by the handler.
 *
 * Returns: 0 on success, -1 on failure
 */
static int dpll_subscribe_events(struct ynl_sock *dpll_sock)
{
    int ret = ynl_subscribe(dpll_sock, DPLL_MCGRP_MONITOR);
    if (ret < 0) {
        LOG_ERROR("Failed to subscribe to DPLL '%s' monitor group (ret=%d)\n",
                  DPLL_MCGRP_MONITOR, ret);
        return -1;
    }
    LOG_INFO("Subscribed to DPLL '%s' multicast group\n", DPLL_MCGRP_MONITOR);
    return 0;
}

/**
 * dpll_handle_events - Parse and dispatch DPLL_CMD_DEVICE_CHANGE_NTF events
 * @state:     Application state
 * @dpll_sock: DPLL YNL socket (already subscribed to monitor group)
 *
 * Reads all queued notifications from the netlink socket and processes only
 * DPLL_CMD_DEVICE_CHANGE_NTF events by calling process_dpll_master_state().
 * All other notification types are freed and discarded.
 */
static void dpll_handle_events(AppState *state, struct ynl_sock *dpll_sock)
{
    if (ynl_ntf_check(dpll_sock) < 0) {
        LOG_ERROR("ynl_ntf_check() failed\n");
        return;
    }

    struct ynl_ntf_base_type *ntf;
    while (ynl_has_ntf(dpll_sock)) {
        ntf = ynl_ntf_dequeue(dpll_sock);
        if (!ntf)
            break;

        if (ntf->cmd != DPLL_CMD_DEVICE_CHANGE_NTF) {
            LOG_DEBUG("Ignoring event cmd=%u\n", ntf->cmd);
            ynl_ntf_free(ntf);
            continue;
        }

        struct dpll_device_get_ntf *dev_ntf =
            (struct dpll_device_get_ntf *)ntf;
        if (dev_ntf->obj._present.lock_status) {
            LOG_INFO("DPLL_CMD_DEVICE_CHANGE_NTF: device_id=%s%u lock_status=%u (%s)\n",
                     dev_ntf->obj._present.id ? "" : "(not present) ",
                     dev_ntf->obj.id,
                     dev_ntf->obj.lock_status,
                     dpll_lock_status_str(dev_ntf->obj.lock_status));
        } else {
            LOG_INFO("DPLL_CMD_DEVICE_CHANGE_NTF: device_id=%s%u\n",
                     dev_ntf->obj._present.id ? "" : "(not present) ",
                     dev_ntf->obj.id);
        }
        process_dpll_master_state(state, dpll_sock);

        ynl_ntf_free(ntf);
    }
}

/**
 * run_main_loop - Event-based main loop driven by DPLL netlink notifications
 * @state:     Application state
 * @dpll_sock: Initialised DPLL netlink socket
 *
 * Subscribes to the DPLL "monitor" multicast group, then blocks in poll()
 * waiting for DPLL events or incoming PTP management messages.
 *
 * - DPLL device/pin change → dpll_handle_events() → process_dpll_master_state()
 * - PTP socket readable     → process_ptp_messages()
 * - 1 s poll timeout        → PTP subscription renewal + phase adjustment
 *
 * This eliminates the fixed 8 ms polling period for DPLL: master transitions
 * are detected within one kernel notification latency.
 */
void run_main_loop(AppState *state, struct ynl_sock *dpll_sock)
{
    LOG_INFO("=== ENTERING EVENT-BASED MAIN LOOP ===\n");
    LOG_INFO("Subscribing to DPLL monitor events...\n");

    if (dpll_subscribe_events(dpll_sock) < 0) {
        LOG_ERROR("Cannot enter event loop: DPLL subscribe failed\n");
        return;
    }

    int dpll_fd = ynl_socket_get_fd(dpll_sock);
    LOG_INFO("Listening for DPLL events on fd=%d (Press Ctrl+C to exit)...\n", dpll_fd);

    while (running) {
        struct pollfd pfds[2];
        int nfds = 0;

        /* fd 0: DPLL netlink events */
        pfds[nfds].fd     = dpll_fd;
        pfds[nfds].events = POLLIN;
        nfds++;

        /* fd 1: local PTP socket for management messages */
        if (state->local_socket_fd >= 0) {
            pfds[nfds].fd     = state->local_socket_fd;
            pfds[nfds].events = POLLIN;
            nfds++;
        }

        /* Block until an event arrives or 1 s elapses (for housekeeping) */
        int rc = poll(pfds, nfds, 1000);
        if (rc < 0) {
            if (errno == EINTR)
                continue;
            LOG_ERROR("poll() failed: %s\n", strerror(errno));
            break;
        }

        /* Handle DPLL notifications */
        if (pfds[0].revents & POLLIN)
            dpll_handle_events(state, dpll_sock);


#ifdef ENABLE_PTP_SUBSCRIPTION
        /* Renew PTP subscription periodically regardless of events */
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        long elapsed = now.tv_sec - state->last_subscription.tv_sec;
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

        /* Re-evaluate holdover tiers on poll timeout. During holdover, no
         * DPLL notifications arrive (hardware state is static), so tier
         * progression must be checked periodically. The 1s poll timeout
         * ensures this runs at least once per second. */
        if (state->in_holdover)
            process_dpll_master_state(state, dpll_sock);

        /* HW_BASED mode: periodic phase adjustment */
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
    }
}
