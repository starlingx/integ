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
 * @file gearshift.c
 * @brief Gearshift control for SW_BASED operation mode
 */

#define MODULE "GS"
#include <string.h>
#include <errno.h>
#include <poll.h>
#include <time.h>
#include <sys/socket.h>
#include <sys/un.h>
#include "../hdr/gearshift.h"
#include "../hdr/ptp_protocol.h"
#include "../hdr/log.h"

/* Timeout in milliseconds to wait for a GET response after a SET */
#define GEARSHIFT_VERIFY_TIMEOUT_MS 1100

/**
 * read_gearshift_response - Read and verify the RESPONSE to a SET/GET already sent.
 * ptp4l and ts2phc both echo the new gear value back in a RESPONSE message.
 * We read that single RESPONSE here rather than issuing a separate GET,
 * which would leave a second RESPONSE in the socket buffer for the main loop
 * to trip over as an "unhandled management ID: 0xC0F0".
 */
static bool read_gearshift_response(int sockfd, const struct sockaddr_un *peer_addr,
                                    uint8_t expected_gear)
{
    struct timespec deadline;
    clock_gettime(CLOCK_MONOTONIC, &deadline);
    deadline.tv_nsec += GEARSHIFT_VERIFY_TIMEOUT_MS * 1000000LL;
    if (deadline.tv_nsec >= 1000000000LL) {
        deadline.tv_sec++;
        deadline.tv_nsec -= 1000000000LL;
    }

    for (;;) {
        /* Recalculate remaining timeout each iteration */
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        int remaining_ms = (int)((deadline.tv_sec - now.tv_sec) * 1000
                           + (deadline.tv_nsec - now.tv_nsec) / 1000000);
        if (remaining_ms <= 0) {
            LOG_ERROR("gearshift: no response from %s (timeout)\n",
                      peer_addr->sun_path);
            return false;
        }

        struct pollfd pfd = { .fd = sockfd, .events = POLLIN };
        int ready = poll(&pfd, 1, remaining_ms);
        if (ready < 0) {
            LOG_ERROR("gearshift: no response from %s (%s)\n",
                      peer_addr->sun_path, strerror(errno));
            return false;
        }
        if (ready == 0) {
            LOG_ERROR("gearshift: no response from %s (timeout)\n",
                      peer_addr->sun_path);
            return false;
        }

        uint8_t buf[512];
        ssize_t n = recvfrom(sockfd, buf, sizeof(buf), 0, NULL, NULL);
        if (n < 0) {
            LOG_ERROR("gearshift: recvfrom failed: %s\n", strerror(errno));
            return false;
        }

        uint16_t mgmt_id;
        const uint8_t *data;
        size_t data_len;
        if (!parse_management_response(buf, (size_t)n, &mgmt_id, &data, &data_len)) {
            LOG_ERROR("gearshift: failed to parse response from %s\n",
                      peer_addr->sun_path);
            return false;
        }

        if (mgmt_id != MGMT_ID_GEARSHIFT_NP) {
            /* Async notification (e.g. TIME_STATUS_NP 0xC000) delivered to this
             * socket because apts_mgr is subscribed for events on the same UDS.
             * Discard it and keep waiting for the actual gearshift response. */
            LOG_DEBUG("gearshift: skipping async notification 0x%04X from %s\n",
                      mgmt_id, peer_addr->sun_path);
            continue;
        }

        if (data_len < 1) {
            LOG_ERROR("gearshift: response data too short from %s\n",
                      peer_addr->sun_path);
            return false;
        }

        uint8_t actual_gear = data[0];
        const char *gear_str = (actual_gear == GEAR_NEUTRAL) ? "NEUTRAL" :
                               (actual_gear == GEAR_DRIVE)   ? "DRIVE"   : "PARK";
        const char *exp_str  = (expected_gear == GEAR_NEUTRAL) ? "NEUTRAL" :
                               (expected_gear == GEAR_DRIVE)   ? "DRIVE"   : "PARK";

        if (actual_gear != expected_gear) {
            LOG_ERROR("gearshift: %s gear mismatch — expected %s, got %s\n",
                      peer_addr->sun_path, exp_str, gear_str);
            return false;
        }

        LOG_INFO("gearshift: %s gear confirmed %s\n", peer_addr->sun_path, gear_str);
        return true;
    }
}

/**
 * get_gearshift - Send MGMT_ID_GEAR_STATUS_NP GET and return current gear value.
 * @sockfd: Already-bound UDS socket file descriptor
 * @peer_addr: Peer address of the target daemon
 * @current_gear: Output — populated with the gear value reported by the daemon
 *
 * Uses MGMT_ID_GEAR_STATUS_NP (0xC0F1) which returns a gear_status_np struct
 * containing gear, source, and flags — richer than the raw GEARSHIFT_NP GET.
 *
 * Returns: true on success (current_gear is valid), false on failure.
 */
static bool get_gearshift(int sockfd, const struct sockaddr_un *peer_addr,
                          uint8_t *current_gear)
{
    if (sockfd < 0 || !peer_addr || !current_gear)
        return false;

    uint8_t msg[512];
    int len = build_management_message(msg, sizeof(msg), 0,
                                       MGMT_ID_GEAR_STATUS_NP, GET,
                                       NULL, 0);
    if (len < 0) {
        LOG_ERROR("get_gearshift: failed to build GET message\n");
        return false;
    }

    ssize_t sent = sendto(sockfd, msg, len, 0,
                          (const struct sockaddr *)peer_addr, sizeof(*peer_addr));
    if (sent < 0) {
        LOG_ERROR("get_gearshift: sendto() failed: %s\n", strerror(errno));
        return false;
    }

    struct timespec deadline;
    clock_gettime(CLOCK_MONOTONIC, &deadline);
    deadline.tv_nsec += GEARSHIFT_VERIFY_TIMEOUT_MS * 1000000LL;
    if (deadline.tv_nsec >= 1000000000LL) {
        deadline.tv_sec++;
        deadline.tv_nsec -= 1000000000LL;
    }

    for (;;) {
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        int remaining_ms = (int)((deadline.tv_sec - now.tv_sec) * 1000
                           + (deadline.tv_nsec - now.tv_nsec) / 1000000);
        if (remaining_ms <= 0) {
            LOG_ERROR("get_gearshift: no response from %s (timeout)\n",
                      peer_addr->sun_path);
            return false;
        }

        struct pollfd pfd = { .fd = sockfd, .events = POLLIN };
        int ready = poll(&pfd, 1, remaining_ms);
        if (ready < 0) {
            LOG_ERROR("get_gearshift: no response from %s (%s)\n",
                      peer_addr->sun_path, strerror(errno));
            return false;
        }
        if (ready == 0) {
            LOG_ERROR("get_gearshift: no response from %s (timeout)\n",
                      peer_addr->sun_path);
            return false;
        }

        uint8_t buf[512];
        ssize_t n = recvfrom(sockfd, buf, sizeof(buf), 0, NULL, NULL);
        if (n < 0) {
            LOG_ERROR("get_gearshift: recvfrom failed: %s\n", strerror(errno));
            return false;
        }

        uint16_t mgmt_id;
        const uint8_t *data;
        size_t data_len;
        if (!parse_management_response(buf, (size_t)n, &mgmt_id, &data, &data_len)) {
            LOG_ERROR("get_gearshift: failed to parse response from %s\n",
                      peer_addr->sun_path);
            return false;
        }

        if (mgmt_id != MGMT_ID_GEAR_STATUS_NP) {
            /* Async notification on the shared UDS socket — discard and retry */
            LOG_DEBUG("get_gearshift: skipping async notification 0x%04X from %s\n",
                      mgmt_id, peer_addr->sun_path);
            continue;
        }

        if (data_len < sizeof(struct gear_status_np)) {
            LOG_ERROR("get_gearshift: short data from %s (got %zu, need %zu)\n",
                      peer_addr->sun_path, data_len, sizeof(struct gear_status_np));
            return false;
        }

        const struct gear_status_np *gs = (const struct gear_status_np *)data;
        *current_gear = gs->gear;
        LOG_DEBUG("get_gearshift: %s gear=%u source=%s flags=0x%04X\n",
                  peer_addr->sun_path, gs->gear,
                  gs->source < 4 ? gear_source_str[gs->source] : "unknown",
                  gs->flags);
        return true;
    }
}

/**
 * send_gearshift - Send MID_GEARSHIFT_NP SET message using an existing bound socket.
 * Performs a GET first; if the daemon is already in the requested gear, the SET
 * is skipped to avoid unnecessary disruption.
 * @sockfd: Already-bound UDS socket file descriptor
 * @peer_addr: Peer address of the target daemon
 * @gear: GEAR_PARK, GEAR_NEUTRAL or GEAR_DRIVE
 */
static void send_gearshift(int sockfd, const struct sockaddr_un *peer_addr,
                           uint8_t gear)
{
    if (sockfd < 0 || !peer_addr) {
        LOG_ERROR("send_gearshift: invalid socket or peer_addr\n");
        return;
    }

    /* Query current gear; skip SET if already in the desired state */
    uint8_t current_gear;
    if (get_gearshift(sockfd, peer_addr, &current_gear)) {
        const char *cur_str = (current_gear == GEAR_NEUTRAL) ? "NEUTRAL" :
                              (current_gear == GEAR_DRIVE)   ? "DRIVE"   : "PARK";
        if (current_gear == gear) {
            LOG_INFO("send_gearshift: %s already in %s — skipping SET\n",
                     peer_addr->sun_path, cur_str);
            return;
        }
        LOG_INFO("send_gearshift: %s current gear %s — proceeding with SET\n",
                 peer_addr->sun_path, cur_str);
    } else {
        LOG_ERROR("send_gearshift: GET failed for %s — proceeding with SET anyway\n",
                  peer_addr->sun_path);
    }

    /* Payload: management_tlv_datum { uint8_t val; uint8_t reserved; } */
    uint8_t datum[2] = { gear, 0 };

    uint8_t msg[512];
    int len = build_management_message(msg, sizeof(msg), 0,
                                       MGMT_ID_GEARSHIFT_NP, SET,
                                       datum, sizeof(datum));
    if (len < 0) {
        LOG_ERROR("send_gearshift: failed to build management message\n");
        return;
    }

    const char *gear_str = (gear == GEAR_NEUTRAL) ? "NEUTRAL" :
                           (gear == GEAR_DRIVE)   ? "DRIVE"   : "PARK";
    LOG_INFO("Sending GEARSHIFT %s to %s\n", gear_str, peer_addr->sun_path);

    ssize_t sent = sendto(sockfd, msg, len, 0,
                          (const struct sockaddr *)peer_addr, sizeof(*peer_addr));
    if (sent < 0) {
        LOG_ERROR("send_gearshift: sendto() failed: %s\n", strerror(errno));
        return;
    }

    /* Read back the RESPONSE that the daemon echoes for the SET.
     * This both confirms the gear was applied and drains the socket,
     * preventing the main loop from seeing a stray 0xC0F0 message. */
    read_gearshift_response(sockfd, peer_addr, gear);
}

void handle_sw_based_failover(AppState *state, enum pin_source new_master)
{
    if (state->ts2phc_socket_fd < 0) {
        LOG_ERROR("handle_sw_based_failover: ts2phc socket not available (ts2_0 not configured)\n");
        return;
    }

    struct timespec t_start, t_end;
    clock_gettime(CLOCK_MONOTONIC, &t_start);

    if (new_master == GNSS_REF4P || new_master == GNSS_REF4N) {
        LOG_INFO("SW_BASED failover to GNSS: ptp4l -> %s, ts2phc -> DRIVE\n", GEAR_IDLE_STR);
        send_gearshift(state->local_socket_fd,  &state->local_peer_addr,  GEAR_IDLE);
        state->gear_ptp_bh = GEAR_IDLE;
        send_gearshift(state->ts2phc_socket_fd, &state->ts2phc_peer_addr, GEAR_DRIVE);
        state->gear_ts2_0 = GEAR_DRIVE;
    } else if (new_master == SDP2_REF0P || new_master == SDP0_REF0N) {
        LOG_INFO("SW_BASED failover to PTP: ts2phc -> %s, ptp4l -> DRIVE\n", GEAR_IDLE_STR);
        send_gearshift(state->ts2phc_socket_fd, &state->ts2phc_peer_addr, GEAR_IDLE);
        state->gear_ts2_0 = GEAR_IDLE;
        send_gearshift(state->local_socket_fd,  &state->local_peer_addr,  GEAR_DRIVE);
        state->gear_ptp_bh = GEAR_DRIVE;
    } else if (new_master >= HOLDOVER_0 && new_master <= HOLDOVER_3) {
        LOG_INFO("SW_BASED failover to HOLDOVER: ts2phc -> DRIVE, ptp4l -> %s\n", GEAR_IDLE_STR);
        send_gearshift(state->local_socket_fd,  &state->local_peer_addr,  GEAR_IDLE);
        state->gear_ptp_bh = GEAR_IDLE;
        send_gearshift(state->ts2phc_socket_fd, &state->ts2phc_peer_addr, GEAR_DRIVE);
        state->gear_ts2_0 = GEAR_DRIVE;
    } else {
        LOG_INFO("SW_BASED failover to unknown source (%d): no gearshift action defined\n",
                 new_master);
        return;
    }

    clock_gettime(CLOCK_MONOTONIC, &t_end);
    int64_t elapsed_ns = ((int64_t)(t_end.tv_sec  - t_start.tv_sec)  * 1000000000LL)
                       +  (int64_t)(t_end.tv_nsec - t_start.tv_nsec);
    LOG_INFO("SW_BASED failover completed in %" PRId64 " ns (%.3f ms)\n",
             elapsed_ns, (double)elapsed_ns / 1e6);
}
