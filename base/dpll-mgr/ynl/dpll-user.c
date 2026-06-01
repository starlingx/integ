// SPDX-License-Identifier: ((GPL-2.0 WITH Linux-syscall-note) OR BSD-3-Clause)
/* Do not edit directly, auto-generated from: */
/*	Documentation/netlink/specs/dpll.yaml */
/* YNL-GEN user source */

#include <stdlib.h>
#include <string.h>
#include "dpll-user.h"
#include "ynl.h"
#include <linux/dpll.h>

#include <linux/genetlink.h>

/* Enums */
static const char * const dpll_op_strmap[] = {
	[DPLL_CMD_DEVICE_ID_GET] = "device-id-get",
	[DPLL_CMD_DEVICE_GET] = "device-get",
	[DPLL_CMD_DEVICE_SET] = "device-set",
	[DPLL_CMD_DEVICE_CREATE_NTF] = "device-create-ntf",
	[DPLL_CMD_DEVICE_DELETE_NTF] = "device-delete-ntf",
	[DPLL_CMD_DEVICE_CHANGE_NTF] = "device-change-ntf",
	[DPLL_CMD_PIN_ID_GET] = "pin-id-get",
	[DPLL_CMD_PIN_GET] = "pin-get",
	[DPLL_CMD_PIN_SET] = "pin-set",
	[DPLL_CMD_PIN_CREATE_NTF] = "pin-create-ntf",
	[DPLL_CMD_PIN_DELETE_NTF] = "pin-delete-ntf",
	[DPLL_CMD_PIN_CHANGE_NTF] = "pin-change-ntf",
};

const char *dpll_op_str(int op)
{
	if (op < 0 || op >= (int)YNL_ARRAY_SIZE(dpll_op_strmap))
		return NULL;
	return dpll_op_strmap[op];
}

static const char * const dpll_mode_strmap[] = {
	[1] = "manual",
	[2] = "automatic",
};

const char *dpll_mode_str(enum dpll_mode value)
{
	if (value < 0 || value >= (int)YNL_ARRAY_SIZE(dpll_mode_strmap))
		return NULL;
	return dpll_mode_strmap[value];
}

static const char * const dpll_lock_status_strmap[] = {
	[1] = "unlocked",
	[2] = "locked",
	[3] = "locked-ho-acq",
	[4] = "holdover",
};

const char *dpll_lock_status_str(enum dpll_lock_status value)
{
	if (value < 0 || value >= (int)YNL_ARRAY_SIZE(dpll_lock_status_strmap))
		return NULL;
	return dpll_lock_status_strmap[value];
}

static const char * const dpll_lock_status_error_strmap[] = {
	[1] = "none",
	[2] = "undefined",
	[3] = "media-down",
	[4] = "fractional-frequency-offset-too-high",
};

const char *dpll_lock_status_error_str(enum dpll_lock_status_error value)
{
	if (value < 0 || value >= (int)YNL_ARRAY_SIZE(dpll_lock_status_error_strmap))
		return NULL;
	return dpll_lock_status_error_strmap[value];
}

static const char * const dpll_type_strmap[] = {
	[1] = "pps",
	[2] = "eec",
};

const char *dpll_type_str(enum dpll_type value)
{
	if (value < 0 || value >= (int)YNL_ARRAY_SIZE(dpll_type_strmap))
		return NULL;
	return dpll_type_strmap[value];
}

static const char * const dpll_pin_type_strmap[] = {
	[1] = "mux",
	[2] = "ext",
	[3] = "synce-eth-port",
	[4] = "int-oscillator",
	[5] = "gnss",
};

const char *dpll_pin_type_str(enum dpll_pin_type value)
{
	if (value < 0 || value >= (int)YNL_ARRAY_SIZE(dpll_pin_type_strmap))
		return NULL;
	return dpll_pin_type_strmap[value];
}

static const char * const dpll_pin_direction_strmap[] = {
	[1] = "input",
	[2] = "output",
};

const char *dpll_pin_direction_str(enum dpll_pin_direction value)
{
	if (value < 0 || value >= (int)YNL_ARRAY_SIZE(dpll_pin_direction_strmap))
		return NULL;
	return dpll_pin_direction_strmap[value];
}

static const char * const dpll_pin_state_strmap[] = {
	[1] = "connected",
	[2] = "disconnected",
	[3] = "selectable",
};

const char *dpll_pin_state_str(enum dpll_pin_state value)
{
	if (value < 0 || value >= (int)YNL_ARRAY_SIZE(dpll_pin_state_strmap))
		return NULL;
	return dpll_pin_state_strmap[value];
}

static const char * const dpll_pin_capabilities_strmap[] = {
	[0] = "direction-can-change",
	[1] = "priority-can-change",
	[2] = "state-can-change",
};

const char *dpll_pin_capabilities_str(enum dpll_pin_capabilities value)
{
	value = ffs(value) - 1;
	if (value < 0 || value >= (int)YNL_ARRAY_SIZE(dpll_pin_capabilities_strmap))
		return NULL;
	return dpll_pin_capabilities_strmap[value];
}

/* Policies */
const struct ynl_policy_attr dpll_frequency_range_policy[DPLL_A_PIN_MAX + 1] = {
	[DPLL_A_PIN_FREQUENCY_MIN] = { .name = "frequency-min", .type = YNL_PT_U64, },
	[DPLL_A_PIN_FREQUENCY_MAX] = { .name = "frequency-max", .type = YNL_PT_U64, },
};

const struct ynl_policy_nest dpll_frequency_range_nest = {
	.max_attr = DPLL_A_PIN_MAX,
	.table = dpll_frequency_range_policy,
};

const struct ynl_policy_attr dpll_pin_parent_device_policy[DPLL_A_PIN_MAX + 1] = {
	[DPLL_A_PIN_PARENT_ID] = { .name = "parent-id", .type = YNL_PT_U32, },
	[DPLL_A_PIN_DIRECTION] = { .name = "direction", .type = YNL_PT_U32, },
	[DPLL_A_PIN_PRIO] = { .name = "prio", .type = YNL_PT_U32, },
	[DPLL_A_PIN_STATE] = { .name = "state", .type = YNL_PT_U32, },
	[DPLL_A_PIN_PHASE_OFFSET] = { .name = "phase-offset", .type = YNL_PT_U64, },
};

const struct ynl_policy_nest dpll_pin_parent_device_nest = {
	.max_attr = DPLL_A_PIN_MAX,
	.table = dpll_pin_parent_device_policy,
};

const struct ynl_policy_attr dpll_pin_parent_pin_policy[DPLL_A_PIN_MAX + 1] = {
	[DPLL_A_PIN_PARENT_ID] = { .name = "parent-id", .type = YNL_PT_U32, },
	[DPLL_A_PIN_STATE] = { .name = "state", .type = YNL_PT_U32, },
};

const struct ynl_policy_nest dpll_pin_parent_pin_nest = {
	.max_attr = DPLL_A_PIN_MAX,
	.table = dpll_pin_parent_pin_policy,
};

const struct ynl_policy_attr dpll_policy[DPLL_A_MAX + 1] = {
	[DPLL_A_ID] = { .name = "id", .type = YNL_PT_U32, },
	[DPLL_A_MODULE_NAME] = { .name = "module-name", .type = YNL_PT_NUL_STR, },
	[DPLL_A_PAD] = { .name = "pad", .type = YNL_PT_IGNORE, },
	[DPLL_A_CLOCK_ID] = { .name = "clock-id", .type = YNL_PT_U64, },
	[DPLL_A_MODE] = { .name = "mode", .type = YNL_PT_U32, },
	[DPLL_A_MODE_SUPPORTED] = { .name = "mode-supported", .type = YNL_PT_U32, },
	[DPLL_A_LOCK_STATUS] = { .name = "lock-status", .type = YNL_PT_U32, },
	[DPLL_A_TEMP] = { .name = "temp", .type = YNL_PT_U32, },
	[DPLL_A_TYPE] = { .name = "type", .type = YNL_PT_U32, },
	[DPLL_A_LOCK_STATUS_ERROR] = { .name = "lock-status-error", .type = YNL_PT_U32, },
};

const struct ynl_policy_nest dpll_nest = {
	.max_attr = DPLL_A_MAX,
	.table = dpll_policy,
};

const struct ynl_policy_attr dpll_pin_policy[DPLL_A_PIN_MAX + 1] = {
	[DPLL_A_PIN_ID] = { .name = "id", .type = YNL_PT_U32, },
	[DPLL_A_PIN_PARENT_ID] = { .name = "parent-id", .type = YNL_PT_U32, },
	[DPLL_A_PIN_MODULE_NAME] = { .name = "module-name", .type = YNL_PT_NUL_STR, },
	[DPLL_A_PIN_PAD] = { .name = "pad", .type = YNL_PT_IGNORE, },
	[DPLL_A_PIN_CLOCK_ID] = { .name = "clock-id", .type = YNL_PT_U64, },
	[DPLL_A_PIN_BOARD_LABEL] = { .name = "board-label", .type = YNL_PT_NUL_STR, },
	[DPLL_A_PIN_PANEL_LABEL] = { .name = "panel-label", .type = YNL_PT_NUL_STR, },
	[DPLL_A_PIN_PACKAGE_LABEL] = { .name = "package-label", .type = YNL_PT_NUL_STR, },
	[DPLL_A_PIN_TYPE] = { .name = "type", .type = YNL_PT_U32, },
	[DPLL_A_PIN_DIRECTION] = { .name = "direction", .type = YNL_PT_U32, },
	[DPLL_A_PIN_FREQUENCY] = { .name = "frequency", .type = YNL_PT_U64, },
	[DPLL_A_PIN_FREQUENCY_SUPPORTED] = { .name = "frequency-supported", .type = YNL_PT_NEST, .nest = &dpll_frequency_range_nest, },
	[DPLL_A_PIN_FREQUENCY_MIN] = { .name = "frequency-min", .type = YNL_PT_U64, },
	[DPLL_A_PIN_FREQUENCY_MAX] = { .name = "frequency-max", .type = YNL_PT_U64, },
	[DPLL_A_PIN_PRIO] = { .name = "prio", .type = YNL_PT_U32, },
	[DPLL_A_PIN_STATE] = { .name = "state", .type = YNL_PT_U32, },
	[DPLL_A_PIN_CAPABILITIES] = { .name = "capabilities", .type = YNL_PT_U32, },
	[DPLL_A_PIN_PARENT_DEVICE] = { .name = "parent-device", .type = YNL_PT_NEST, .nest = &dpll_pin_parent_device_nest, },
	[DPLL_A_PIN_PARENT_PIN] = { .name = "parent-pin", .type = YNL_PT_NEST, .nest = &dpll_pin_parent_pin_nest, },
	[DPLL_A_PIN_PHASE_ADJUST_MIN] = { .name = "phase-adjust-min", .type = YNL_PT_U32, },
	[DPLL_A_PIN_PHASE_ADJUST_MAX] = { .name = "phase-adjust-max", .type = YNL_PT_U32, },
	[DPLL_A_PIN_PHASE_ADJUST] = { .name = "phase-adjust", .type = YNL_PT_U32, },
	[DPLL_A_PIN_PHASE_OFFSET] = { .name = "phase-offset", .type = YNL_PT_U64, },
	[DPLL_A_PIN_FRACTIONAL_FREQUENCY_OFFSET] = { .name = "fractional-frequency-offset", .type = YNL_PT_UINT, },
	[DPLL_A_PIN_ESYNC_FREQUENCY] = { .name = "esync-frequency", .type = YNL_PT_U64, },
	[DPLL_A_PIN_ESYNC_FREQUENCY_SUPPORTED] = { .name = "esync-frequency-supported", .type = YNL_PT_NEST, .nest = &dpll_frequency_range_nest, },
	[DPLL_A_PIN_ESYNC_PULSE] = { .name = "esync-pulse", .type = YNL_PT_U32, },
};

const struct ynl_policy_nest dpll_pin_nest = {
	.max_attr = DPLL_A_PIN_MAX,
	.table = dpll_pin_policy,
};

/* Common nested types */
void dpll_frequency_range_free(struct dpll_frequency_range *obj)
{
}

int dpll_frequency_range_parse(struct ynl_parse_arg *yarg,
			       const struct nlattr *nested)
{
	struct dpll_frequency_range *dst = yarg->data;
	const struct nlattr *attr;

	ynl_attr_for_each_nested(attr, nested) {
		unsigned int type = ynl_attr_type(attr);

		if (type == DPLL_A_PIN_FREQUENCY_MIN) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.frequency_min = 1;
			dst->frequency_min = ynl_attr_get_u64(attr);
		} else if (type == DPLL_A_PIN_FREQUENCY_MAX) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.frequency_max = 1;
			dst->frequency_max = ynl_attr_get_u64(attr);
		}
	}

	return 0;
}

void dpll_pin_parent_device_free(struct dpll_pin_parent_device *obj)
{
}

int dpll_pin_parent_device_put(struct nlmsghdr *nlh, unsigned int attr_type,
			       struct dpll_pin_parent_device *obj)
{
	struct nlattr *nest;

	nest = ynl_attr_nest_start(nlh, attr_type);
	if (obj->_present.parent_id)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_PARENT_ID, obj->parent_id);
	if (obj->_present.direction)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_DIRECTION, obj->direction);
	if (obj->_present.prio)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_PRIO, obj->prio);
	if (obj->_present.state)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_STATE, obj->state);
	if (obj->_present.phase_offset)
		ynl_attr_put_s64(nlh, DPLL_A_PIN_PHASE_OFFSET, obj->phase_offset);
	ynl_attr_nest_end(nlh, nest);

	return 0;
}

int dpll_pin_parent_device_parse(struct ynl_parse_arg *yarg,
				 const struct nlattr *nested)
{
	struct dpll_pin_parent_device *dst = yarg->data;
	const struct nlattr *attr;

	ynl_attr_for_each_nested(attr, nested) {
		unsigned int type = ynl_attr_type(attr);

		if (type == DPLL_A_PIN_PARENT_ID) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.parent_id = 1;
			dst->parent_id = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_PIN_DIRECTION) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.direction = 1;
			dst->direction = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_PIN_PRIO) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.prio = 1;
			dst->prio = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_PIN_STATE) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.state = 1;
			dst->state = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_PIN_PHASE_OFFSET) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.phase_offset = 1;
			dst->phase_offset = ynl_attr_get_s64(attr);
		}
	}

	return 0;
}

void dpll_pin_parent_pin_free(struct dpll_pin_parent_pin *obj)
{
}

int dpll_pin_parent_pin_put(struct nlmsghdr *nlh, unsigned int attr_type,
			    struct dpll_pin_parent_pin *obj)
{
	struct nlattr *nest;

	nest = ynl_attr_nest_start(nlh, attr_type);
	if (obj->_present.parent_id)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_PARENT_ID, obj->parent_id);
	if (obj->_present.state)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_STATE, obj->state);
	ynl_attr_nest_end(nlh, nest);

	return 0;
}

int dpll_pin_parent_pin_parse(struct ynl_parse_arg *yarg,
			      const struct nlattr *nested)
{
	struct dpll_pin_parent_pin *dst = yarg->data;
	const struct nlattr *attr;

	ynl_attr_for_each_nested(attr, nested) {
		unsigned int type = ynl_attr_type(attr);

		if (type == DPLL_A_PIN_PARENT_ID) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.parent_id = 1;
			dst->parent_id = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_PIN_STATE) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.state = 1;
			dst->state = ynl_attr_get_u32(attr);
		}
	}

	return 0;
}

/* ============== DPLL_CMD_DEVICE_ID_GET ============== */
/* DPLL_CMD_DEVICE_ID_GET - do */
void dpll_device_id_get_req_free(struct dpll_device_id_get_req *req)
{
	free(req->module_name);
	free(req);
}

void dpll_device_id_get_rsp_free(struct dpll_device_id_get_rsp *rsp)
{
	free(rsp);
}

int dpll_device_id_get_rsp_parse(const struct nlmsghdr *nlh,
				 struct ynl_parse_arg *yarg)
{
	struct dpll_device_id_get_rsp *dst;
	const struct nlattr *attr;

	dst = yarg->data;

	ynl_attr_for_each(attr, nlh, yarg->ys->family->hdr_len) {
		unsigned int type = ynl_attr_type(attr);

		if (type == DPLL_A_ID) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.id = 1;
			dst->id = ynl_attr_get_u32(attr);
		}
	}

	return YNL_PARSE_CB_OK;
}

struct dpll_device_id_get_rsp *
dpll_device_id_get(struct ynl_sock *ys, struct dpll_device_id_get_req *req)
{
	struct ynl_req_state yrs = { .yarg = { .ys = ys, }, };
	struct dpll_device_id_get_rsp *rsp;
	struct nlmsghdr *nlh;
	int err;

	nlh = ynl_gemsg_start_req(ys, ys->family_id, DPLL_CMD_DEVICE_ID_GET, 1);
	ys->req_policy = &dpll_nest;
	yrs.yarg.rsp_policy = &dpll_nest;

	if (req->_present.module_name_len)
		ynl_attr_put_str(nlh, DPLL_A_MODULE_NAME, req->module_name);
	if (req->_present.clock_id)
		ynl_attr_put_u64(nlh, DPLL_A_CLOCK_ID, req->clock_id);
	if (req->_present.type)
		ynl_attr_put_u32(nlh, DPLL_A_TYPE, req->type);

	rsp = calloc(1, sizeof(*rsp));
	yrs.yarg.data = rsp;
	yrs.cb = dpll_device_id_get_rsp_parse;
	yrs.rsp_cmd = DPLL_CMD_DEVICE_ID_GET;

	err = ynl_exec(ys, nlh, &yrs);
	if (err < 0)
		goto err_free;

	return rsp;

err_free:
	dpll_device_id_get_rsp_free(rsp);
	return NULL;
}

/* ============== DPLL_CMD_DEVICE_GET ============== */
/* DPLL_CMD_DEVICE_GET - do */
void dpll_device_get_req_free(struct dpll_device_get_req *req)
{
	free(req);
}

void dpll_device_get_rsp_free(struct dpll_device_get_rsp *rsp)
{
	free(rsp->module_name);
	free(rsp->mode_supported);
	free(rsp);
}

int dpll_device_get_rsp_parse(const struct nlmsghdr *nlh,
			      struct ynl_parse_arg *yarg)
{
	unsigned int n_mode_supported = 0;
	struct dpll_device_get_rsp *dst;
	const struct nlattr *attr;
	int i;

	dst = yarg->data;

	if (dst->mode_supported)
		return ynl_error_parse(yarg, "attribute already present (dpll.mode-supported)");

	ynl_attr_for_each(attr, nlh, yarg->ys->family->hdr_len) {
		unsigned int type = ynl_attr_type(attr);

		if (type == DPLL_A_ID) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.id = 1;
			dst->id = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_MODULE_NAME) {
			unsigned int len;

			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;

			len = strnlen(ynl_attr_get_str(attr), ynl_attr_data_len(attr));
			dst->_present.module_name_len = len;
			dst->module_name = malloc(len + 1);
			memcpy(dst->module_name, ynl_attr_get_str(attr), len);
			dst->module_name[len] = 0;
		} else if (type == DPLL_A_MODE) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.mode = 1;
			dst->mode = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_MODE_SUPPORTED) {
			n_mode_supported++;
		} else if (type == DPLL_A_LOCK_STATUS) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.lock_status = 1;
			dst->lock_status = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_LOCK_STATUS_ERROR) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.lock_status_error = 1;
			dst->lock_status_error = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_TEMP) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.temp = 1;
			dst->temp = ynl_attr_get_s32(attr);
		} else if (type == DPLL_A_CLOCK_ID) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.clock_id = 1;
			dst->clock_id = ynl_attr_get_u64(attr);
		} else if (type == DPLL_A_TYPE) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.type = 1;
			dst->type = ynl_attr_get_u32(attr);
		}
	}

	if (n_mode_supported) {
		dst->mode_supported = calloc(n_mode_supported, sizeof(*dst->mode_supported));
		dst->n_mode_supported = n_mode_supported;
		i = 0;
		ynl_attr_for_each(attr, nlh, yarg->ys->family->hdr_len) {
			if (ynl_attr_type(attr) == DPLL_A_MODE_SUPPORTED) {
				dst->mode_supported[i] = ynl_attr_get_u32(attr);
				i++;
			}
		}
	}

	return YNL_PARSE_CB_OK;
}

struct dpll_device_get_rsp *
dpll_device_get(struct ynl_sock *ys, struct dpll_device_get_req *req)
{
	struct ynl_req_state yrs = { .yarg = { .ys = ys, }, };
	struct dpll_device_get_rsp *rsp;
	struct nlmsghdr *nlh;
	int err;

	nlh = ynl_gemsg_start_req(ys, ys->family_id, DPLL_CMD_DEVICE_GET, 1);
	ys->req_policy = &dpll_nest;
	yrs.yarg.rsp_policy = &dpll_nest;

	if (req->_present.id)
		ynl_attr_put_u32(nlh, DPLL_A_ID, req->id);

	rsp = calloc(1, sizeof(*rsp));
	yrs.yarg.data = rsp;
	yrs.cb = dpll_device_get_rsp_parse;
	yrs.rsp_cmd = DPLL_CMD_DEVICE_GET;

	err = ynl_exec(ys, nlh, &yrs);
	if (err < 0)
		goto err_free;

	return rsp;

err_free:
	dpll_device_get_rsp_free(rsp);
	return NULL;
}

/* DPLL_CMD_DEVICE_GET - dump */
void dpll_device_get_list_free(struct dpll_device_get_list *rsp)
{
	struct dpll_device_get_list *next = rsp;

	while ((void *)next != YNL_LIST_END) {
		rsp = next;
		next = rsp->next;

		free(rsp->obj.module_name);
		free(rsp->obj.mode_supported);
		free(rsp);
	}
}

struct dpll_device_get_list *dpll_device_get_dump(struct ynl_sock *ys)
{
	struct ynl_dump_state yds = {};
	struct nlmsghdr *nlh;
	int err;

	yds.yarg.ys = ys;
	yds.yarg.rsp_policy = &dpll_nest;
	yds.yarg.data = NULL;
	yds.alloc_sz = sizeof(struct dpll_device_get_list);
	yds.cb = dpll_device_get_rsp_parse;
	yds.rsp_cmd = DPLL_CMD_DEVICE_GET;

	nlh = ynl_gemsg_start_dump(ys, ys->family_id, DPLL_CMD_DEVICE_GET, 1);

	err = ynl_exec_dump(ys, nlh, &yds);
	if (err < 0)
		goto free_list;

	return yds.first;

free_list:
	dpll_device_get_list_free(yds.first);
	return NULL;
}

/* DPLL_CMD_DEVICE_GET - notify */
void dpll_device_get_ntf_free(struct dpll_device_get_ntf *rsp)
{
	free(rsp->obj.module_name);
	free(rsp->obj.mode_supported);
	free(rsp);
}

/* ============== DPLL_CMD_DEVICE_SET ============== */
/* DPLL_CMD_DEVICE_SET - do */
void dpll_device_set_req_free(struct dpll_device_set_req *req)
{
	free(req);
}

int dpll_device_set(struct ynl_sock *ys, struct dpll_device_set_req *req)
{
	struct ynl_req_state yrs = { .yarg = { .ys = ys, }, };
	struct nlmsghdr *nlh;
	int err;

	nlh = ynl_gemsg_start_req(ys, ys->family_id, DPLL_CMD_DEVICE_SET, 1);
	ys->req_policy = &dpll_nest;

	if (req->_present.id)
		ynl_attr_put_u32(nlh, DPLL_A_ID, req->id);

	err = ynl_exec(ys, nlh, &yrs);
	if (err < 0)
		return -1;

	return 0;
}

/* ============== DPLL_CMD_PIN_ID_GET ============== */
/* DPLL_CMD_PIN_ID_GET - do */
void dpll_pin_id_get_req_free(struct dpll_pin_id_get_req *req)
{
	free(req->module_name);
	free(req->board_label);
	free(req->panel_label);
	free(req->package_label);
	free(req);
}

void dpll_pin_id_get_rsp_free(struct dpll_pin_id_get_rsp *rsp)
{
	free(rsp);
}

int dpll_pin_id_get_rsp_parse(const struct nlmsghdr *nlh,
			      struct ynl_parse_arg *yarg)
{
	struct dpll_pin_id_get_rsp *dst;
	const struct nlattr *attr;

	dst = yarg->data;

	ynl_attr_for_each(attr, nlh, yarg->ys->family->hdr_len) {
		unsigned int type = ynl_attr_type(attr);

		if (type == DPLL_A_PIN_ID) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.id = 1;
			dst->id = ynl_attr_get_u32(attr);
		}
	}

	return YNL_PARSE_CB_OK;
}

struct dpll_pin_id_get_rsp *
dpll_pin_id_get(struct ynl_sock *ys, struct dpll_pin_id_get_req *req)
{
	struct ynl_req_state yrs = { .yarg = { .ys = ys, }, };
	struct dpll_pin_id_get_rsp *rsp;
	struct nlmsghdr *nlh;
	int err;

	nlh = ynl_gemsg_start_req(ys, ys->family_id, DPLL_CMD_PIN_ID_GET, 1);
	ys->req_policy = &dpll_pin_nest;
	yrs.yarg.rsp_policy = &dpll_pin_nest;

	if (req->_present.module_name_len)
		ynl_attr_put_str(nlh, DPLL_A_PIN_MODULE_NAME, req->module_name);
	if (req->_present.clock_id)
		ynl_attr_put_u64(nlh, DPLL_A_PIN_CLOCK_ID, req->clock_id);
	if (req->_present.board_label_len)
		ynl_attr_put_str(nlh, DPLL_A_PIN_BOARD_LABEL, req->board_label);
	if (req->_present.panel_label_len)
		ynl_attr_put_str(nlh, DPLL_A_PIN_PANEL_LABEL, req->panel_label);
	if (req->_present.package_label_len)
		ynl_attr_put_str(nlh, DPLL_A_PIN_PACKAGE_LABEL, req->package_label);
	if (req->_present.type)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_TYPE, req->type);

	rsp = calloc(1, sizeof(*rsp));
	yrs.yarg.data = rsp;
	yrs.cb = dpll_pin_id_get_rsp_parse;
	yrs.rsp_cmd = DPLL_CMD_PIN_ID_GET;

	err = ynl_exec(ys, nlh, &yrs);
	if (err < 0)
		goto err_free;

	return rsp;

err_free:
	dpll_pin_id_get_rsp_free(rsp);
	return NULL;
}

/* ============== DPLL_CMD_PIN_GET ============== */
/* DPLL_CMD_PIN_GET - do */
void dpll_pin_get_req_free(struct dpll_pin_get_req *req)
{
	free(req);
}

void dpll_pin_get_rsp_free(struct dpll_pin_get_rsp *rsp)
{
	unsigned int i;

	free(rsp->board_label);
	free(rsp->panel_label);
	free(rsp->package_label);
	for (i = 0; i < rsp->n_frequency_supported; i++)
		dpll_frequency_range_free(&rsp->frequency_supported[i]);
	free(rsp->frequency_supported);
	for (i = 0; i < rsp->n_parent_device; i++)
		dpll_pin_parent_device_free(&rsp->parent_device[i]);
	free(rsp->parent_device);
	for (i = 0; i < rsp->n_parent_pin; i++)
		dpll_pin_parent_pin_free(&rsp->parent_pin[i]);
	free(rsp->parent_pin);
	for (i = 0; i < rsp->n_esync_frequency_supported; i++)
		dpll_frequency_range_free(&rsp->esync_frequency_supported[i]);
	free(rsp->esync_frequency_supported);
	free(rsp);
}

int dpll_pin_get_rsp_parse(const struct nlmsghdr *nlh,
			   struct ynl_parse_arg *yarg)
{
	unsigned int n_esync_frequency_supported = 0;
	unsigned int n_frequency_supported = 0;
	unsigned int n_parent_device = 0;
	unsigned int n_parent_pin = 0;
	struct dpll_pin_get_rsp *dst;
	const struct nlattr *attr;
	struct ynl_parse_arg parg;
	int i;

	dst = yarg->data;
	parg.ys = yarg->ys;

	if (dst->esync_frequency_supported)
		return ynl_error_parse(yarg, "attribute already present (pin.esync-frequency-supported)");
	if (dst->frequency_supported)
		return ynl_error_parse(yarg, "attribute already present (pin.frequency-supported)");
	if (dst->parent_device)
		return ynl_error_parse(yarg, "attribute already present (pin.parent-device)");
	if (dst->parent_pin)
		return ynl_error_parse(yarg, "attribute already present (pin.parent-pin)");

	ynl_attr_for_each(attr, nlh, yarg->ys->family->hdr_len) {
		unsigned int type = ynl_attr_type(attr);

		if (type == DPLL_A_PIN_ID) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.id = 1;
			dst->id = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_PIN_BOARD_LABEL) {
			unsigned int len;

			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;

			len = strnlen(ynl_attr_get_str(attr), ynl_attr_data_len(attr));
			dst->_present.board_label_len = len;
			dst->board_label = malloc(len + 1);
			memcpy(dst->board_label, ynl_attr_get_str(attr), len);
			dst->board_label[len] = 0;
		} else if (type == DPLL_A_PIN_PANEL_LABEL) {
			unsigned int len;

			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;

			len = strnlen(ynl_attr_get_str(attr), ynl_attr_data_len(attr));
			dst->_present.panel_label_len = len;
			dst->panel_label = malloc(len + 1);
			memcpy(dst->panel_label, ynl_attr_get_str(attr), len);
			dst->panel_label[len] = 0;
		} else if (type == DPLL_A_PIN_PACKAGE_LABEL) {
			unsigned int len;

			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;

			len = strnlen(ynl_attr_get_str(attr), ynl_attr_data_len(attr));
			dst->_present.package_label_len = len;
			dst->package_label = malloc(len + 1);
			memcpy(dst->package_label, ynl_attr_get_str(attr), len);
			dst->package_label[len] = 0;
		} else if (type == DPLL_A_PIN_TYPE) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.type = 1;
			dst->type = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_PIN_FREQUENCY) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.frequency = 1;
			dst->frequency = ynl_attr_get_u64(attr);
		} else if (type == DPLL_A_PIN_FREQUENCY_SUPPORTED) {
			n_frequency_supported++;
		} else if (type == DPLL_A_PIN_CAPABILITIES) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.capabilities = 1;
			dst->capabilities = ynl_attr_get_u32(attr);
		} else if (type == DPLL_A_PIN_PARENT_DEVICE) {
			n_parent_device++;
		} else if (type == DPLL_A_PIN_PARENT_PIN) {
			n_parent_pin++;
		} else if (type == DPLL_A_PIN_PHASE_ADJUST_MIN) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.phase_adjust_min = 1;
			dst->phase_adjust_min = ynl_attr_get_s32(attr);
		} else if (type == DPLL_A_PIN_PHASE_ADJUST_MAX) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.phase_adjust_max = 1;
			dst->phase_adjust_max = ynl_attr_get_s32(attr);
		} else if (type == DPLL_A_PIN_PHASE_ADJUST) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.phase_adjust = 1;
			dst->phase_adjust = ynl_attr_get_s32(attr);
		} else if (type == DPLL_A_PIN_FRACTIONAL_FREQUENCY_OFFSET) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.fractional_frequency_offset = 1;
			dst->fractional_frequency_offset = ynl_attr_get_sint(attr);
		} else if (type == DPLL_A_PIN_ESYNC_FREQUENCY) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.esync_frequency = 1;
			dst->esync_frequency = ynl_attr_get_u64(attr);
		} else if (type == DPLL_A_PIN_ESYNC_FREQUENCY_SUPPORTED) {
			n_esync_frequency_supported++;
		} else if (type == DPLL_A_PIN_ESYNC_PULSE) {
			if (ynl_attr_validate(yarg, attr))
				return YNL_PARSE_CB_ERROR;
			dst->_present.esync_pulse = 1;
			dst->esync_pulse = ynl_attr_get_u32(attr);
		}
	}

	if (n_esync_frequency_supported) {
		dst->esync_frequency_supported = calloc(n_esync_frequency_supported, sizeof(*dst->esync_frequency_supported));
		dst->n_esync_frequency_supported = n_esync_frequency_supported;
		i = 0;
		parg.rsp_policy = &dpll_frequency_range_nest;
		ynl_attr_for_each(attr, nlh, yarg->ys->family->hdr_len) {
			if (ynl_attr_type(attr) == DPLL_A_PIN_ESYNC_FREQUENCY_SUPPORTED) {
				parg.data = &dst->esync_frequency_supported[i];
				if (dpll_frequency_range_parse(&parg, attr))
					return YNL_PARSE_CB_ERROR;
				i++;
			}
		}
	}
	if (n_frequency_supported) {
		dst->frequency_supported = calloc(n_frequency_supported, sizeof(*dst->frequency_supported));
		dst->n_frequency_supported = n_frequency_supported;
		i = 0;
		parg.rsp_policy = &dpll_frequency_range_nest;
		ynl_attr_for_each(attr, nlh, yarg->ys->family->hdr_len) {
			if (ynl_attr_type(attr) == DPLL_A_PIN_FREQUENCY_SUPPORTED) {
				parg.data = &dst->frequency_supported[i];
				if (dpll_frequency_range_parse(&parg, attr))
					return YNL_PARSE_CB_ERROR;
				i++;
			}
		}
	}
	if (n_parent_device) {
		dst->parent_device = calloc(n_parent_device, sizeof(*dst->parent_device));
		dst->n_parent_device = n_parent_device;
		i = 0;
		parg.rsp_policy = &dpll_pin_parent_device_nest;
		ynl_attr_for_each(attr, nlh, yarg->ys->family->hdr_len) {
			if (ynl_attr_type(attr) == DPLL_A_PIN_PARENT_DEVICE) {
				parg.data = &dst->parent_device[i];
				if (dpll_pin_parent_device_parse(&parg, attr))
					return YNL_PARSE_CB_ERROR;
				i++;
			}
		}
	}
	if (n_parent_pin) {
		dst->parent_pin = calloc(n_parent_pin, sizeof(*dst->parent_pin));
		dst->n_parent_pin = n_parent_pin;
		i = 0;
		parg.rsp_policy = &dpll_pin_parent_pin_nest;
		ynl_attr_for_each(attr, nlh, yarg->ys->family->hdr_len) {
			if (ynl_attr_type(attr) == DPLL_A_PIN_PARENT_PIN) {
				parg.data = &dst->parent_pin[i];
				if (dpll_pin_parent_pin_parse(&parg, attr))
					return YNL_PARSE_CB_ERROR;
				i++;
			}
		}
	}

	return YNL_PARSE_CB_OK;
}

struct dpll_pin_get_rsp *
dpll_pin_get(struct ynl_sock *ys, struct dpll_pin_get_req *req)
{
	struct ynl_req_state yrs = { .yarg = { .ys = ys, }, };
	struct dpll_pin_get_rsp *rsp;
	struct nlmsghdr *nlh;
	int err;

	nlh = ynl_gemsg_start_req(ys, ys->family_id, DPLL_CMD_PIN_GET, 1);
	ys->req_policy = &dpll_pin_nest;
	yrs.yarg.rsp_policy = &dpll_pin_nest;

	if (req->_present.id)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_ID, req->id);

	rsp = calloc(1, sizeof(*rsp));
	yrs.yarg.data = rsp;
	yrs.cb = dpll_pin_get_rsp_parse;
	yrs.rsp_cmd = DPLL_CMD_PIN_GET;

	err = ynl_exec(ys, nlh, &yrs);
	if (err < 0)
		goto err_free;

	return rsp;

err_free:
	dpll_pin_get_rsp_free(rsp);
	return NULL;
}

/* DPLL_CMD_PIN_GET - dump */
void dpll_pin_get_req_dump_free(struct dpll_pin_get_req_dump *req)
{
	free(req);
}

void dpll_pin_get_list_free(struct dpll_pin_get_list *rsp)
{
	struct dpll_pin_get_list *next = rsp;

	while ((void *)next != YNL_LIST_END) {
		unsigned int i;

		rsp = next;
		next = rsp->next;

		free(rsp->obj.board_label);
		free(rsp->obj.panel_label);
		free(rsp->obj.package_label);
		for (i = 0; i < rsp->obj.n_frequency_supported; i++)
			dpll_frequency_range_free(&rsp->obj.frequency_supported[i]);
		free(rsp->obj.frequency_supported);
		for (i = 0; i < rsp->obj.n_parent_device; i++)
			dpll_pin_parent_device_free(&rsp->obj.parent_device[i]);
		free(rsp->obj.parent_device);
		for (i = 0; i < rsp->obj.n_parent_pin; i++)
			dpll_pin_parent_pin_free(&rsp->obj.parent_pin[i]);
		free(rsp->obj.parent_pin);
		for (i = 0; i < rsp->obj.n_esync_frequency_supported; i++)
			dpll_frequency_range_free(&rsp->obj.esync_frequency_supported[i]);
		free(rsp->obj.esync_frequency_supported);
		free(rsp);
	}
}

struct dpll_pin_get_list *
dpll_pin_get_dump(struct ynl_sock *ys, struct dpll_pin_get_req_dump *req)
{
	struct ynl_dump_state yds = {};
	struct nlmsghdr *nlh;
	int err;

	yds.yarg.ys = ys;
	yds.yarg.rsp_policy = &dpll_pin_nest;
	yds.yarg.data = NULL;
	yds.alloc_sz = sizeof(struct dpll_pin_get_list);
	yds.cb = dpll_pin_get_rsp_parse;
	yds.rsp_cmd = DPLL_CMD_PIN_GET;

	nlh = ynl_gemsg_start_dump(ys, ys->family_id, DPLL_CMD_PIN_GET, 1);
	ys->req_policy = &dpll_pin_nest;

	if (req->_present.id)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_ID, req->id);

	err = ynl_exec_dump(ys, nlh, &yds);
	if (err < 0)
		goto free_list;

	return yds.first;

free_list:
	dpll_pin_get_list_free(yds.first);
	return NULL;
}

/* DPLL_CMD_PIN_GET - notify */
void dpll_pin_get_ntf_free(struct dpll_pin_get_ntf *rsp)
{
	unsigned int i;

	free(rsp->obj.board_label);
	free(rsp->obj.panel_label);
	free(rsp->obj.package_label);
	for (i = 0; i < rsp->obj.n_frequency_supported; i++)
		dpll_frequency_range_free(&rsp->obj.frequency_supported[i]);
	free(rsp->obj.frequency_supported);
	for (i = 0; i < rsp->obj.n_parent_device; i++)
		dpll_pin_parent_device_free(&rsp->obj.parent_device[i]);
	free(rsp->obj.parent_device);
	for (i = 0; i < rsp->obj.n_parent_pin; i++)
		dpll_pin_parent_pin_free(&rsp->obj.parent_pin[i]);
	free(rsp->obj.parent_pin);
	for (i = 0; i < rsp->obj.n_esync_frequency_supported; i++)
		dpll_frequency_range_free(&rsp->obj.esync_frequency_supported[i]);
	free(rsp->obj.esync_frequency_supported);
	free(rsp);
}

/* ============== DPLL_CMD_PIN_SET ============== */
/* DPLL_CMD_PIN_SET - do */
void dpll_pin_set_req_free(struct dpll_pin_set_req *req)
{
	unsigned int i;

	for (i = 0; i < req->n_parent_device; i++)
		dpll_pin_parent_device_free(&req->parent_device[i]);
	free(req->parent_device);
	for (i = 0; i < req->n_parent_pin; i++)
		dpll_pin_parent_pin_free(&req->parent_pin[i]);
	free(req->parent_pin);
	free(req);
}

int dpll_pin_set(struct ynl_sock *ys, struct dpll_pin_set_req *req)
{
	struct ynl_req_state yrs = { .yarg = { .ys = ys, }, };
	struct nlmsghdr *nlh;
	int err;

	nlh = ynl_gemsg_start_req(ys, ys->family_id, DPLL_CMD_PIN_SET, 1);
	ys->req_policy = &dpll_pin_nest;

	if (req->_present.id)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_ID, req->id);
	if (req->_present.frequency)
		ynl_attr_put_u64(nlh, DPLL_A_PIN_FREQUENCY, req->frequency);
	if (req->_present.direction)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_DIRECTION, req->direction);
	if (req->_present.prio)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_PRIO, req->prio);
	if (req->_present.state)
		ynl_attr_put_u32(nlh, DPLL_A_PIN_STATE, req->state);
	for (unsigned int i = 0; i < req->n_parent_device; i++)
		dpll_pin_parent_device_put(nlh, DPLL_A_PIN_PARENT_DEVICE, &req->parent_device[i]);
	for (unsigned int i = 0; i < req->n_parent_pin; i++)
		dpll_pin_parent_pin_put(nlh, DPLL_A_PIN_PARENT_PIN, &req->parent_pin[i]);
	if (req->_present.phase_adjust)
		ynl_attr_put_s32(nlh, DPLL_A_PIN_PHASE_ADJUST, req->phase_adjust);
	if (req->_present.esync_frequency)
		ynl_attr_put_u64(nlh, DPLL_A_PIN_ESYNC_FREQUENCY, req->esync_frequency);

	err = ynl_exec(ys, nlh, &yrs);
	if (err < 0)
		return -1;

	return 0;
}

static const struct ynl_ntf_info dpll_ntf_info[] =  {
	[DPLL_CMD_DEVICE_CREATE_NTF] =  {
		.alloc_sz	= sizeof(struct dpll_device_get_ntf),
		.cb		= dpll_device_get_rsp_parse,
		.policy		= &dpll_nest,
		.free		= (void *)dpll_device_get_ntf_free,
	},
	[DPLL_CMD_DEVICE_DELETE_NTF] =  {
		.alloc_sz	= sizeof(struct dpll_device_get_ntf),
		.cb		= dpll_device_get_rsp_parse,
		.policy		= &dpll_nest,
		.free		= (void *)dpll_device_get_ntf_free,
	},
	[DPLL_CMD_DEVICE_CHANGE_NTF] =  {
		.alloc_sz	= sizeof(struct dpll_device_get_ntf),
		.cb		= dpll_device_get_rsp_parse,
		.policy		= &dpll_nest,
		.free		= (void *)dpll_device_get_ntf_free,
	},
	[DPLL_CMD_PIN_CREATE_NTF] =  {
		.alloc_sz	= sizeof(struct dpll_pin_get_ntf),
		.cb		= dpll_pin_get_rsp_parse,
		.policy		= &dpll_pin_nest,
		.free		= (void *)dpll_pin_get_ntf_free,
	},
	[DPLL_CMD_PIN_DELETE_NTF] =  {
		.alloc_sz	= sizeof(struct dpll_pin_get_ntf),
		.cb		= dpll_pin_get_rsp_parse,
		.policy		= &dpll_pin_nest,
		.free		= (void *)dpll_pin_get_ntf_free,
	},
	[DPLL_CMD_PIN_CHANGE_NTF] =  {
		.alloc_sz	= sizeof(struct dpll_pin_get_ntf),
		.cb		= dpll_pin_get_rsp_parse,
		.policy		= &dpll_pin_nest,
		.free		= (void *)dpll_pin_get_ntf_free,
	},
};

const struct ynl_family ynl_dpll_family =  {
	.name		= "dpll",
	.hdr_len	= sizeof(struct genlmsghdr),
	.ntf_info	= dpll_ntf_info,
	.ntf_info_size	= YNL_ARRAY_SIZE(dpll_ntf_info),
};
