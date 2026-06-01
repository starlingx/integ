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


#include "../hdr/dpll_phase_adjust.h"
#include "../hdr/ptp_protocol.h"
#include "../hdr/phc_utils.h"

#define DPLL_LOCK_WAIT_TIMEOUT_MS 60000
#define DPLL_LOCK_WAIT_POLL_MS      200

static const char *dpll_lock_status_to_str_local(enum dpll_lock_status status)
{
    switch (status) {
    case DPLL_LOCK_STATUS_LOCKED:
        return "LOCKED";
    case DPLL_LOCK_STATUS_LOCKED_HO_ACQ:
        return "LOCKED_HO_ACQ";
    case DPLL_LOCK_STATUS_UNLOCKED:
        return "UNLOCKED";
    case DPLL_LOCK_STATUS_HOLDOVER:
        return "HOLDOVER";
    default:
        return "UNKNOWN";
    }
}

static bool is_dpll_device_locked(enum dpll_lock_status status)
{
    return (status == DPLL_LOCK_STATUS_LOCKED ||
            status == DPLL_LOCK_STATUS_LOCKED_HO_ACQ);
}

static int wait_for_dpll_device_lock(AppState *state, int timeout_ms, int poll_ms, const char *phase)
{
    int elapsed_ms = 0;
    enum dpll_lock_status lock_status = DPLL_LOCK_STATUS_UNLOCKED;
    enum dpll_mode mode = (enum dpll_mode)0;
    __u32 connected_pin_id = 0;
    enum pin_source connected_pin_src = PIN_SOURCE_UNKNOWN;
    __u32 ptp_pin_id = state ? state->ptp_pin_id : 0;
    enum dpll_pin_state ptp_pin_state = state ? state->ptp_pin_state : DPLL_PIN_STATE_DISCONNECTED;

    if (!state || !state->dpll_sock) {
        return -1;
    }

    while (elapsed_ms <= timeout_ms) {
        (void)dpll_get_device_state_and_connected_pin(state->dpll_sock,
                                                       state->pps_dpll_device_id,
                                                       &lock_status,
                                                       &mode,
                                                       &connected_pin_id,
                                                       &connected_pin_src,
                                                       &ptp_pin_id,
                                                       &ptp_pin_state);

        state->lock_status = lock_status;
        state->ptp_pin_id = ptp_pin_id;
        state->ptp_pin_state = ptp_pin_state;

        if (elapsed_ms > 0 && (elapsed_ms % 10000) < poll_ms) {
            LOG_INFO("Waiting for DPLL lock: %d ms elapsed (%s), status=%s\n",
                     elapsed_ms, phase ? phase : "lock wait",
                     dpll_lock_status_to_str_local(lock_status));
        }

        if (is_dpll_device_locked(lock_status)) {
            LOG_INFO("DPLL is LOCKED after %d ms (%s)\n",
                     elapsed_ms, phase ? phase : "lock wait");
            return 0;
        }

        if (elapsed_ms >= timeout_ms) {
            break;
        }

        usleep((unsigned int)poll_ms * 1000U);
        elapsed_ms += poll_ms;
    }

    LOG_ERROR("DPLL did not reach LOCKED state within %d ms (%s), last status=%s\n",
             timeout_ms,
             phase ? phase : "lock wait",
             dpll_lock_status_to_str_local(state->lock_status));
    return -1;
}

/**
 * perform_phase_adjustment - Perform DPLL phase adjustment
 * @state: Application state
 * @dpll_sock: DPLL netlink socket
 * @master_offset_ns: Current master offset in nanoseconds
 * @apts_offset_ns: Previous saved offset in nanoseconds
 *
 * Performs gradual phase adjustment using DPLL phase adjust mechanism.
 * Used for small offsets (<100µs) that need smooth correction.
 *
 * Applies adjustment in multiple iterations (max 150ns per iteration)
 * to avoid large step corrections that could disturb DPLL lock.
 *
 * Returns: 0 on success, -1 on failure
 */
static int perform_phase_adjustment(AppState *state, struct ynl_sock *dpll_sock,
                                   int64_t master_offset_ns, int64_t apts_offset_ns)
{
    static uint64_t adjustment_skip_count = 0;

    /* Calculate difference from last saved offset */
    int64_t diff = master_offset_ns - apts_offset_ns;
    if (diff == 0) {
        adjustment_skip_count++;
        return 0;  /* No change detected, skip adjustment */
    }

    int64_t diff_phase_offset_ns = diff;

    /* Calculate adjustment magnitude based on diff */
    int64_t abs_diff = (diff_phase_offset_ns < 0) ? -diff_phase_offset_ns : diff_phase_offset_ns;

    int64_t scale = g_config.manager.phase_offset_factor;
    if (scale <= 0) {
        scale = 1;
    }
    int64_t adjustment_magnitude = abs_diff * scale;

    /* Apply sign based on master_offset
     * If master_offset > 0 (local clock is ahead), apply negative (delay)
     * If master_offset < 0 (local clock is behind), apply positive (advance)
     */
    int64_t phase_adjust_ns;
    if (master_offset_ns > 0) {
        phase_adjust_ns = -adjustment_magnitude;
    } else if (master_offset_ns < 0) {
        phase_adjust_ns = +adjustment_magnitude;
    } else {
        phase_adjust_ns = 0;
    }

    /* Calculate dynamic iteration count based on magnitude
     * Max 150 ns per iteration to avoid large step corrections
     */
    uint64_t max_adjust_per_iter_ns = 150;
    int64_t num_iterations = (adjustment_magnitude + max_adjust_per_iter_ns - 1) / max_adjust_per_iter_ns;

    /* Calculate per-iteration adjustment (ceiling division) */
    int64_t phase_adjust_ns_per_iter;
    if (phase_adjust_ns > 0) {
        phase_adjust_ns_per_iter = (phase_adjust_ns + num_iterations - 1) / num_iterations;
    } else if (phase_adjust_ns < 0) {
        phase_adjust_ns_per_iter = (phase_adjust_ns - num_iterations + 1) / num_iterations;
    } else {
        phase_adjust_ns_per_iter = 0;
    }
    int64_t phase_adjust_ps_per_iter = phase_adjust_ns_per_iter * 1000LL;

    /* Get connected pin information to apply adjustment */
    struct dpll_pin_get_req pin_req = {
        ._present = {
            .id = 1,
        },
        .id = state->ptp_pin_id,
    };

    struct dpll_pin_get_rsp *pin_rsp = dpll_pin_get(dpll_sock, &pin_req);
    if (!pin_rsp || !pin_rsp->package_label) {
        LOG_ERROR("Failed to get pin info for pin_id %u\n", state->ptp_pin_id);
        if (pin_rsp) {
            dpll_pin_get_rsp_free(pin_rsp);
        }
        return -1;
    }

    /* Get phase_offset from parent device (initial state) */
    __s64 pin_phase_offset = 0;
    __u32 pin_state = 0;
    if (pin_rsp->parent_device && pin_rsp->n_parent_device >= 2) {
        pin_phase_offset = pin_rsp->parent_device[1].phase_offset;
        if (pin_rsp->parent_device[1]._present.state) {
            pin_state = pin_rsp->parent_device[1].state;
        }
    }

    /* Get DPLL lock status string */
    const char *lock_status_str = "UNKNOWN";
    const char *lock_states[] = {"", "UNLOCKED", "LOCKED", "LOCKED_HO_ACQ", "HOLDOVER"};
    if (state->lock_status >= 1 && state->lock_status <= 4) {
        lock_status_str = lock_states[state->lock_status];
    }

        LOG_INFO("Adjust: timeOff %+4lld ns, diff %+4lld ns, phase_adj %+7lld ns, iterations %4lld, adj_per_iter %+4lld ns, phase_offset %+9lld ps, state %u, DPLL: %s\n",
          (long long)master_offset_ns,
          (long long)diff,
          (long long)phase_adjust_ns,
          (long long)num_iterations,
          (long long)phase_adjust_ns_per_iter,
          (long long)(pin_phase_offset / 1000),
          pin_state,
            lock_status_str);

    /* Apply adjustment num_iterations times */
    __s64 old_phase_adjust = 0;
    for (int i = 0; i < num_iterations; i++) {
        old_phase_adjust = dpll_pin_set_phase_adjust(dpll_sock,
                                                      "REF0P",
                                                      phase_adjust_ps_per_iter);
        if (old_phase_adjust == (__s64)-1) {
            LOG_ERROR("Failed to set phase adjust (iteration %d)\n", i + 1);
            dpll_pin_get_rsp_free(pin_rsp);
            return -1;
        }

        old_phase_adjust = dpll_pin_set_phase_adjust(dpll_sock,
                                                      "REF0N",
                                                      phase_adjust_ps_per_iter);
        if (old_phase_adjust == (__s64)-1) {
            LOG_ERROR("Failed to set phase adjust (iteration %d)\n", i + 1);
            dpll_pin_get_rsp_free(pin_rsp);
            return -1;
        }
        usleep(50000);  /* 50ms delay between iterations to let hardware settle */
    }

    dpll_pin_get_rsp_free(pin_rsp);
    return 0;
}

/**
 * perform_clock_phase_adjust - Apply phase offset adjustment using clock_adjtime
 * @state: Application state
 * @master_offset_ns: Master offset in nanoseconds to correct
 *
 * Applies a direct phase offset adjustment to the PHC using ADJ_SETOFFSET.
 * This shifts the clock by the specified nanoseconds.
 *
 * Returns: 0 on success, -1 on failure
 */
int perform_clock_phase_adjust(AppState *state, int64_t master_offset_ns)
{
    char phc_device[64];
    enum dpll_lock_status lock_status = DPLL_LOCK_STATUS_UNLOCKED;
    enum dpll_mode mode = (enum dpll_mode)0;
    __u32 connected_pin_id = 0;
    enum pin_source connected_pin_src = PIN_SOURCE_UNKNOWN;
    __u32 ptp_pin_id = state ? state->ptp_pin_id : 0;
    enum dpll_pin_state ptp_pin_state = state ? state->ptp_pin_state : DPLL_PIN_STATE_DISCONNECTED;

    if (!state || !state->dpll_sock) {
        LOG_ERROR("DPLL socket not available for clock phase adjustment\n");
        return -1;
    }

    if (dpll_get_device_state_and_connected_pin(state->dpll_sock,
                                                 state->pps_dpll_device_id,
                                                 &lock_status,
                                                 &mode,
                                                 &connected_pin_id,
                                                 &connected_pin_src,
                                                 &ptp_pin_id,
                                                 &ptp_pin_state) != 0) {
        LOG_ERROR("Failed to query DPLL state before clock phase adjustment\n");
        return -1;
    }

    state->lock_status = lock_status;
    state->connected_pin_id = connected_pin_id;
    state->ptp_pin_id = ptp_pin_id;
    state->ptp_pin_state = ptp_pin_state;

    if (!is_ptp_pin(connected_pin_src)) {
        LOG_INFO("Skipping clock phase adjustment: connected source is not PTP (source=%d, pin_id=%u)\n",
                 connected_pin_src, connected_pin_id);
        return 0;
    }

    /* Discover PHC device dynamically */
    if (phc_get_device_from_interface(g_config.manager.phc_interface, phc_device, sizeof(phc_device)) != 0) {
        LOG_ERROR("Failed to discover PHC device for interface %s\n", g_config.manager.phc_interface);
        return -1;
    }

    /* Get TIME_STATUS_NP to update master_offset */
    int req_ret = send_get_request(state->local_socket_fd, &state->local_peer_addr,
                    MGMT_ID_TIME_STATUS_NP, &state->local_sequence_id);
    if (req_ret != 0) {
        LOG_ERROR("Failed to send TIME_STATUS_NP GET request (ret=%d)\n", req_ret);
        return -1;
    }
    usleep(100000);  /* 100ms delay */
    process_ptp_messages(state);

    /* Skip if master_offset is zero (either not received or perfectly synced) */
    if (state->master_offset == 0) {
        LOG_INFO("Skipping phase adjustment: master_offset is zero\n");
        return 0;
    }
    master_offset_ns = state->master_offset;

    LOG_INFO("Using PHC device: %s\n", phc_device);

    int fd = open(phc_device, O_RDWR);
    if (fd < 0) {
        LOG_ERROR("Failed to open %s: %s\n", phc_device, strerror(errno));
        return -1;
    }

    clockid_t clkid = FD_TO_CLOCKID(fd);

    struct timex tx;
    memset(&tx, 0, sizeof(tx));

    /* Get absolute value of master_offset */
    int64_t step = (master_offset_ns < 0) ? -master_offset_ns : master_offset_ns;
    int sign;

    if (master_offset_ns < 0)
        sign = 1;   /* Slave behind, add time */
    else
        sign = -1;  /* Slave ahead, subtract time */

    tx.modes = ADJ_SETOFFSET | ADJ_NANO;
    tx.time.tv_sec = sign * (step / 1000000000LL);
    tx.time.tv_usec = sign * (step % 1000000000LL);

    /* The value of a timeval is the sum of its fields, but the
     * field tv_usec must always be non-negative. */
    if (tx.time.tv_usec < 0) {
        tx.time.tv_sec -= 1;
        tx.time.tv_usec += 1000000000;
    }

    int rc = clock_adjtime(clkid, &tx);
    if (rc < 0) {
        LOG_ERROR("clock_adjtime phase adjust failed: %s\n", strerror(errno));
        close(fd);
        return -1;
    }

    close(fd);

    LOG_INFO("clockAdjust: offset %9lld adjusted %+9lld (tv_sec=%ld tv_usec=%ld) \n",
             (long long)master_offset_ns, (long long)-master_offset_ns,
             (long)tx.time.tv_sec, (long)tx.time.tv_usec);

    sleep(3);

    if (wait_for_dpll_device_lock(state,
                                  DPLL_LOCK_WAIT_TIMEOUT_MS,
                                  DPLL_LOCK_WAIT_POLL_MS,
                                  "after clock_adjtime") != 0) {
        LOG_ERROR("WARNING: DPLL failed to relock after step adjust; exiting application\n");
        return -1;
    }

    return 0;
}

/**
 * monitor_and_adjust_phase_offset - Monitor and adjust phase offset
 * @state: Application state
 *
 * This function:
 * 1. Queries TIME_STATUS_NP to get master_offset
 * 2. For large offsets (>100µs): performs direct clock adjustment
 * 3. For small offsets (<100µs): performs gradual DPLL phase adjustment
 *
 * Called periodically from main loop.
 */
void monitor_and_adjust_phase_offset(AppState *state)
{
    struct ynl_sock *dpll_sock = state->dpll_sock;

    /* Check if DPLL socket is available */
    if (!dpll_sock) {
        LOG_DEBUG("DPLL socket not initialized, skipping phase offset monitoring\n");
        return;
    }

    /* Get TIME_STATUS_NP to update master_offset */
    int req_ret = send_get_request(state->local_socket_fd, &state->local_peer_addr,
                    MGMT_ID_TIME_STATUS_NP, &state->local_sequence_id);
    if (req_ret != 0) {
        LOG_ERROR("Failed to send TIME_STATUS_NP GET request (ret=%d)\n", req_ret);
        return;
    }
    process_ptp_messages(state);

    /* Skip if master_offset is zero (either not received or perfectly synced) */
    if (state->master_offset == 0) {
        LOG_DEBUG("Skipping phase adjustment: master_offset is zero\n");
        return;
    }

    /* Small offset: perform gradual phase adjustment via DPLL */
    LOG_DEBUG("Small offset (%" PRId64 " ns), using DPLL phase adjustment\n",
              state->master_offset);
    if (perform_phase_adjustment(state, dpll_sock, state->master_offset, state->apts_offset) == 0) {
        /* Update apts_offset after successful phase adjustment */
        state->apts_offset = state->master_offset;
    }
}
