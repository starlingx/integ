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
 * @file ptp_protocol.c
 * @brief PTP Protocol Processing Implementation
 * 
 * This module handles all PTP management protocol operations.
 */

#define _DEFAULT_SOURCE
#define MODULE "PTP"

#include "../hdr/ptp_protocol.h"

/* External YNL socket from dpll.c */
extern struct ynl_sock *ys;

/* DPLL device ID - typically 0 for primary device */
#define DPLL_DEVICE_ID 0

/* Forward declaration for static helper used before its definition */
static void handle_ptp_port_down(AppState *state);

/**
 * Get the expected data size for a management ID (for GET requests)
 * This matches what pmc sends to reserve space for the response
 */
size_t get_mgmt_id_data_size(uint16_t mgmt_id)
{
    switch (mgmt_id) {
        case MGMT_ID_CURRENT_DATA_SET:         return 18;  /* 72 bytes total */
        case MGMT_ID_PARENT_DATA_SET:          return 32;  /* 86 bytes total */
        case MGMT_ID_PORT_DATA_SET:            return 26;  /* 80 bytes total */
        case MGMT_ID_TIME_STATUS_NP:           return 50;  /* 104 bytes total */
        case MGMT_ID_GRANDMASTER_SETTINGS_NP:  return 8;   /* 62 bytes total (from earlier test) */
        case MGMT_ID_SUBSCRIBE_EVENTS_NP:      return 18;  /* For subscription */
        case MGMT_ID_GEARSHIFT_NP:             return 2;   /* management_tlv_datum: val + reserved */
        case MGMT_ID_GEAR_STATUS_NP:           return 4;   /* gear_status_np: gear(1) + source(1) + flags(2) */
        default:                               return 18;  /* Default minimum */
    }
}

/**
 * Build PTP management message
 */
int build_management_message(uint8_t *buffer, size_t buffer_size,
                                     uint16_t sequence_id, uint16_t mgmt_id,
                                     uint8_t action,
                                     const void *data, size_t data_len)
{
    /* Management fields: targetPortIdentity(10) + hops(2) + actionField(1) + reserved(1) = 14 bytes */
    const size_t mgmt_fields_len = 14;
    
    /* Get the expected data size for this management ID (matches pmc behavior) */
    const size_t expected_data_size = get_mgmt_id_data_size(mgmt_id);
    size_t actual_tlv_data = (data_len > expected_data_size) ? data_len : expected_data_size;
    
    /* Check buffer size: PTP header + mgmt fields + TLV + actual_tlv_data */
    if (buffer_size < sizeof(PTPHeader) + mgmt_fields_len + sizeof(ManagementTLV) + actual_tlv_data) {
        return -1;
    }
    
    memset(buffer, 0, buffer_size);
    
    /* Build PTP header */
    PTPHeader *hdr = (PTPHeader *)buffer;
    /* First byte: transportSpecific (4 bits) | messageType (4 bits) */
    hdr->messageType_versionPTP = (0x0 << 4) | (PTP_MANAGEMENT & 0x0F);
    /* Second byte: minorVersionPTP (4 bits) | versionPTP (4 bits) - for PTP v2.1 this is 0x12 */
    hdr->versionPTP_messageType = (0x01 << 4) | PTP_VERSION;
    /* Management message total length includes the actual_tlv_data (min 8 bytes) */
    hdr->messageLength = htons(sizeof(PTPHeader) + mgmt_fields_len + sizeof(ManagementTLV) + actual_tlv_data);
    hdr->domainNumber = (uint8_t)g_config.manager.ptp_domain_number;
    /* Set sourcePortIdentity: use process ID for uniqueness (8 bytes clockId + 2 bytes portNum) */
    uint32_t pid = (uint32_t)getpid();
    hdr->sourcePortIdentity.id[0] = 0xFF;  /* Local administration */
    hdr->sourcePortIdentity.id[1] = 0xFE;
    hdr->sourcePortIdentity.id[2] = (pid >> 24) & 0xFF;
    hdr->sourcePortIdentity.id[3] = (pid >> 16) & 0xFF;
    hdr->sourcePortIdentity.id[4] = (pid >> 8) & 0xFF;
    hdr->sourcePortIdentity.id[5] = pid & 0xFF;
    hdr->sourcePortIdentity.id[6] = (sequence_id >> 8) & 0xFF;
    hdr->sourcePortIdentity.id[7] = sequence_id & 0xFF;
    hdr->sourcePortNumber = 0;  /* Port number */
    hdr->sequenceId = htons(sequence_id);
    hdr->controlField = 0;  /* Management messages use 0 in PTP v2 */
    hdr->logMessageInterval = 0x7F;
    
    /* Build management message fields after PTP header */
    uint8_t *mgmt_ptr = buffer + sizeof(PTPHeader);
    
    /* targetPortIdentity (10 bytes): clockIdentity(8) + portNumber(2) */
    memset(mgmt_ptr, 0xFF, 8);  /* All 1's for "all clocks" */
    mgmt_ptr += 8;
    *((uint16_t*)mgmt_ptr) = htons(0xFFFF);  /* All 1's for "all ports" */
    mgmt_ptr += 2;
    
    /* startingBoundaryHops (1 byte) */
    *mgmt_ptr++ = 0;
    
    /* boundaryHops (1 byte) */
    *mgmt_ptr++ = 0;
    
    /* actionField (1 byte) - action type (GET, SET, COMMAND, etc.) */
    *mgmt_ptr++ = action & 0x0F;  /* action in lower nibble */
    
    /* Reserved (1 byte) */
    *mgmt_ptr++ = 0;
    
    /* Build Management TLV (no padding between mgmt fields and TLV!) */
    ManagementTLV *tlv = (ManagementTLV *)mgmt_ptr;
    tlv->tlvType = htons(0x0001);  /* Management TLV type */
    /* TLV lengthField = managementId size + actual data size (min 8 bytes) */
    tlv->lengthField = htons(2 + actual_tlv_data);
    tlv->managementId = htons(mgmt_id);  /* Management ID */
    
    /* TLV data section: copy user data + pad to expected size */
    uint8_t *data_ptr = mgmt_ptr + sizeof(ManagementTLV);
    if (data && data_len > 0) {
        memcpy(data_ptr, data, data_len);
        /* Pad to expected size if needed */
        if (data_len < expected_data_size) {
            memset(data_ptr + data_len, 0, expected_data_size - data_len);
        }
    } else {
        /* No user data: fill with zeros up to expected size (pmc behavior) */
        memset(data_ptr, 0, expected_data_size);
    }
    
    return sizeof(PTPHeader) + mgmt_fields_len + sizeof(ManagementTLV) + actual_tlv_data;
}



/**
 * Build SUBSCRIBE_EVENTS_NP management message
 * This is a specialized builder that correctly formats the subscription bitmask
 */
int build_subscription_message(uint8_t *buffer, size_t buffer_size,
                                       uint16_t sequence_id, uint16_t duration,
                                       uint8_t event_bitmask)
{
    /* Management fields: targetPortIdentity(10) + hops(2) + actionField(1) + reserved(1) = 14 bytes */
    const size_t mgmt_fields_len = 14;
    
    /* SUBSCRIBE_EVENTS_NP data: duration (2 bytes) + bitmask (64 bytes) = 66 bytes */
    const size_t subscription_data_len = 66;
    
    /* Check buffer size: PTP header + mgmt fields + TLV + subscription data */
    if (buffer_size < sizeof(PTPHeader) + mgmt_fields_len + sizeof(ManagementTLV) + subscription_data_len) {
        return -1;
    }
    
    memset(buffer, 0, buffer_size);
    
    /* Build PTP header */
    PTPHeader *hdr = (PTPHeader *)buffer;
    hdr->messageType_versionPTP = (0x0 << 4) | (PTP_MANAGEMENT & 0x0F);
    hdr->versionPTP_messageType = (0x01 << 4) | PTP_VERSION;
    hdr->messageLength = htons(sizeof(PTPHeader) + mgmt_fields_len + sizeof(ManagementTLV) + subscription_data_len);
    hdr->domainNumber = (uint8_t)g_config.manager.ptp_domain_number;
    
    /* Set sourcePortIdentity */
    uint32_t pid = (uint32_t)getpid();
    hdr->sourcePortIdentity.id[0] = 0xFF;
    hdr->sourcePortIdentity.id[1] = 0xFE;
    hdr->sourcePortIdentity.id[2] = (pid >> 24) & 0xFF;
    hdr->sourcePortIdentity.id[3] = (pid >> 16) & 0xFF;
    hdr->sourcePortIdentity.id[4] = (pid >> 8) & 0xFF;
    hdr->sourcePortIdentity.id[5] = pid & 0xFF;
    hdr->sourcePortIdentity.id[6] = (sequence_id >> 8) & 0xFF;
    hdr->sourcePortIdentity.id[7] = sequence_id & 0xFF;
    hdr->sourcePortNumber = 0;
    hdr->sequenceId = htons(sequence_id);
    hdr->controlField = 0;
    hdr->logMessageInterval = 0x7F;
    
    /* Build management message fields */
    uint8_t *mgmt_ptr = buffer + sizeof(PTPHeader);
    
    /* targetPortIdentity: all 0xFF for broadcast */
    memset(mgmt_ptr, 0xFF, 8);
    mgmt_ptr += 8;
    *((uint16_t*)mgmt_ptr) = htons(0xFFFF);
    mgmt_ptr += 2;
    
    /* Hops */
    *mgmt_ptr++ = 0;
    *mgmt_ptr++ = 0;
    
    /* actionField: SET (1) for SUBSCRIBE_EVENTS_NP */
    *mgmt_ptr++ = SET;
    
    /* reserved */
    *mgmt_ptr++ = 0;
    
    /* Build Management TLV */
    ManagementTLV *tlv = (ManagementTLV *)mgmt_ptr;
    tlv->tlvType = htons(0x0001);
    tlv->lengthField = htons(2 + subscription_data_len);  /* managementId + data */
    tlv->managementId = htons(MGMT_ID_SUBSCRIBE_EVENTS_NP);
    
    /* Build subscription data: duration (2 bytes) + bitmask (64 bytes) */
    uint8_t *data_ptr = mgmt_ptr + sizeof(ManagementTLV);
    
    /* Duration (big-endian) */
    *((uint16_t*)data_ptr) = htons(duration);
    data_ptr += 2;
    
    /* Event bitmask: 64 bytes, all zeros except first byte */
    memset(data_ptr, 0, 64);
    data_ptr[0] = event_bitmask;  /* Set the event bits in first byte */
    
    return sizeof(PTPHeader) + mgmt_fields_len + sizeof(ManagementTLV) + subscription_data_len;
}


/**
 * Send subscription request
 */
bool send_subscription_request(int sock_fd, struct sockaddr_un *peer_addr, uint16_t *sequence_id)
{
    uint8_t buffer[BUFFER_SIZE];
    
    /* Build event bitmask: PORT_STATE is always subscribed.
     * TIME_STATUS_NP and PARENT_DATA_SET are only needed when:
     *   - operation_mode is HW_BASED (runtime), AND
     *   - STATIC_PARAMS_FROM_CONFIG is not defined (compile-time).
     * When params come from the config file there is no need to pull
     * clock quality / UTC offset / GM identity from ptp4l notifications. */
    uint8_t event_bitmask = 0;
    event_bitmask |= (1 << NOTIFY_PORT_STATE);       /* Bit 0: Port state changes (always) */
#ifndef STATIC_PARAMS_FROM_CONFIG
    if (g_config.manager.operation_mode == OPERATION_MODE_HW_BASED) {
        event_bitmask |= (1 << NOTIFY_TIME_SYNC);    /* Bit 1: Time synchronization */
        event_bitmask |= (1 << NOTIFY_PARENT_DATA_SET); /* Bit 2: GM/parent changes */
    }
#endif
    
    /* Build subscription message using specialized function */
    int msg_len = build_subscription_message(buffer, sizeof(buffer), *sequence_id,
                                             SUBSCRIPTION_DURATION, event_bitmask);
    if (msg_len < 0) {
        LOG_ERROR("Failed to build subscription message\n");
        return false;
    }
    
    ssize_t sent = sendto(sock_fd, buffer, msg_len, 0, (struct sockaddr *)peer_addr, sizeof(*peer_addr));
    if (sent < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            LOG_DEBUG("sendto would block, skipping subscription request\n");
            return false;
        }
        LOG_ERROR("Failed to send subscription message: %s\n", strerror(errno));
        return false;
    }
    
    if (sent != msg_len) {
        LOG_ERROR("Partial send: sent %zd of %d bytes\n", sent, msg_len);
        return false;
    }
    
#ifdef HEX_DUMP
    /* Debug: print first 64 bytes as hex */
    LOG_DEBUG("Sent %zd bytes SUBSCRIBE_EVENTS_NP:\n", sent);
    LOG_RAW("HEX: ");
    for (int i = 0; i < (msg_len < 64 ? msg_len : 64); i++) {
        LOG_RAW("%02X ", buffer[i]);
        if ((i + 1) % 16 == 0) LOG_RAW("\n     ");
    }
    LOG_RAW("\n");
#endif
    
    (*sequence_id)++;
    LOG_INFO("Subscription request sent (duration: %d sec)\n", SUBSCRIPTION_DURATION);
    return true;
}


/**
 * Send GET request for clock data
 */
int send_get_request(int sockfd, struct sockaddr_un *peer_addr, uint16_t mgmt_id, uint16_t *seq)
{
    uint8_t msg[512];
    int len = build_management_message(msg, sizeof(msg), *seq, mgmt_id, GET, NULL, 0);
    if (len < 0) {
        LOG_ERROR("Failed to build management message\n");
        return EINVAL;
    }
    
    LOG_DEBUG("Sending GET request for mgmt_id=0x%04X to %s, len=%d\n", mgmt_id, peer_addr->sun_path, len);
    
    ssize_t sent = sendto(sockfd, msg, len, 0, (struct sockaddr *)peer_addr, sizeof(*peer_addr));
    if (sent < 0) {
        int err = errno;
        if (err == EAGAIN || err == EWOULDBLOCK) {
            LOG_DEBUG("sendto() would block\n");
            return err;
        }
        LOG_ERROR("sendto() failed for GET request: %s\n", strerror(err));
        return err;
    }
    
    LOG_DEBUG("Sent %zd bytes successfully\n", sent);
    (*seq)++;
    return 0;
}

/**
 * Parse received management message
 */
bool parse_management_response(const uint8_t *buffer, size_t len,
                                      uint16_t *mgmt_id, const uint8_t **data,
                                      size_t *data_len)
{
    /* Management message structure: PTPHeader(34) + management fields(22) + TLV */
    const size_t mgmt_fields_len = 14;  /* targetPortIdentity(10) + hops(2) + actionField(1) + reserved(1) + padding(8) */
    
    if (len < sizeof(PTPHeader) + mgmt_fields_len + sizeof(ManagementTLV)) {
        LOG_DEBUG("Message too short: %zu < %zu\n", len, sizeof(PTPHeader) + mgmt_fields_len + sizeof(ManagementTLV));
        return false;
    }
    
    const PTPHeader *hdr = (const PTPHeader *)buffer;
    const ManagementTLV *tlv = (const ManagementTLV *)(buffer + sizeof(PTPHeader) + mgmt_fields_len);
    
    /* Verify it's a management message - messageType is in LOW nibble of first byte */
    uint8_t msg_type = hdr->messageType_versionPTP & 0x0F;
    LOG_DEBUG("Message type byte: 0x%02X, extracted msg_type: 0x%X, expected: 0x%X\n", 
           hdr->messageType_versionPTP, msg_type, PTP_MANAGEMENT);
    
    if (msg_type != PTP_MANAGEMENT) {
        LOG_DEBUG("Not a management message: type=0x%X\n", msg_type);
        return false;
    }
    
    *mgmt_id = ntohs(tlv->managementId);
    *data = buffer + sizeof(PTPHeader) + mgmt_fields_len + sizeof(ManagementTLV);
    *data_len = ntohs(tlv->lengthField) - 2;  /* Subtract managementId size */
    
    LOG_DEBUG("Successfully parsed: mgmt_id=0x%04X, data_len=%zu\n", *mgmt_id, *data_len);
    return true;
}



/**
 * Process TIME_STATUS_NP response
 */
void process_time_status_np(AppState *state, const uint8_t *data, size_t data_len)
{
    LOG_DEBUG("Processing TIME_STATUS_NP response (data_len=%zu)\n", data_len);
    
    if (!state) {
        LOG_ERROR("Invalid state pointer in process_time_status_np\n");
        return;
    }

    if (data_len < 50) {
        LOG_ERROR("TIME_STATUS_NP data too short (%zu bytes, expected >= 50)\n", data_len);
        return;
    }
    
    /* Parse TIME_STATUS_NP TLV (50 bytes) */
    const uint8_t *ptr = data;
    
    /* master_offset (8 bytes) */
    int64_t master_offset = (int64_t)be64toh(*(uint64_t*)ptr);
    ptr += 8;
    
    /* ingress_time (8 bytes) - skip */
    ptr += 8;
    
    /* currentUtcOffset (2 bytes) */
    int16_t current_utc_offset = (int16_t)ntohs(*(uint16_t*)ptr);
    ptr += 2;
    
    /* cumulativeScaledRateOffset (4 bytes) - skip */
    ptr += 4;
    
    /* scaledLastGmPhaseChange (2 bytes) - skip */
    ptr += 2;
    
    /* gmTimeBaseIndicator (2 bytes) - skip */
    ptr += 2;
    
    /* lastGmPhaseChange (10 bytes) - contains time properties */
    /* currentUtcOffset (2 bytes) - duplicate, skip */
    ptr += 2;
    
    /* Time properties flags */
    uint8_t leap59 = *ptr++;
    uint8_t leap61 = *ptr++;
    uint8_t current_utc_offset_valid = *ptr++;
    uint8_t ptp_timescale = *ptr++;
    uint8_t time_traceable = *ptr++;
    uint8_t frequency_traceable = *ptr++;
    uint8_t time_source = *ptr++;
    
    /* gmPresent (4 bytes) at byte offset 38 in TIME_STATUS_NP:
     * 1 = external GM is being tracked (grandmasterIdentity != clockIdentity)
     * 0 = no external GM (free-running or LISTENING) */
    bool gm_present = ((int32_t)ntohl(*(const uint32_t *)(data + 38))) != 0;
    LOG_DEBUG("gmPresent=%d\n", gm_present);

    /* Use active PTP source index (REF0P or REF0N) */
    enum pin_source ptp_idx =
        (state->current_master == SDP2_REF0P || state->current_master == SDP0_REF0N)
            ? state->current_master
            : SDP2_REF0P;
    
    /* Store master offset in state */
    state->master_offset = master_offset;
    
    /* Update all clock parameters using PTP index */
    state->clock_params[ptp_idx].phase_offset = master_offset;
    if (current_utc_offset_valid) {
        state->clock_params[ptp_idx].current_utc_offset = current_utc_offset;
    } else {
        LOG_DEBUG("TIME_STATUS_NP has invalid UTC offset flag; keeping existing currentUtcOffset=%d\n",
                 state->clock_params[ptp_idx].current_utc_offset);
    }
    state->clock_params[ptp_idx].leap61 = leap61;
    state->clock_params[ptp_idx].leap59 = leap59;
    if (current_utc_offset_valid) {
        state->clock_params[ptp_idx].current_utc_offset_valid = 1;
    }
    state->clock_params[ptp_idx].ptp_timescale = ptp_timescale;
    state->clock_params[ptp_idx].time_traceable = time_traceable;
    state->clock_params[ptp_idx].frequency_traceable = frequency_traceable;
    state->clock_params[ptp_idx].time_source = time_source;
    clock_gettime(CLOCK_MONOTONIC, &state->clock_params[ptp_idx].last_update);
    
    LOG_DEBUG("Phase offset: %" PRId64 " ns, UTC offset: %d, timeSource: 0x%02X, flags: leap61=%d leap59=%d utcValid=%d timescale=%d traceable=%d freqTraceable=%d\n",
            master_offset, current_utc_offset, time_source, leap61, leap59, current_utc_offset_valid,
            ptp_timescale, time_traceable, frequency_traceable);
}



/**
 * Process PARENT_DATA_SET response
 */
void process_parent_data_set(AppState *state, const uint8_t *data, size_t data_len)
{
    LOG_INFO("Processing PARENT_DATA_SET response (data_len=%zu)\n", data_len);
    
    if (!state) {
        LOG_ERROR("Invalid state pointer in process_parent_data_set\n");
        return;
    }

    if (data_len < 32) {
        LOG_ERROR("PARENT_DATA_SET data too short (%zu bytes, expected >= 32)\n", data_len);
        return;
    }
    
    /* Parse PARENT_DATA_SET - linuxptp/IEEE 1588 hybrid structure
     * NOTE: linuxptp puts clockQuality BEFORE grandmasterIdentity, 
     * different from IEEE 1588-2019 which has identity first
     */
    const uint8_t *ptr = data;
    
    /* Skip parentPortIdentity (10 bytes) */
    ptr += 10;
    
    /* parentStats (1 byte) */
    ptr += 1;
    
    /* reserved (1 byte) */
    ptr += 1;
    
    /* observedParentOffsetScaledLogVariance (2 bytes) */
    ptr += 2;
    
    /* observedParentClockPhaseChangeRate (4 bytes) */
    ptr += 4;
    
    /* NOW at offset 18: In linuxptp, clockQuality comes FIRST */
    /* grandmasterPriority1 (1 byte) - linuxptp puts this before identity! */
    
    /* Use active PTP source index (REF0P or REF0N) */
    enum pin_source ptp_idx =
        (state->current_master == SDP2_REF0P || state->current_master == SDP0_REF0N)
            ? state->current_master
            : SDP2_REF0P;
    
    uint8_t gm_priority1 = ptr[0];
    ptr += 1;
    
    /* grandmasterClockQuality (4 bytes) */
    uint8_t gm_clock_class = ptr[0];
    uint8_t gm_clock_accuracy = ptr[1];
    uint16_t gm_offset_scaled_log_variance =
        (uint16_t)(((uint16_t)ptr[2] << 8) | (uint16_t)ptr[3]);
    
    LOG_DEBUG("PARENT_DATA_SET clockQuality bytes: %02X %02X %02X %02X\n", 
              ptr[0], ptr[1], ptr[2], ptr[3]);
    ptr += 4;
    
    /* grandmasterPriority2 (1 byte) */
    uint8_t gm_priority2 = ptr[0];
    ptr += 1;
    
    /* grandmasterIdentity (8 bytes) - comes AFTER priorities and quality in linuxptp */
    ClockIdentity gm_identity;
    memcpy(gm_identity.id, ptr, 8);
    ptr += 8;

    state->clock_params[ptp_idx].gm_priority1 = gm_priority1;
    state->clock_params[ptp_idx].gm_clock_class = gm_clock_class;
    state->clock_params[ptp_idx].gm_clock_accuracy = gm_clock_accuracy;
    state->clock_params[ptp_idx].gm_offset_scaled_log_variance = gm_offset_scaled_log_variance;
    state->clock_params[ptp_idx].gm_priority2 = gm_priority2;
    state->clock_params[ptp_idx].gm_identity = gm_identity;
    
    state->clock_params[ptp_idx].gm_present = true;
    clock_gettime(CLOCK_MONOTONIC, &state->clock_params[ptp_idx].last_update);
    
    LOG_DEBUG("GM Identity: %02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x\n",
           state->clock_params[ptp_idx].gm_identity.id[0],
           state->clock_params[ptp_idx].gm_identity.id[1],
           state->clock_params[ptp_idx].gm_identity.id[2],
           state->clock_params[ptp_idx].gm_identity.id[3],
           state->clock_params[ptp_idx].gm_identity.id[4],
           state->clock_params[ptp_idx].gm_identity.id[5],
           state->clock_params[ptp_idx].gm_identity.id[6],
           state->clock_params[ptp_idx].gm_identity.id[7]);
        LOG_DEBUG("GM Clock Class: %u, Accuracy: 0x%02X, Variance: 0x%04X, Priority1: %u, Priority2: %u, TimeSource: 0x%02X\n",
           state->clock_params[ptp_idx].gm_clock_class,
           state->clock_params[ptp_idx].gm_clock_accuracy,
            state->clock_params[ptp_idx].gm_offset_scaled_log_variance,
           state->clock_params[ptp_idx].gm_priority1,
            state->clock_params[ptp_idx].gm_priority2,
            state->clock_params[ptp_idx].time_source);
    
    /* Check if running in free running mode */
    if (state->clock_params[ptp_idx].gm_clock_class >= 187) {
        const char *mode = "";
        switch (state->clock_params[ptp_idx].gm_clock_class) {
            case 187: mode = "free running, locked"; break;
            case 193: mode = "free running, not locked"; break;
            case 248: mode = "free running (default)"; break;
            case 255: mode = "slave-only"; break;
            default: mode = "degraded/free running"; break;
        }
        LOG_INFO("GM is in free running mode: Clock Class %u (%s)\n",
               state->clock_params[ptp_idx].gm_clock_class, mode);
    }
}

/**
 * Convert TIME_STATUS_NP and PARENT_DATA_SET parameters to GRANDMASTER_SETTINGS_NP format
 * 
 * GRANDMASTER_SETTINGS_NP structure (8 bytes):
 *   - clockClass (1 byte)
 *   - clockAccuracy (1 byte)
 *   - offsetScaledLogVariance (2 bytes)
 *   - currentUtcOffset (2 bytes)
 *   - flags (1 byte): leap61|leap59|utcValid|timescale|timeTraceable|freqTraceable
 *   - timeSource (1 byte)
 */
void convert_to_grandmaster_settings_np(const ClockParameters *clock_params,
                                               uint8_t *gm_settings_data,
                                               size_t *data_len)
{
    uint8_t *ptr = gm_settings_data;
    
    /* Debug: Log what we're converting */
    LOG_DEBUG("Converting to GRANDMASTER_SETTINGS_NP: clockClass=%u, clockAccuracy=%u, variance=%u, utcOffset=%d, utcValid=%u\n",
              clock_params->gm_clock_class, clock_params->gm_clock_accuracy, 
              clock_params->gm_offset_scaled_log_variance,
              clock_params->current_utc_offset,
              clock_params->current_utc_offset_valid);
    
    /* clockClass (1 byte) - from PARENT_DATA_SET */
    *ptr++ = clock_params->gm_clock_class;
    
    /* clockAccuracy (1 byte) - from PARENT_DATA_SET */
    *ptr++ = clock_params->gm_clock_accuracy;
    
    /* offsetScaledLogVariance (2 bytes, network byte order) - from PARENT_DATA_SET */
    *(uint16_t*)ptr = htons(clock_params->gm_offset_scaled_log_variance);
    ptr += 2;
    
    /* currentUtcOffset (2 bytes, network byte order) - from TIME_STATUS_NP */
    *(int16_t*)ptr = htons(clock_params->current_utc_offset);
    ptr += 2;
    
    /* flags (1 byte) - from TIME_STATUS_NP */
    uint8_t flags = 0;
    flags |= (clock_params->leap61 & 0x01) << 0;
    flags |= (clock_params->leap59 & 0x01) << 1;
    flags |= (clock_params->current_utc_offset_valid & 0x01) << 2;
    flags |= (clock_params->ptp_timescale & 0x01) << 3;
    flags |= (clock_params->time_traceable & 0x01) << 4;
    flags |= (clock_params->frequency_traceable & 0x01) << 5;
    *ptr++ = flags;
    
    /* timeSource (1 byte) - from TIME_STATUS_NP */
    *ptr++ = clock_params->time_source;
    
    *data_len = 8;
}

/**
 * Build GRANDMASTER_SETTINGS_NP SET message
 * 

 * 
 * This creates a properly formatted PTP management message with GRANDMASTER_SETTINGS_NP TLV
 * containing the 8-byte grandmaster settings data.
 */
int build_grandmaster_settings_np_message(uint8_t *buffer, size_t buffer_size,
                                                 uint16_t sequence_id,
                                                 const ClockParameters *clock_params)
{
    if (buffer_size < 128) {
        LOG_ERROR("Buffer too small for GRANDMASTER_SETTINGS_NP message\n");
        return -1;
    }
    
    /* Convert clock parameters to GRANDMASTER_SETTINGS_NP format */
    uint8_t gm_settings_data[8];
    size_t gm_settings_len;
    convert_to_grandmaster_settings_np(clock_params, gm_settings_data, &gm_settings_len);
    
    /* Build the management message with SET action */
    return build_management_message(buffer, buffer_size,
                                   sequence_id,
                                   MGMT_ID_GRANDMASTER_SETTINGS_NP,
                                   SET,
                                   gm_settings_data,
                                   gm_settings_len);
}



/**
 * Forward clock parameters to remote instances using PMC interface
 */
void forward_clock_parameters(AppState *state)
{
    /* Determine which index to use for clock parameters */
    enum pin_source param_idx = state->current_master;
    
    /* Check if we're in holdover state - allow forwarding with stored parameters */
    bool is_holdover = (state->current_master >= HOLDOVER_0 && state->current_master <= HOLDOVER_3);
    
    if (is_holdover) {
        LOG_DEBUG("Forwarding clock parameters from holdover state (pin source %d) to %d valid remote(s)\n", 
                 param_idx, state->rx_count);
    } else {
        LOG_INFO("Forwarding clock parameters from pin source %d to %d valid remote(s)\n", 
                 param_idx, state->rx_count);
    }
    
    for (int i = 0; i < state->rx_count; i++) {
        /* Note: Only valid, active remotes are stored during initialization */
        uint8_t buffer[BUFFER_SIZE];
        
        /* Build GRANDMASTER_SETTINGS_NP SET message using new function */
        LOG_DEBUG("Building GRANDMASTER_SETTINGS_NP SET for remote %d (%s)\n", 
                i, state->remotes[i].uds_path);
        
        int msg_len = build_grandmaster_settings_np_message(buffer, sizeof(buffer),
                                                           state->remotes[i].sequence_id,
                                                           &state->clock_params[param_idx]);
        
        if (msg_len > 0) {
            LOG_DEBUG("     SET message length: %d bytes (data: 8 bytes)\n", msg_len);
            LOG_RAW("     SET message hex:\n     ");
            for (int j = 0; j < msg_len; j++) {
                LOG_RAW("%02X ", buffer[j]);
                if ((j + 1) % 16 == 0 && j + 1 < msg_len) LOG_RAW("\n     ");
            }
            LOG_RAW("\n");
            
            /* Extract and display the GRANDMASTER_SETTINGS_NP data (last 8 bytes) */
            if (msg_len >= 8) {
                const uint8_t *gm_data = buffer + msg_len - 8;
                LOG_RAW("     GM Settings data: ");
                for (int j = 0; j < 8; j++) {
                    LOG_RAW("%02X ", gm_data[j]);
                }
                LOG_RAW("\n");
                LOG_DEBUG("     clockClass=%d, clockAccuracy=0x%02X, variance=0x%04X\n",
                       gm_data[0], gm_data[1], ntohs(*(uint16_t*)(gm_data + 2)));
                LOG_DEBUG("     utcOffset=%d, flags=0x%02X, timeSource=0x%02X\n",
                       (int16_t)ntohs(*(uint16_t*)(gm_data + 4)), gm_data[6], gm_data[7]);
            }
            
            ssize_t sent = sendto(state->remotes[i].socket_fd, buffer, msg_len, 0,
                                  (struct sockaddr *)&state->remotes[i].peer_addr,
                                  sizeof(state->remotes[i].peer_addr));
            if (sent >= 0) {
                state->remotes[i].sequence_id++;
                LOG_DEBUG("     SET sent successfully (%zd bytes)\n", sent);
            } else {
                LOG_ERROR("     SET send failed: %s\n", strerror(errno));
            }
        } else {
            LOG_ERROR("     Failed to build GRANDMASTER_SETTINGS_NP message\n");
        }
    }
}

/**
 * Check if ptp4l is in free running mode by querying GRANDMASTER_SETTINGS_NP
 * - Clock classes >= 187 indicate free-running mode
 * - This works correctly with --free_running flag 
 * - Loops until free running mode is detected or max retries reached
 * - Also waits for port state to reach UNCALIBRATED or SLAVE
 * - Also waits for master_offset > 0
 * Returns: true if free running, false if max retries exceeded
 */
bool check_free_running_mode(int sock_fd, struct sockaddr_un *peer_addr, uint16_t *sequence_id)
{
    uint8_t buffer[BUFFER_SIZE];
    const int MAX_RETRIES = 100;  /* Maximum retry attempts */
    const int RETRY_DELAY_SEC = 1;  /* Delay between retries in seconds */
    int retry_count = 0;
    bool clock_class_ok = false;
    bool port_state_ok = false;
    bool master_offset_ok = false;
    
    LOG_INFO("Waiting for ptp4l to enter free running mode, reach UNCALIBRATED state, and get master_offset...\n");
    
    while (retry_count < MAX_RETRIES) {
        if (retry_count > 0) {
            LOG_INFO("Retry %d/%d - waiting %d seconds before next attempt...\n", 
                     retry_count, MAX_RETRIES, RETRY_DELAY_SEC);
            sleep(RETRY_DELAY_SEC);
        }
        
        /* Send GRANDMASTER_SETTINGS_NP request to get clock class */
        int req_ret = send_get_request(sock_fd, peer_addr, MGMT_ID_GRANDMASTER_SETTINGS_NP, sequence_id);
        if (req_ret != 0) {
            LOG_ERROR("Failed to send GRANDMASTER_SETTINGS_NP GET request (attempt %d/%d, ret=%d)\n",
                     retry_count + 1, MAX_RETRIES, req_ret);
            retry_count++;
            continue;
        }
        usleep(50000);  /* 50ms delay between requests */
        
        /* Send PORT_DATA_SET request to get port state */
        req_ret = send_get_request(sock_fd, peer_addr, MGMT_ID_PORT_DATA_SET, sequence_id);
        if (req_ret != 0) {
            LOG_ERROR("Failed to send PORT_DATA_SET GET request (attempt %d/%d, ret=%d)\n",
                     retry_count + 1, MAX_RETRIES, req_ret);
            retry_count++;
            continue;
        }
        usleep(50000);  /* 50ms delay between requests */
        
        /* Send TIME_STATUS_NP request to get master_offset */
        req_ret = send_get_request(sock_fd, peer_addr, MGMT_ID_TIME_STATUS_NP, sequence_id);
        if (req_ret != 0) {
            LOG_ERROR("Failed to send TIME_STATUS_NP GET request (attempt %d/%d, ret=%d)\n",
                     retry_count + 1, MAX_RETRIES, req_ret);
            retry_count++;
            continue;
        }
        
        /* Wait for responses with timeout */
        fd_set readfds;
        struct timeval tv;
        int responses_received = 0;
        
        /* Try to receive up to 3 responses (GRANDMASTER_SETTINGS_NP, PORT_DATA_SET, TIME_STATUS_NP) */
        while (responses_received < 3) {
            tv.tv_sec = 1;  /* 1 second timeout per response */
            tv.tv_usec = 0;
            
            FD_ZERO(&readfds);
            FD_SET(sock_fd, &readfds);
            
            int ret = select(sock_fd + 1, &readfds, NULL, NULL, &tv);
            if (ret <= 0) {
                if (ret == 0) {
                    LOG_DEBUG("Timeout waiting for response %d/3 (attempt %d/%d)\n", 
                             responses_received + 1, retry_count + 1, MAX_RETRIES);
                } else {
                    LOG_ERROR("Select error: %s\n", strerror(errno));
                }
                break;  /* Move to next retry */
            }
            
            struct sockaddr_un from_addr;
            socklen_t from_len = sizeof(from_addr);
            ssize_t len = recvfrom(sock_fd, buffer, sizeof(buffer), 0, 
                                   (struct sockaddr *)&from_addr, &from_len);
            if (len < 0) {
                LOG_ERROR("Failed to receive response: %s (attempt %d/%d)\n", 
                         strerror(errno), retry_count + 1, MAX_RETRIES);
                break;
            }
            
            LOG_DEBUG("Received %zd bytes from %s\n", len, from_addr.sun_path);
            
            /* Parse response */
            uint16_t mgmt_id;
            const uint8_t *data;
            size_t data_len;
            
            if (!parse_management_response(buffer, len, &mgmt_id, &data, &data_len)) {
                LOG_DEBUG("Failed to parse response (attempt %d/%d)\n", 
                         retry_count + 1, MAX_RETRIES);
                responses_received++;
                continue;
            }
            
            if (mgmt_id == MGMT_ID_GRANDMASTER_SETTINGS_NP) {
                /* Parse GRANDMASTER_SETTINGS_NP structure (8 bytes minimum) */
                if (data_len < 8) {
                    LOG_DEBUG("GRANDMASTER_SETTINGS_NP data too short: %zu bytes\n", data_len);
                    responses_received++;
                    continue;
                }
                
                /* Extract clock class from first byte */
                uint8_t gm_clock_class = data[0];
                uint8_t clock_accuracy = data[1];
                uint8_t time_source = data[7];
                
                LOG_INFO("Attempt %d/%d - GM Clock Class: %u, Accuracy: %u, Time Source: %u\n", 
                         retry_count + 1, MAX_RETRIES, gm_clock_class, clock_accuracy, time_source);
                
                /* Check if clock class indicates free-running mode (255) */
                if (gm_clock_class == 255) {
                    clock_class_ok = true;
                    LOG_INFO("  ✓ Clock Class OK: %u (free running)\n", gm_clock_class);
                } else {
                    clock_class_ok = false;
                    LOG_INFO("  ✗ Clock Class not ready: %u (need 255)\n", gm_clock_class);
                }
                responses_received++;
            }
            else if (mgmt_id == MGMT_ID_PORT_DATA_SET) {
                /* Parse PORT_DATA_SET structure */
                if (data_len < 11) {
                    LOG_DEBUG("PORT_DATA_SET data too short: %zu bytes\n", data_len);
                    responses_received++;
                    continue;
                }
                
                /* Port state is at byte 10 */
                uint8_t port_state = data[10];
                const char *state_str[] = {"UNKNOWN", "INITIALIZING", "FAULTY", "DISABLED",
                                           "LISTENING", "PRE_MASTER", "MASTER", "PASSIVE",
                                           "UNCALIBRATED", "SLAVE"};
                
                LOG_INFO("Attempt %d/%d - Port State: %s (%u)\n", 
                         retry_count + 1, MAX_RETRIES, 
                         (port_state < 10) ? state_str[port_state] : "INVALID", port_state);
                
                /* Check if port state is UNCALIBRATED (8) or SLAVE (9) */
                if (port_state >= 8 && port_state <= 9) {
                    port_state_ok = true;
                    LOG_INFO("  ✓ Port State OK: %s\n", state_str[port_state]);
                } else {
                    port_state_ok = false;
                    LOG_INFO("  ✗ Port State not ready: %s (need UNCALIBRATED or SLAVE)\n", 
                             state_str[port_state]);
                }
                responses_received++;
            }
            else if (mgmt_id == MGMT_ID_TIME_STATUS_NP) {
                /* Parse TIME_STATUS_NP structure (50 bytes minimum) */
                if (data_len < 50) {
                    LOG_DEBUG("TIME_STATUS_NP data too short: %zu bytes\n", data_len);
                    responses_received++;
                    continue;
                }
                
                /* master_offset is first 8 bytes */
                int64_t master_offset = (int64_t)be64toh(*(uint64_t*)data);
                
                LOG_INFO("Attempt %d/%d - Master Offset: %+ld ns\n", 
                         retry_count + 1, MAX_RETRIES, master_offset);
                
                /* Check if master_offset != 0 */
                if (master_offset != 0) {
                    master_offset_ok = true;
                    LOG_INFO("  ✓ Master Offset OK: %+ld ns\n", master_offset);
                } else {
                    master_offset_ok = false;
                    LOG_INFO("  ✗ Master Offset not ready: %+ld ns (need != 0)\n", master_offset);
                }
                responses_received++;
            }
            else {
                LOG_DEBUG("Unexpected mgmt_id=0x%04X (attempt %d/%d)\n", 
                         mgmt_id, retry_count + 1, MAX_RETRIES);
                responses_received++;
            }
        }
        
        /* Check if all three conditions are met */
        if (clock_class_ok && port_state_ok && master_offset_ok) {
            LOG_INFO("✓ SUCCESS: ptp4l is ready (FREE-RUNNING, UNCALIBRATED/SLAVE, master_offset > 0)\n");
            return true;
        }
        
        retry_count++;
    }
    
    /* Max retries exceeded */
    LOG_ERROR("✗ FAILED: ptp4l did not reach required state after %d attempts\n", MAX_RETRIES);
    LOG_ERROR("   Clock Class OK: %s, Port State OK: %s, Master Offset OK: %s\n", 
              clock_class_ok ? "YES" : "NO", port_state_ok ? "YES" : "NO", master_offset_ok ? "YES" : "NO");
    LOG_ERROR("   Please verify ptp4l is running with --free_running flag\n");
    
    return false;
}

#if 0
/**
 * Reprioritize PTP pin to have higher priority than GNSS if needed
 * Ensures REF0P priority is higher (lower value) than REF4P priority
 * @ys: YNL socket for DPLL
 * 
 * Returns: 0 on success, -1 on error
 */
static int reprioritize_ptp_pin(AppState *state)
{
    if (!state->dpll_sock) {
        LOG_ERROR("YNL socket not initialized\n");
        return -1;
    }

    int ref4p_prio = dpll_pin_get_priority(state->dpll_sock, state->pps_dpll_device_id, "REF4P");
    int ref0p_prio = dpll_pin_get_priority(state->dpll_sock, state->pps_dpll_device_id, "REF0P");

    LOG_INFO("REF0P priority=%d, REF4P priority=%d (lower value = higher priority)\n",
             ref0p_prio, ref4p_prio);

    /* No action needed if REF0P already has highest possible priority */
    if (ref0p_prio == DPLL_HIGHEST_PRIORITY) {
        LOG_INFO("REF0P already at highest priority (%d) - no action needed\n",
                 DPLL_HIGHEST_PRIORITY);
        return 0;
    }

    /* No action needed if REF0P priority is already higher than REF4P */
    if (ref0p_prio < ref4p_prio) {
        LOG_INFO("REF0P priority (%d) already higher than REF4P (%d) - no action needed\n",
                 ref0p_prio, ref4p_prio);
        return 0;
    }

    /* Set REF0P to highest priority so PTP takes precedence */
    LOG_INFO("Setting REF0P priority to highest (%d)\n", DPLL_HIGHEST_PRIORITY);
    int old_prio = dpll_pin_set_priority(state->dpll_sock, state->pps_dpll_device_id,
                                         "REF0P", DPLL_HIGHEST_PRIORITY);
    if (old_prio >= 0) {
        LOG_INFO("Successfully set REF0P priority: %d -> %d\n", old_prio, DPLL_HIGHEST_PRIORITY);
        return 0;
    }

    LOG_ERROR("Failed to set REF0P priority\n");
    return -1;
}
#endif

/**
 * Handle PTP port up state when transitioning to MASTER
 * Checks DPLL pin source and forwards clock parameters if needed
 * @state: Application state
 */
void handle_ptp_port_up(AppState *state)
{
    if (state->pps_dpll_device_id) {
#if 0
        /* Ensure REF0P has higher priority than GNSS (REF4P) */
        reprioritize_ptp_pin(state);
#endif

        LOG_INFO("Enabling PTP pins REF0P and REF0N due to port up state\n");

        /* Enable REF0P - set to SELECTABLE state */
        int old_state = dpll_pin_set_state(state->dpll_sock, state->pps_dpll_device_id,
                                           "REF0P", DPLL_PIN_STATE_SELECTABLE);
        if (old_state >= 0) {
            LOG_INFO("Successfully enabled REF0P (old state: %d)\n", old_state);
        } else {
            LOG_ERROR("Failed to enable REF0P\n");
        }

        /* Enable REF0N - set to SELECTABLE state */
        old_state = dpll_pin_set_state(state->dpll_sock, state->pps_dpll_device_id,
                                       "REF0N", DPLL_PIN_STATE_SELECTABLE);
        if (old_state >= 0) {
            LOG_INFO("Successfully enabled REF0N (old state: %d)\n", old_state);
        } else {
            LOG_ERROR("Failed to enable REF0N\n");
        }

    } else {
        LOG_ERROR("DPLL not initialized - cannot enable PTP pins\n");
    }
}

/**
 * Handle PTP port down state by disabling PTP pins (REF0P, REF0N)
 * Called when port enters FAULTY or DISABLED state
 * @dpll_sock: DPLL netlink socket
 */
static void handle_ptp_port_down(AppState *state)
{
    if (state->pps_dpll_device_id) {
        LOG_INFO("Disabling PTP pins REF0P and REF0N due to port down state\n");
        
        /* Disable REF0P - set to DISCONNECTED state (2) */
        int old_state = dpll_pin_set_state(state->dpll_sock, state->pps_dpll_device_id, "REF0P", DPLL_PIN_STATE_DISCONNECTED);
        if (old_state >= 0) {
            LOG_INFO("Successfully disabled REF0P (old state: %d)\n", old_state);
        } else {
            LOG_ERROR("Failed to disable REF0P\n");
        }
        
        /* Disable REF0N - set to DISCONNECTED state (2) */
        old_state = dpll_pin_set_state(state->dpll_sock, state->pps_dpll_device_id, "REF0N", DPLL_PIN_STATE_DISCONNECTED);
        if (old_state >= 0) {
            LOG_INFO("Successfully disabled REF0N (old state: %d)\n", old_state);
        } else {
            LOG_ERROR("Failed to disable REF0N\n");
        }
    } else {
        LOG_ERROR("DPLL not initialized - cannot disable PTP pins\n");
    }
}

/**
 * Process PORT_DATA_SET response
 * Handles port state changes and triggers parameter forwarding on MASTER transition
 */
void process_port_data_set(AppState *state, uint16_t mgmt_id, 
                                   const uint8_t *data, size_t data_len)
{
    LOG_DEBUG("Received PORT_DATA_SET (0x%04X) - %zu bytes\n", mgmt_id, data_len);
    
#ifdef HEX_DUMP
    LOG_RAW("  PORT_DATA_SET Data: ");
    for (size_t i = 0; i < (data_len < 16 ? data_len : 16); i++) {
        LOG_RAW("%02X ", data[i]);
    }
    LOG_RAW("\n");
#endif

    if (data_len < 11) {
        LOG_ERROR("PORT_DATA_SET data too short (%zu bytes, expected >= 11)\n", data_len);
        return;
    }
    
    /* PORT_DATA_SET structure (IEEE 1588-2019):
     * Bytes 0-7: portIdentity.clockIdentity (8 bytes)
     * Bytes 8-9: portIdentity.portNumber (2 bytes)
     * Byte 10: portState enum:
     *   1 = INITIALIZING
     *   2 = FAULTY
     *   3 = DISABLED
     *   4 = LISTENING
     *   5 = PRE_MASTER
     *   6 = MASTER
     *   7 = PASSIVE
     *   8 = UNCALIBRATED
     *   9 = SLAVE
     */
    uint8_t old_port_state = state->port_state;
    uint8_t new_port_state = data[10];
    state->port_state = new_port_state;
    
    const char *state_str[] = {"UNKNOWN", "INITIALIZING", "FAULTY", "DISABLED",
                               "LISTENING", "PRE_MASTER", "MASTER", "PASSIVE",
                               "UNCALIBRATED", "SLAVE"};
    
    /* Only log when state actually changes */
    if (old_port_state != new_port_state) {
        LOG_INFO("PORT STATE CHANGE: %s (0x%02X)\n", 
               (new_port_state < 10) ? state_str[new_port_state] : "INVALID", new_port_state);
    }
    
    /* All pin enable/disable decisions are driven here from port state.
     *
     * Port DOWN (FAULTY=2, DISABLED=3): disable PTP pins immediately because
     * sync packets stop so TIME_STATUS_NP notifications will never arrive to
     * indicate GM loss. Force re-subscription so we don't miss the port-UP.
     *
     * Port UP (UNCALIBRATED=8, SLAVE=9) recovered from a down state:
     * re-enable PTP pins.
     */
    if (new_port_state == 2 || new_port_state == 3) {
        LOG_INFO("WARNING: PTP port is DOWN (FAULTY or DISABLED)\n");
        if (!state->ptp_port_down) {
            state->ptp_port_down = true;
            handle_ptp_port_down(state);
        }
        /* Force immediate re-subscription: ptp4l may drop the subscription when
         * port goes FAULTY/DISABLED so we won't miss the port-UP notification */
        state->last_subscription.tv_sec = 0;
    } else if (state->ptp_port_down && (new_port_state == 8 || new_port_state == 9)) {
        /* Port recovered to UNCALIBRATED/SLAVE from a down state.
         * Use ptp_port_down flag (not old_port_state) because ptp4l transitions
         * FAULTY -> LISTENING -> UNCALIBRATED: by the time UNCALIBRATED arrives
         * old_port_state is LISTENING(4), not FAULTY(2). */
        LOG_INFO("PTP port recovered to %s: re-enabling PTP pins\n",
                 state_str[new_port_state]);
        state->ptp_port_down = false;
        handle_ptp_port_up(state);
    }

}

/**
 * Process received messages
 */
void process_ptp_messages(AppState *state)
{
    uint8_t buffer[BUFFER_SIZE];
    const uint8_t *data;
    uint16_t mgmt_id;
    size_t data_len;
    fd_set readfds;

    struct timeval tv = {0, 100000};  /* 100ms timeout */
    
    FD_ZERO(&readfds);
    FD_SET(state->local_socket_fd, &readfds);
    
    int ret = select(state->local_socket_fd + 1, &readfds, NULL, NULL, &tv);
    if (ret < 0) {
        if (errno != EINTR) {
            LOG_ERROR("Select error: %s\n", strerror(errno));
        }
        return;
    }
    
    if (ret == 0) {
        return;  /* Timeout */
    }
    
    struct sockaddr_un from_addr;
    socklen_t from_len = sizeof(from_addr);
    ssize_t len = recvfrom(state->local_socket_fd, buffer, sizeof(buffer), 0,
                           (struct sockaddr *)&from_addr, &from_len);
    if (len < 0) {
        LOG_ERROR("Receive error: %s\n", strerror(errno));
        return;
    }
    
#ifdef HEX_DUMP
    /* Debug: print received message hex dump */
    LOG_DEBUG("\nReceived %zd bytes:\n", len);
    LOG_RAW("HEX: ");
    for (ssize_t i = 0; i < (len < 128 ? len : 128); i++) {
        LOG_RAW("%02X ", buffer[i]);
        if ((i + 1) % 16 == 0) LOG_RAW("\n     ");
    }
    LOG_RAW("\n");
#endif
    
    if (parse_management_response(buffer, len, &mgmt_id, &data, &data_len)) {
        LOG_DEBUG("Parsed management response: mgmt_id=0x%04X, data_len=%zu\n", mgmt_id, data_len);
        
        switch (mgmt_id) {
            case MGMT_ID_TIME_STATUS_NP:
                process_time_status_np(state, data, data_len);
                break;
                
            case MGMT_ID_PARENT_DATA_SET:
                process_parent_data_set(state, data, data_len);
                break;
                
            case MGMT_ID_SUBSCRIBE_EVENTS_NP:
                LOG_DEBUG("Subscription acknowledged by ptp4l\n");
                state->subscription_active = true;
                break;
                
            case MGMT_ID_FAULT_LOG:
                LOG_INFO("Received FAULT_LOG (0x0006) - %zu bytes\n", data_len);
                if (data_len >= 6) {
                    /* Decode FAULT_LOG data:
                     * IEEE 1588-2019: FAULT_LOG contains number of records and fault records
                     * However, linuxptp sends this as an error/status indicator
                     * Bytes 0-1: uint16 - appears to be related management ID (0xC003 = SUBSCRIBE_EVENTS_NP)
                     * Bytes 2-5: uint32 - additional status/error code
                     */
                    uint16_t related_id = ntohs(*((uint16_t*)data));
                    uint32_t status_code = ntohl(*((uint32_t*)(data + 2)));
                    LOG_INFO("  Related Management ID: 0x%04X, Status Code: 0x%08X\n", 
                             related_id, status_code);
                    
                    /* Hex dump of fault log data */
                    LOG_RAW("  Fault Log Data: ");
                    for (size_t i = 0; i < data_len && i < 16; i++) {
                        LOG_RAW("%02X ", data[i]);
                    }
                    LOG_RAW("\n");
                }
                break;
                
            case MGMT_ID_PORT_DATA_SET:
            case MGMT_ID_PORT_DATA_SET_NP:
                process_port_data_set(state, mgmt_id, data, data_len);
                break;

            case MGMT_ID_GEARSHIFT_NP:
                /* Unsolicited gearshift notification from ptp4l — already handled
                 * synchronously in send_gearshift(); just drain it silently. */
                LOG_DEBUG("Received GEARSHIFT_NP notification (gear=0x%02X), discarding\n",
                          data_len > 0 ? data[0] : 0xFF);
                break;

            default:
                LOG_INFO("Received unhandled management ID: 0x%04X\n", mgmt_id);
                break;
        }
    } else {
        LOG_ERROR("Failed to parse management response (%zd bytes)\n", len);
    }
}
