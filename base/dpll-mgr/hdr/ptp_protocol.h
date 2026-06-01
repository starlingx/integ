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
 * @file ptp_protocol.h
 * @brief PTP Protocol Processing Functions
 * 
 * This module handles all PTP management protocol operations including:
 * - Building and parsing PTP management messages
 * - Processing PTP TLVs (TIME_STATUS_NP, PARENT_DATA_SET, etc.)
 * - Subscription management
 * - Parameter forwarding
 */

#ifndef _PTP_PROTOCOL_H
#define _PTP_PROTOCOL_H

#include "apts_manager.h"

/**
 * get_mgmt_id_data_size - Get expected data size for a management ID
 * @mgmt_id: Management ID
 *
 * Returns: Expected data size in bytes
 */
size_t get_mgmt_id_data_size(uint16_t mgmt_id);

/**
 * build_management_message - Build a PTP management message
 * @buffer: Buffer to write message to
 * @buffer_size: Size of buffer
 * @sequence_id: Sequence ID for the message
 * @mgmt_id: Management ID
 * @action: Action field (GET, SET, etc.)
 * @data: Optional data payload
 * @data_len: Length of data payload
 *
 * Returns: Message length on success, -1 on error
 */
int build_management_message(uint8_t *buffer, size_t buffer_size,
                             uint16_t sequence_id, uint16_t mgmt_id,
                             uint8_t action,
                             const void *data, size_t data_len);

/**
 * build_subscription_message - Build SUBSCRIBE_EVENTS_NP message
 * @buffer: Buffer to write message to
 * @buffer_size: Size of buffer
 * @sequence_id: Sequence ID
 * @duration: Subscription duration in seconds
 * @event_bitmask: Event bitmask (which events to subscribe to)
 *
 * Returns: Message length on success, -1 on error
 */
int build_subscription_message(uint8_t *buffer, size_t buffer_size,
                               uint16_t sequence_id, uint16_t duration,
                               uint8_t event_bitmask);

/**
 * send_subscription_request - Send subscription request to ptp4l
 * @sock_fd: Socket file descriptor
 * @peer_addr: Peer address structure
 * @sequence_id: Pointer to sequence ID (will be incremented)
 *
 * Returns: true on success, false on error
 */
bool send_subscription_request(int sock_fd, struct sockaddr_un *peer_addr, 
                               uint16_t *sequence_id);

/**
 * send_get_request - Send GET request for clock data
 * @sockfd: Socket file descriptor
 * @peer_addr: Peer address structure
 * @mgmt_id: Management ID to query
 * @seq: Pointer to sequence ID (will be incremented)
 *
 * Returns: 0 on success, errno-style error code on failure
 */
int send_get_request(int sockfd, struct sockaddr_un *peer_addr,
                     uint16_t mgmt_id, uint16_t *seq);

/**
 * parse_management_response - Parse received management message
 * @buffer: Buffer containing received message
 * @len: Length of received message
 * @mgmt_id: Pointer to store parsed management ID
 * @data: Pointer to store data location
 * @data_len: Pointer to store data length
 *
 * Returns: true on success, false on error
 */
bool parse_management_response(const uint8_t *buffer, size_t len,
                              uint16_t *mgmt_id, const uint8_t **data,
                              size_t *data_len);

/**
 * process_time_status_np - Process TIME_STATUS_NP response
 * @state: Application state
 * @data: TLV data
 * @data_len: TLV data length
 */
void process_time_status_np(AppState *state, const uint8_t *data, size_t data_len);

/**
 * process_parent_data_set - Process PARENT_DATA_SET response
 * @state: Application state
 * @data: TLV data
 * @data_len: TLV data length
 */
void process_parent_data_set(AppState *state, const uint8_t *data, size_t data_len);

/**
 * convert_to_grandmaster_settings_np - Convert clock parameters to GM settings format
 * @clock_params: Clock parameters structure
 * @gm_settings_data: Buffer to write GM settings data
 * @data_len: Pointer to store data length
 */
void convert_to_grandmaster_settings_np(const ClockParameters *clock_params,
                                       uint8_t *gm_settings_data,
                                       size_t *data_len);

/**
 * build_grandmaster_settings_np_message - Build GRANDMASTER_SETTINGS_NP SET message
 * @buffer: Buffer to write message to
 * @buffer_size: Size of buffer
 * @sequence_id: Sequence ID
 * @clock_params: Clock parameters to send
 *
 * Returns: Message length on success, -1 on error
 */
int build_grandmaster_settings_np_message(uint8_t *buffer, size_t buffer_size,
                                         uint16_t sequence_id,
                                         const ClockParameters *clock_params);

/**
 * forward_clock_parameters - Forward clock parameters to remote instances
 * @state: Application state
 */
void forward_clock_parameters(AppState *state);

/**
 * check_free_running_mode - Check if ptp4l is in free running mode
 * @sock_fd: Socket file descriptor
 * @peer_addr: Peer address structure
 * @sequence_id: Pointer to sequence ID (will be incremented)
 *
 * Returns: true if free running, false otherwise
 */
bool check_free_running_mode(int sock_fd, struct sockaddr_un *peer_addr, 
                             uint16_t *sequence_id);

/**
 * process_port_data_set - Process PORT_DATA_SET response
 * @state: Application state
 * @mgmt_id: Management ID
 * @data: TLV data
 * @data_len: TLV data length
 */
void process_port_data_set(AppState *state, uint16_t mgmt_id, 
                          const uint8_t *data, size_t data_len);

/**
 * process_ptp_messages - Process received messages from ptp4l
 * @state: Application state
 */
void process_ptp_messages(AppState *state);

/**
 * handle_ptp_port_up - Enable PTP DPLL pins (REF0P, REF0N -> SELECTABLE)
 * Called at init time and on gmPresent 0->1 transitions.
 * @state: Application state
 */
void handle_ptp_port_up(AppState *state);

#endif /* _PTP_PROTOCOL_H */
