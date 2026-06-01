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


#define MODULE "DPLL"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <time.h>
#include <net/if.h>
#include <linux/dpll.h>
#include <ynl/ynl.h>
#include "../hdr/dpll_utils.h"
#include "../hdr/log.h"

//#define DEBUG

extern const struct ynl_family ynl_dpll_family;
struct dpll_pin_get_list *pin_list = NULL;
struct ynl_sock *ys;

/* Adding for Debug purpose */
struct dpll_pin_get_list* dpll_pin_dump(struct ynl_sock *ys, __u32 device_id)
{
	struct dpll_pin_get_req_dump pin_req = {0};
	struct dpll_pin_get_list *pin_list = NULL;
	struct dpll_pin_get_list *pin_list_head = NULL;
	(void)device_id;

	/* Check if YNL socket is valid */
	if (!ys) {
		LOG_ERROR("dpll_pin_dump: YNL socket is NULL\n");
		return NULL;
	}

	/* Do unfiltered pin dump; parent_device[] carries per-device data */

	pin_list = dpll_pin_get_dump(ys, &pin_req);
	if (pin_list == NULL) {
		LOG_ERROR("No pin info received\n");
		return NULL;
	}
	
	pin_list_head = pin_list;  /* Save the head before iteration */
	
#ifdef DEBUG
	while(pin_list) {
		if (pin_list->obj.parent_device) {
			LOG_DEBUG("id: %d boardlabel:%s state:%u\n", pin_list->obj.id,
					pin_list->obj.board_label,
					pin_list->obj.parent_device->state);
		}
		pin_list = pin_list->next;
	}
#endif
	return pin_list_head;  /* Return the saved head, not NULL */
}

int dpll_one_pin_by_package_label(struct ynl_sock *ys,
		char* package_label,
		struct dpll_pin_get_rsp *pin_rsp)
{
        int cnt = 0; 

	/* pin-get dump returns pin objects with parent_device entries per DPLL device */
	pin_list = dpll_pin_dump(ys, 0);

	while(pin_list && (cnt < 24)) {
		if (pin_list->obj.package_label &&
		    strncmp(pin_list->obj.package_label,
					package_label,
					strlen(package_label)) == 0) {
			memcpy(pin_rsp, &(pin_list->obj), sizeof(struct dpll_pin_get_rsp));
			return 0;
		}
		pin_list = pin_list->next;
		cnt++;
	}
        return 1;
}

__s64 dpll_pin_set_phase_adjust(struct ynl_sock *ys, char *package_label, 
		__s64 phase_adjust)
{
	int ret = 0;
	__s64 old_phase_adjust = -1;
	struct dpll_pin_get_rsp pin_rsp = {0};
	struct dpll_pin_set_req set_req = {0};

	/* Validate phase_adjust is within __s32 range for netlink */
	if (phase_adjust > INT32_MAX || phase_adjust < INT32_MIN) {
		LOG_ERROR("Phase adjust value %lld fs out of range [%d, %d]\n",
				(long long)phase_adjust, INT32_MIN, INT32_MAX);
		return -1;
	}

	ret = dpll_one_pin_by_package_label(ys, package_label, &pin_rsp);
	if (!ret) {
		if (pin_rsp._present.phase_adjust) {
			old_phase_adjust = pin_rsp.phase_adjust;
			LOG_DEBUG("package label: %s phase_adj:%lld fs, input:%lld fs\n",
					package_label,
					(long long)pin_rsp.phase_adjust,
					(long long)phase_adjust);
		}
		set_req._present.id = 1;
		set_req.id = pin_rsp.id;

		set_req._present.phase_adjust = 1;
		set_req.phase_adjust = (__s32)phase_adjust;  /* Safe cast after bounds check */

		ret = dpll_pin_set(ys, &set_req);
		if (ret) {
			LOG_ERROR("Error while setting phase adjust\n");
		}
	}
	return old_phase_adjust;
}


int dpll_pin_set_state(struct ynl_sock *ys, __u32 device_id, char *package_label, 
		int state)
{
	int ret = 0;
	int old_state = -1;
	struct dpll_pin_get_rsp pin_rsp = {0};
	struct dpll_pin_set_req set_req = {0};

	/* Get pin info by package_label to obtain pin ID */
	ret = dpll_one_pin_by_package_label(ys, package_label, &pin_rsp);
	if (ret) {
		LOG_ERROR("Pin %s not found for device %u\n", package_label, device_id);
		return -1;
	}

	/* Get old state from the correct parent_device matching device_id */
	if (pin_rsp.parent_device) {
		struct dpll_pin_parent_device *target_parent = NULL;
		/* Find parent_device matching device_id */
		for (unsigned int i = 0; i < pin_rsp.n_parent_device; i++) {
			if (pin_rsp.parent_device[i].parent_id == device_id) {
				target_parent = &pin_rsp.parent_device[i];
				break;
			}
		}
		if (target_parent) {
			old_state = target_parent->state;
			if (old_state == state) {
				LOG_INFO("Same state observed: %s state:%d\n",
					package_label, old_state);
			} else {
				LOG_INFO("Changing state: %s from %d to %d\n",
					package_label, old_state, state);
			}
		}
	}

	/* Set the new state */
	set_req._present.id = 1;
	set_req.id = pin_rsp.id;

	set_req.parent_device = (struct dpll_pin_parent_device*)
		calloc(1, sizeof(struct dpll_pin_parent_device));
	if (!set_req.parent_device) {
		LOG_ERROR("Memory allocation failed\n");
		return -1;
	}
	set_req.n_parent_device = 1;
	set_req.parent_device->_present.state = 1;
	set_req.parent_device->state = state;

	set_req.parent_device->_present.parent_id = 1;
	set_req.parent_device->parent_id = device_id;
	
	ret = dpll_pin_set(ys, &set_req);
	if (ret) {
		LOG_ERROR("Error while changing state\n");
		free(set_req.parent_device);
		return -1;
	}

	free(set_req.parent_device);

	return old_state;
}


int dpll_pin_set_priority(struct ynl_sock *ys, __u32 device_id, char *package_label, 
		int prio)
{
	int ret = 0;
	int old_prio = -1;
	struct dpll_pin_get_rsp pin_rsp = {0};
	struct dpll_pin_set_req set_req = {0};
	unsigned int parent_count = 0;
	struct dpll_pin_parent_device *target_parent = NULL;

	if (!ys) {
		LOG_ERROR("dpll_pin_set_priority: YNL socket is NULL\n");
		return -1;
	}

	/* Get pin info by package_label to obtain pin ID */
	ret = dpll_one_pin_by_package_label(ys, package_label, &pin_rsp);
	if (ret) {
		LOG_ERROR("Pin %s not found\n", package_label);
		return -1;
	}

	/* Get old priority/state from the correct parent_device matching device_id */
	if (pin_rsp.parent_device) {
		parent_count = pin_rsp.n_parent_device;
		LOG_DEBUG("Pin lookup: package_label:%s pin_id:%u parent_count:%u requested_prio:%d\n",
			package_label, pin_rsp.id, parent_count, prio);

		for (unsigned int i = 0; i < parent_count; i++) {
			LOG_DEBUG("  parent[%u]: parent_id=%u state=%u prio=%u present(state=%u prio=%u phase_offset=%u)\n",
				i,
				pin_rsp.parent_device[i].parent_id,
				pin_rsp.parent_device[i].state,
				pin_rsp.parent_device[i].prio,
				pin_rsp.parent_device[i]._present.state,
				pin_rsp.parent_device[i]._present.prio,
				pin_rsp.parent_device[i]._present.phase_offset);
		}

		/* Find parent_device matching device_id */
		for (unsigned int i = 0; i < parent_count; i++) {
			if (pin_rsp.parent_device[i].parent_id == device_id) {
				target_parent = &pin_rsp.parent_device[i];
				break;
			}
		}
		if (target_parent) {
			old_prio = target_parent->prio;
			LOG_DEBUG("device:%u package label:%s cur prio:%d state:%d\n",
				device_id, package_label, old_prio, target_parent->state);
		} else {
			LOG_ERROR("No parent match for package label:%s on device:%u\n",
				package_label, device_id);
		}
	}

	if (!target_parent) {
		LOG_ERROR("Cannot set priority for %s: missing parent context for device %u\n",
			package_label, device_id);
		return -1;
	}

	/* Policy 1 (always enabled): requested priority 15 means disconnect pin and return */
	if (prio == 15) {
		if (target_parent->state != DPLL_PIN_STATE_DISCONNECTED) {
			int old_state = dpll_pin_set_state(ys, device_id, package_label, DPLL_PIN_STATE_DISCONNECTED);
			if (old_state < 0) {
				LOG_ERROR("Failed to move %s to DISCONNECTED for requested priority 15\n",
					package_label);
				return -1;
			}
			LOG_INFO("Requested priority=15: moved %s state from %d to DISCONNECTED; skipping priority write\n",
				package_label, old_state);
		} else {
			LOG_INFO("Requested priority=15: %s already DISCONNECTED; skipping priority write\n",
				package_label);
		}
		return old_prio;
	}

#ifdef DPLL_SET_SELECTABLE_BEFORE_PRIORITY_SET
	/* Policy 2: for requested priority <15, disconnected pins must be selectable first */
	if (prio < 15 && target_parent->state == DPLL_PIN_STATE_DISCONNECTED) {
		int old_state = dpll_pin_set_state(ys, device_id, package_label, DPLL_PIN_STATE_SELECTABLE);
		if (old_state < 0) {
			LOG_ERROR("Failed to move %s from DISCONNECTED to SELECTABLE before priority update\n",
				package_label);
			return -1;
		}
		LOG_INFO("Moved %s state from %d to SELECTABLE before applying priority %d\n",
			package_label, old_state, prio);
	}
#endif


	/* Set the new priority */
	set_req._present.id = 1;
	set_req.id = pin_rsp.id;

	set_req.parent_device = (struct dpll_pin_parent_device*)
		calloc(1, sizeof(struct dpll_pin_parent_device));
	if (!set_req.parent_device) {
		LOG_ERROR("Memory allocation failed\n");
		return -1;
	}
	set_req.n_parent_device = 1;
	set_req.parent_device->_present.prio = 1;
	set_req.parent_device->prio = prio;

	set_req.parent_device->_present.parent_id = 1;
	set_req.parent_device->parent_id = device_id;

	LOG_INFO("Set request: pin_id=%u package_label=%s parent_id=%u prio=%d parent_count=%u\n",
		set_req.id,
		package_label,
		set_req.parent_device->parent_id,
		set_req.parent_device->prio,
		set_req.n_parent_device);
	
	ret = dpll_pin_set(ys, &set_req);
	if (ret) {
		LOG_ERROR("Error while changing priority for %s on device %u (ret=%d, ynl_code=%d, attr_offs=%u, msg=%s)\n",
			package_label,
			device_id,
			ret,
			ys->err.code,
			ys->err.attr_offs,
			ys->err.msg);
		free(set_req.parent_device);
		return -1;
	}

	LOG_DEBUG("Priority set ACK: package_label=%s device_id=%u requested_prio=%d\n",
		package_label, device_id, prio);

	free(set_req.parent_device);

	return old_prio;
}

int dpll_pin_get_priority(struct ynl_sock *ys, __u32 device_id, char *package_label)
{
	int ret = 0;
	int prio = -1;
	struct dpll_pin_parent_device *target_parent = NULL;
	struct dpll_pin_get_rsp pin_rsp = {0};

	ret = dpll_one_pin_by_package_label(ys, package_label, &pin_rsp);
	if (!ret) {
		if (pin_rsp.parent_device) {
			for (unsigned int i = 0; i < pin_rsp.n_parent_device; i++) {
				if (pin_rsp.parent_device[i].parent_id == device_id) {
					target_parent = &pin_rsp.parent_device[i];
					break;
				}
			}

			if (target_parent) {
				prio = target_parent->prio;
				LOG_DEBUG("device:%u package label:%s prio:%d state:%d\n",
					device_id,
					package_label,
					target_parent->prio,
					target_parent->state);
			} else {
				LOG_ERROR("No parent match for package label:%s on device:%u\n",
					package_label, device_id);
			}
		}
	}
	return prio;
}

int init_dpll()
{
	struct ynl_error yerr;

	ys = ynl_sock_create(&ynl_dpll_family, &yerr);
	if (!ys) {
		LOG_ERROR("Not able to create netlink socket: %s\n", yerr.msg);
		return 1;
	}
	LOG_INFO("Socket creation sucessful\n");

	return 0;
}

/**
 * dpll_find_device_id_by_type - Find the DPLL device of specified type
 * @ys: YNL socket
 * @device_type: DPLL device type to search for (e.g., DPLL_TYPE_EEC, DPLL_TYPE_PPS)
 *
 * Returns: Device ID on success, -1 if not found or on error
 */
int dpll_find_device_id_by_type(struct ynl_sock *ys, enum dpll_type device_type)
{
	struct dpll_device_get_list *dev_list = NULL;
	struct dpll_device_get_list *dev_iter = NULL;
	int device_id = -1;

	if (!ys) {
		LOG_ERROR("dpll_find_device_id_by_type: YNL socket is NULL\n");
		return -1;
	}

	/* Get list of all DPLL devices */
	dev_list = dpll_device_get_dump(ys);
	if (!dev_list) {
		LOG_ERROR("Failed to get DPLL device list\n");
		return -1;
	}

	/* Iterate through devices to find specified type */
	dev_iter = dev_list;
	while (dev_iter) {
		if (dev_iter->obj._present.type &&
		    dev_iter->obj.type == device_type) {
			/* Also verify this belongs to the zl3073x module */
			if (dev_iter->obj._present.module_name_len &&
			    strcmp(dev_iter->obj.module_name, "zl3073x") != 0) {
				LOG_DEBUG("Skipping device type %d id %d: module_name '%s' != 'zl3073x'\n",
					  device_type,
						  dev_iter->obj._present.id ? (int)dev_iter->obj.id : -1,
					  dev_iter->obj.module_name);
				dev_iter = dev_iter->next;
				continue;
			}
			if (dev_iter->obj._present.id) {
				device_id = dev_iter->obj.id;
				LOG_DEBUG("Found device type %d with ID: %d\n", device_type, device_id);
				break;
			}
		}
		dev_iter = dev_iter->next;
	}

	/* Free the device list */
	dpll_device_get_list_free(dev_list);

	if (device_id == -1) {
		LOG_ERROR("No device of type %d found\n", device_type);
	}

	return device_id;
}

/**
 * dpll_get_device_state_and_connected_pin - Get DPLL device state and connected pin info
 * @ys: YNL socket
 * @device_id: DPLL device ID
 * @lock_status: Output pointer for lock status (can be NULL)
 * @mode: Output pointer for device mode (can be NULL)
 * @connected_pin_id: Output pointer for connected pin ID (can be NULL)
 * @connected_pin_source: Output pointer for connected pin source enum (can be NULL)
 * @ptp_pin_id: Output pointer for PTP pin ID (REF0N) - only updated when REF0N found (can be NULL)
 * @ptp_pin_state: Output pointer for PTP pin state (REF0N) - only updated when REF0N found (can be NULL)
 *
 * Returns: 0 on success, -1 on error
 */
int dpll_get_device_state_and_connected_pin(struct ynl_sock *ys,
					    __u32 device_id,
					    enum dpll_lock_status *lock_status,
					    enum dpll_mode *mode,
					    __u32 *connected_pin_id,
					    enum pin_source *connected_pin_source,
					    __u32 *ptp_pin_id,
					    enum dpll_pin_state *ptp_pin_state)
{
	struct dpll_device_get_req dev_req = {0};
	struct dpll_device_get_rsp *dev_rsp = NULL;
	struct dpll_pin_get_list *pin_list_iter = NULL;
	const char *pin_label = NULL;
	int ret = -1;

	/* Check if YNL socket is valid */
	if (!ys) {
		LOG_ERROR("dpll_get_device_state_and_connected_pin: YNL socket is NULL\n");
		return -1;
	}

	/* Get device state */
	dev_req._present.id = 1;
	dev_req.id = device_id;

	dev_rsp = dpll_device_get(ys, &dev_req);
	if (!dev_rsp) {
		LOG_ERROR("Failed to get DPLL device %u state\n", device_id);
		return -1;
	}

	/* Copy device state information */
	if (lock_status && dev_rsp->_present.lock_status) {
		*lock_status = dev_rsp->lock_status;
	}

	if (mode && dev_rsp->_present.mode) {
		*mode = dev_rsp->mode;
	}

	LOG_DEBUG("DPLL Device %u: lock_status=%s, mode=%s\n",
	       device_id,
	       dev_rsp->_present.lock_status ? 
	           dpll_lock_status_str(dev_rsp->lock_status) : "unknown",
	       dev_rsp->_present.mode ? 
	           dpll_mode_str(dev_rsp->mode) : "unknown");
	fflush(g_log_file ? g_log_file : stdout);

	/* Get all pins and find the connected one */
	pin_list_iter = dpll_pin_dump(ys, device_id);
	if (!pin_list_iter) {
		LOG_ERROR("Failed to get pin list\n");
		dpll_device_get_rsp_free(dev_rsp);
		return -1;
	}

	/* Iterate through pins to find the connected one */
	int pin_count = 0;
	while (pin_list_iter) {
		pin_count++;
		
		/* Check if this pin has parent devices */
		if (!pin_list_iter->obj.parent_device) {
			pin_list_iter = pin_list_iter->next;
			continue;
		}
		
		/* Iterate through all parent devices to find matching device_id */
		int matching_parent_idx = -1;
		unsigned int parent_count = pin_list_iter->obj.n_parent_device;
		
		for (unsigned int i = 0; i < parent_count; i++) {
			struct dpll_pin_parent_device *parent = &pin_list_iter->obj.parent_device[i];
			if (parent->parent_id == device_id && parent->_present.state) {
				matching_parent_idx = i;
				break;
			}
		}
		
		/* If no parent matches this device_id, skip to next pin */
		if (matching_parent_idx == -1) {
			pin_list_iter = pin_list_iter->next;
			continue;
		}
		
		/* Found a parent device matching our device_id */
		struct dpll_pin_parent_device *matched_parent = &pin_list_iter->obj.parent_device[matching_parent_idx];
		
		/* Get pin label */
		const char *current_pin_label = NULL;
		if (pin_list_iter->obj.board_label) {
			current_pin_label = pin_list_iter->obj.board_label;
		} else if (pin_list_iter->obj.package_label) {
			current_pin_label = pin_list_iter->obj.package_label;
		}
		
		/* Convert label to pin source to check if it's a PTP pin */
		enum pin_source current_pin_source = pin_label_to_source(current_pin_label);
		
		/* Check if this is a PTP pin (SDP2_REF0P or SDP0_REF0N) and populate ptp_pin_id/state */
		if (is_ptp_pin(current_pin_source)) {
			if (ptp_pin_id) {
				*ptp_pin_id = pin_list_iter->obj.id;
			}
			/* Use 2nd DPLL parent device (index 1) if available, otherwise use 1st (index 0) */
			struct dpll_pin_parent_device *target_parent = pin_list_iter->obj.parent_device;
			int parent_idx = 0;
			if (pin_list_iter->obj.n_parent_device >= 2) {
				parent_idx = 1;  /* Use 2nd parent device */
				target_parent = &pin_list_iter->obj.parent_device[1];
				LOG_DEBUG("Using 2nd DPLL parent device (index 1) for PTP pin\n");
			}
			if (ptp_pin_state && target_parent) {
				*ptp_pin_state = target_parent->state;
			}
			LOG_DEBUG("Found PTP Pin: id=%u, label=%s, parent_idx=%d, state=%s\n",
			         pin_list_iter->obj.id,
			         current_pin_label ? current_pin_label : "unknown",
			         parent_idx,
			         target_parent ? dpll_pin_state_str(target_parent->state) : "unknown");
		}
		
		/* Process connected pin */
		if (matched_parent->state == DPLL_PIN_STATE_CONNECTED) {
			
			/* Found connected pin */
			if (connected_pin_id) {
				*connected_pin_id = pin_list_iter->obj.id;
			}

			/* Use the label we already extracted */
			pin_label = current_pin_label;

			/* Convert label to pin source enum */
			if (connected_pin_source) {
				*connected_pin_source = pin_label_to_source(pin_label);
			}

			/* Log connected pin information */
			if (matched_parent->_present.phase_offset) {
				LOG_DEBUG("Connected Pin: id=%u, label=%s, state=%s, phase_offset=%lld ns\n",
				       pin_list_iter->obj.id,
				       pin_label ? pin_label : "unknown",
				       dpll_pin_state_str(matched_parent->state),
				       (long long)matched_parent->phase_offset);
			} else {
				LOG_DEBUG("Connected Pin: id=%u, label=%s, state=%s\n",
				       pin_list_iter->obj.id,
				       pin_label ? pin_label : "unknown",
				       dpll_pin_state_str(matched_parent->state));
			}

			ret = 0;
			break;
		}
		
		pin_list_iter = pin_list_iter->next;
	}

	dpll_device_get_rsp_free(dev_rsp);

	if (ret != 0) {
		LOG_DEBUG("No connected pin found for device %u\n", device_id);
	} else {
		if (connected_pin_id && connected_pin_source)
			LOG_DEBUG("Connected PIN ID: %u PIN Source:%d\n", *connected_pin_id, *connected_pin_source);
		else
			return -1;
	}

	return ret;
}
