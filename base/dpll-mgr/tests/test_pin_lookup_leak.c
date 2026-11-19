/*
 * test_pin_lookup_leak.c unit test
 *
 * The pin read/set helpers in dpll_utils.c (dpll_pin_get_priority,
 * dpll_pin_set_state, dpll_pin_set_priority, dpll_pin_set_phase_adjust) look
 * the pin up with a full kernel pin-get dump via
 * dpll_one_pin_by_package_label(), and dpll_get_device_state_and_connected_pin()
 * takes its own dump on every DPLL change event. Each dump is a heap list. Both
 * used to be leaked on every call, so dpll-mgr RSS grew on every source
 * failover without bound.
 *
 * This test replaces the netlink dump with a mock that tracks how many list
 * nodes are alive, then asserts after each public call that every node it
 * allocated has been freed, and that the functional results are unchanged:
 *   - hit / miss / empty-dump (sentinel) / failed-dump (NULL) lookups
 *   - same-state short-circuit, state change, priority 15 -> disconnect path,
 *     priority change, missing parent device, phase adjust
 *   - dpll_get_device_state_and_connected_pin (found / none connected /
 *     empty dump) frees both the pin dump and the device response
 *   - dpll_find_device_id_by_type (present / absent type / last device skipped
 *     by module name / empty dump / failed dump) stops at the list end and frees
 *     the device dump
 *   - a long loop of calls leaves zero live nodes
 *
 * dpll_utils.c is included directly; dpll_pin_get_dump / dpll_pin_set /
 * dpll_pin_get_list_free are redirected to the mocks via macros (the real
 * dpll_pin_get_list_free still does the actual freeing). No framework;
 * non-zero exit = failed assertion.
 *
 * Build/run:  make -f Makefile.test test
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define UNIT_TEST_BUILD 1

#include <ynl/ynl.h>
#include "../ynl/dpll-user.h"

/* --- mock state ------------------------------------------------------------ */
enum { DUMP_NORMAL = 0, DUMP_EMPTY = 1, DUMP_FAIL = 2 };

static int g_dump_mode   = DUMP_NORMAL;
static long g_dump_calls = 0;     /* dump invocations */
static long g_free_calls = 0;     /* list frees */
static long g_live_nodes = 0;     /* allocated minus freed list nodes */

static int  g_set_calls  = 0;
static __u32 g_set_id    = 0;
static __u32 g_set_parent = 0;
static int  g_set_state  = -1;
static int  g_set_prio   = -1;
static int  g_set_has_state = 0;
static int  g_set_has_prio  = 0;
static __s32 g_set_phase = 0;
static int  g_set_ret    = 0;

#define TEST_REF4P_ID 10
#define TEST_SDP0_ID  11
#define TEST_OUT0P_ID 12
#define TEST_EEC_DEV  0
#define TEST_PPS_DEV  1

static struct dpll_pin_get_list *mk_node(const char *label, __u32 id,
					 int eec_state, int eec_prio,
					 int pps_state, int pps_prio)
{
	struct dpll_pin_get_list *n = calloc(1, sizeof(*n));
	struct dpll_pin_parent_device *pd = calloc(2, sizeof(*pd));

	assert(n && pd);
	g_live_nodes++;
	n->obj.package_label = strdup(label);
	n->obj._present.id = 1;
	n->obj.id = id;
	n->obj._present.phase_adjust = 1;
	n->obj.phase_adjust = 77;
	n->obj.n_parent_device = 2;
	n->obj.parent_device = pd;
	pd[0]._present.parent_id = pd[0]._present.state = pd[0]._present.prio = 1;
	pd[0].parent_id = TEST_EEC_DEV;
	pd[0].state = eec_state;
	pd[0].prio = eec_prio;
	pd[1]._present.parent_id = pd[1]._present.state = pd[1]._present.prio = 1;
	pd[1].parent_id = TEST_PPS_DEV;
	pd[1].state = pps_state;
	pd[1].prio = pps_prio;
	return n;
}

/* Mirrors the real YNL dump: node list terminated by YNL_LIST_END, empty dump
 * is YNL_LIST_END itself, failure is NULL. */
static struct dpll_pin_get_list *test_pin_get_dump(struct ynl_sock *ys,
						   struct dpll_pin_get_req_dump *req)
{
	struct dpll_pin_get_list *a, *b, *c;

	(void)ys; (void)req;
	g_dump_calls++;
	if (g_dump_mode == DUMP_FAIL)
		return NULL;
	if (g_dump_mode == DUMP_EMPTY)
		return (struct dpll_pin_get_list *)YNL_LIST_END;

	a = mk_node("REF4P", TEST_REF4P_ID,
		    DPLL_PIN_STATE_CONNECTED, 0, DPLL_PIN_STATE_SELECTABLE, 3);
	b = mk_node("SDP0_REF0N", TEST_SDP0_ID,
		    DPLL_PIN_STATE_DISCONNECTED, 15, DPLL_PIN_STATE_SELECTABLE, 12);
	c = mk_node("OUT0P", TEST_OUT0P_ID,
		    DPLL_PIN_STATE_DISCONNECTED, 15, DPLL_PIN_STATE_DISCONNECTED, 15);
	a->next = b;
	b->next = c;
	c->next = (struct dpll_pin_get_list *)YNL_LIST_END;
	return a;
}

/* Counts the nodes being released, then hands off to the real free. The real
 * dpll_pin_get_list_free() dereferences a NULL head, so a NULL here is a bug. */
static void test_list_free(struct dpll_pin_get_list *l)
{
	struct dpll_pin_get_list *p;

	assert(l != NULL);
	g_free_calls++;
	for (p = l; p && (void *)p != (void *)YNL_LIST_END; p = p->next)
		g_live_nodes--;
	dpll_pin_get_list_free(l);
}

static int test_pin_set(struct ynl_sock *ys, struct dpll_pin_set_req *req)
{
	(void)ys;
	g_set_calls++;
	g_set_id = req->id;
	if (req->n_parent_device && req->parent_device) {
		g_set_parent    = req->parent_device->parent_id;
		g_set_has_state = req->parent_device->_present.state;
		g_set_has_prio  = req->parent_device->_present.prio;
		g_set_state     = req->parent_device->state;
		g_set_prio      = req->parent_device->prio;
	}
	g_set_phase = req->phase_adjust;
	return g_set_ret;
}

static int g_dev_lock = DPLL_LOCK_STATUS_LOCKED_HO_ACQ;
static long g_dev_live = 0;

static struct dpll_device_get_rsp *test_device_get(struct ynl_sock *ys,
						   struct dpll_device_get_req *req)
{
	struct dpll_device_get_rsp *r = calloc(1, sizeof(*r));

	(void)ys;
	assert(r);
	g_dev_live++;
	r->_present.id = 1;
	r->id = req->id;
	r->_present.lock_status = 1;
	r->lock_status = g_dev_lock;
	return r;
}

static void test_device_rsp_free(struct dpll_device_get_rsp *r)
{
	g_dev_live--;
	dpll_device_get_rsp_free(r);
}

/* Device dump mock for dpll_find_device_id_by_type(): one device whose type and
 * module name the test sets, an empty dump (YNL_LIST_END), or a failed dump. */
enum { DEV_ONE = 0, DEV_EMPTY = 1, DEV_FAIL = 2 };
static int g_dev_dump_mode = DEV_ONE;
static int g_dev_type = DPLL_TYPE_PPS;
static const char *g_dev_module = "zl3073x";
static long g_dev_list_live = 0;

static struct dpll_device_get_list *test_device_get_dump(struct ynl_sock *ys)
{
	struct dpll_device_get_list *n;

	(void)ys;
	if (g_dev_dump_mode == DEV_FAIL)
		return NULL;
	if (g_dev_dump_mode == DEV_EMPTY)
		return (struct dpll_device_get_list *)YNL_LIST_END;
	n = calloc(1, sizeof(*n));
	assert(n);
	g_dev_list_live++;
	n->obj._present.id = 1;
	n->obj.id = 1;
	n->obj._present.type = 1;
	n->obj.type = g_dev_type;
	n->obj.module_name = strdup(g_dev_module);
	n->obj._present.module_name_len = strlen(g_dev_module);
	n->next = (struct dpll_device_get_list *)YNL_LIST_END;
	return n;
}

static void test_dev_list_free(struct dpll_device_get_list *l)
{
	struct dpll_device_get_list *p;

	assert(l != NULL);
	for (p = l; (void *)p != (void *)YNL_LIST_END; p = p->next)
		g_dev_list_live--;
	dpll_device_get_list_free(l);
}

#define dpll_device_get_dump     test_device_get_dump
#define dpll_device_get_list_free test_dev_list_free
#define dpll_device_get          test_device_get
#define dpll_device_get_rsp_free test_device_rsp_free
#define dpll_pin_get_dump       test_pin_get_dump
#define dpll_pin_set            test_pin_set
#define dpll_pin_get_list_free  test_list_free

#include "../src/dpll_utils.c"

/* Logging globals normally defined by the daemon (declared in hdr/log.h). */
FILE *g_log_file = NULL;
LogLevel g_log_level = DPLL_LOG_LEVEL_ERROR;

#undef dpll_pin_get_dump
#undef dpll_device_get
#undef dpll_device_get_rsp_free
#undef dpll_device_get_dump
#undef dpll_device_get_list_free
#undef dpll_pin_set
#undef dpll_pin_get_list_free

/* --- helpers --------------------------------------------------------------- */
static void reset(void)
{
	g_dump_mode = DUMP_NORMAL;
	g_set_calls = 0; g_set_id = 0; g_set_parent = 0;
	g_set_state = -1; g_set_prio = -1;
	g_set_has_state = g_set_has_prio = 0;
	g_set_phase = 0; g_set_ret = 0;
	g_dump_calls = g_free_calls = 0;
}

/* Every dump a call made must have been freed, and no node may be alive. */
#define ASSERT_NO_LEAK(tag) do {                                              \
	if (g_live_nodes != 0) {                                              \
		fprintf(stderr, "FAIL %s: %ld list nodes leaked (dumps=%ld "  \
			"frees=%ld)\n", tag, g_live_nodes, g_dump_calls,      \
			g_free_calls);                                        \
		exit(1);                                                      \
	}                                                                     \
	printf("ok   %-44s dumps=%ld frees=%ld live=0\n", tag, g_dump_calls,  \
	       g_free_calls);                                                 \
} while (0)

/* A real (zeroed) socket object: the netlink-error log path reads ys->err. */
static struct ynl_sock g_fake_ys;
#define FAKE_YS (&g_fake_ys)

int main(void)
{
	int r;

	/* T1: get_priority hit returns the PPS-device priority, no leak */
	reset();
	r = dpll_pin_get_priority(FAKE_YS, TEST_PPS_DEV, "REF4P");
	assert(r == 3);
	ASSERT_NO_LEAK("get_priority hit");

	/* T2: get_priority miss (pin not in dump) -> -1, dump freed */
	reset();
	r = dpll_pin_get_priority(FAKE_YS, TEST_PPS_DEV, "NOPE");
	assert(r == -1);
	ASSERT_NO_LEAK("get_priority miss");

	/* T3: empty dump (sentinel only) -> not found, no crash, no leak */
	reset(); g_dump_mode = DUMP_EMPTY;
	r = dpll_pin_get_priority(FAKE_YS, TEST_PPS_DEV, "REF4P");
	assert(r == -1);
	ASSERT_NO_LEAK("get_priority empty dump");

	/* T4: failed dump (NULL) -> not found, no crash */
	reset(); g_dump_mode = DUMP_FAIL;
	r = dpll_pin_get_priority(FAKE_YS, TEST_PPS_DEV, "REF4P");
	assert(r == -1);
	r = dpll_pin_set_state(FAKE_YS, TEST_PPS_DEV, "REF4P", DPLL_PIN_STATE_DISCONNECTED);
	assert(r == -1 && g_set_calls == 0);
	ASSERT_NO_LEAK("failed dump");

	/* T5: set_state to the same state short-circuits (no netlink set) */
	reset();
	r = dpll_pin_set_state(FAKE_YS, TEST_PPS_DEV, "REF4P", DPLL_PIN_STATE_SELECTABLE);
	assert(r == DPLL_PIN_STATE_SELECTABLE && g_set_calls == 0);
	ASSERT_NO_LEAK("set_state same state (no-op)");

	/* T6: set_state change writes the right pin/parent/state, returns old */
	reset();
	r = dpll_pin_set_state(FAKE_YS, TEST_PPS_DEV, "REF4P", DPLL_PIN_STATE_DISCONNECTED);
	assert(r == DPLL_PIN_STATE_SELECTABLE);
	assert(g_set_calls == 1 && g_set_id == TEST_REF4P_ID &&
	       g_set_parent == TEST_PPS_DEV && g_set_has_state &&
	       g_set_state == DPLL_PIN_STATE_DISCONNECTED);
	ASSERT_NO_LEAK("set_state change");

	/* T7: set_state where the netlink set fails -> -1, still no leak */
	reset(); g_set_ret = -1;
	r = dpll_pin_set_state(FAKE_YS, TEST_PPS_DEV, "REF4P", DPLL_PIN_STATE_DISCONNECTED);
	assert(r == -1 && g_set_calls == 1);
	ASSERT_NO_LEAK("set_state netlink error");

	/* T8: set_priority 15 on a non-disconnected pin -> disconnect (2 lookups) */
	reset();
	r = dpll_pin_set_priority(FAKE_YS, TEST_PPS_DEV, "REF4P", 15);
	assert(r == 3);                       /* old priority */
	assert(g_set_calls == 1 && g_set_has_state &&
	       g_set_state == DPLL_PIN_STATE_DISCONNECTED && g_set_id == TEST_REF4P_ID);
	ASSERT_NO_LEAK("set_priority 15 -> disconnect");

	/* T9: set_priority 15 on an already disconnected pin -> no write */
	reset();
	r = dpll_pin_set_priority(FAKE_YS, TEST_PPS_DEV, "OUT0P", 15);
	assert(r == 15 && g_set_calls == 0);
	ASSERT_NO_LEAK("set_priority 15 already disconnected");

	/* T10: set_priority normal change writes pin id + prio, returns old prio */
	reset();
	r = dpll_pin_set_priority(FAKE_YS, TEST_PPS_DEV, "REF4P", 5);
	assert(r == 3);
	assert(g_set_calls == 1 && g_set_id == TEST_REF4P_ID &&
	       g_set_parent == TEST_PPS_DEV && g_set_has_prio && g_set_prio == 5);
	ASSERT_NO_LEAK("set_priority change");

	/* T11: set_priority netlink error -> -1 */
	reset(); g_set_ret = -1;
	r = dpll_pin_set_priority(FAKE_YS, TEST_PPS_DEV, "REF4P", 5);
	assert(r == -1);
	ASSERT_NO_LEAK("set_priority netlink error");

	/* T12: set_priority for a device with no parent entry -> -1 */
	reset();
	r = dpll_pin_set_priority(FAKE_YS, 9, "REF4P", 5);
	assert(r == -1 && g_set_calls == 0);
	ASSERT_NO_LEAK("set_priority missing parent");

	/* T13: set_priority on an unknown pin -> -1 */
	reset();
	r = dpll_pin_set_priority(FAKE_YS, TEST_PPS_DEV, "NOPE", 5);
	assert(r == -1 && g_set_calls == 0);
	ASSERT_NO_LEAK("set_priority unknown pin");

	/* T14: set_phase_adjust returns old value, writes new, no leak */
	reset();
	{
		__s64 old = dpll_pin_set_phase_adjust(FAKE_YS, "REF4P", 1234);
		assert(old == 77);
		assert(g_set_calls == 1 && g_set_id == TEST_REF4P_ID && g_set_phase == 1234);
	}
	ASSERT_NO_LEAK("set_phase_adjust");

	/* T15: connected-pin query frees the pin dump and the device rsp */
	reset();
	{
		enum dpll_lock_status ls = 0;
		enum dpll_mode mode = 0;
		__u32 cid = 0, pid = 0;
		enum pin_source csrc = PIN_SOURCE_UNKNOWN;
		enum dpll_pin_state pst = 0;

		r = dpll_get_device_state_and_connected_pin(FAKE_YS, TEST_EEC_DEV,
			&ls, &mode, &cid, &csrc, &pid, &pst);
		assert(r == 0 && cid == TEST_REF4P_ID);
		assert(ls == DPLL_LOCK_STATUS_LOCKED_HO_ACQ);
		assert(g_dev_live == 0);
	}
	ASSERT_NO_LEAK("connected_pin query (found)");

	/* T16: no connected pin on the device -> walks to the list end without
	 * dereferencing the YNL_LIST_END sentinel, returns -1, no leak */
	reset();
	{
		__u32 cid = 0;
		enum pin_source csrc = PIN_SOURCE_UNKNOWN;

		r = dpll_get_device_state_and_connected_pin(FAKE_YS, TEST_PPS_DEV,
			NULL, NULL, &cid, &csrc, NULL, NULL);
		assert(r == -1);
		assert(g_dev_live == 0);
	}
	ASSERT_NO_LEAK("connected_pin query (none connected)");

	/* T17: empty dump -> -1, no crash, no leak */
	reset(); g_dump_mode = DUMP_EMPTY;
	{
		__u32 cid = 0;
		enum pin_source csrc = PIN_SOURCE_UNKNOWN;

		r = dpll_get_device_state_and_connected_pin(FAKE_YS, TEST_EEC_DEV,
			NULL, NULL, &cid, &csrc, NULL, NULL);
		assert(r == -1 && g_dev_live == 0);
	}
	ASSERT_NO_LEAK("connected_pin query (empty dump)");

	/* T18: a failover-like burst of pin ops leaves nothing alive */
	reset();
	for (int i = 0; i < 1000; i++) {
		dpll_pin_set_state(FAKE_YS, TEST_PPS_DEV, "REF4P", DPLL_PIN_STATE_DISCONNECTED);
		dpll_pin_set_state(FAKE_YS, TEST_PPS_DEV, "SDP0_REF0N", DPLL_PIN_STATE_CONNECTED);
		dpll_pin_set_priority(FAKE_YS, TEST_PPS_DEV, "REF4P", 5);
		dpll_pin_get_priority(FAKE_YS, TEST_PPS_DEV, "SDP0_REF0N");
		dpll_pin_set_phase_adjust(FAKE_YS, "OUT0P", 5);
		{
			__u32 cid = 0;
			enum pin_source csrc = PIN_SOURCE_UNKNOWN;
			dpll_get_device_state_and_connected_pin(FAKE_YS, TEST_EEC_DEV,
				NULL, NULL, &cid, &csrc, NULL, NULL);
		}
	}
	assert(g_dev_live == 0);
	assert(g_dump_calls == g_free_calls);
	ASSERT_NO_LEAK("1000x failover-like pin op burst");

	/* T19-T23: dpll_find_device_id_by_type() stops at the list end */
	g_dev_dump_mode = DEV_ONE; g_dev_type = DPLL_TYPE_PPS; g_dev_module = "zl3073x";
	r = dpll_find_device_id_by_type(FAKE_YS, DPLL_TYPE_PPS);
	assert(r == 1 && g_dev_list_live == 0);
	printf("ok   %-44s id=%d live=0\n", "find_device present type", r);

	r = dpll_find_device_id_by_type(FAKE_YS, DPLL_TYPE_EEC);
	assert(r == -1 && g_dev_list_live == 0);
	printf("ok   %-44s id=%d live=0\n", "find_device absent type (no crash)", r);

	g_dev_module = "other";       /* matching type, but skipped by module name (last device) */
	r = dpll_find_device_id_by_type(FAKE_YS, DPLL_TYPE_PPS);
	assert(r == -1 && g_dev_list_live == 0);
	printf("ok   %-44s id=%d live=0\n", "find_device last device skipped by module", r);
	g_dev_module = "zl3073x";

	g_dev_dump_mode = DEV_EMPTY;
	r = dpll_find_device_id_by_type(FAKE_YS, DPLL_TYPE_PPS);
	assert(r == -1);
	printf("ok   %-44s id=%d\n", "find_device empty dump (no crash)", r);

	g_dev_dump_mode = DEV_FAIL;
	r = dpll_find_device_id_by_type(FAKE_YS, DPLL_TYPE_PPS);
	assert(r == -1);
	printf("ok   %-44s id=%d\n", "find_device failed dump", r);
	g_dev_dump_mode = DEV_ONE;

	printf("ALL PASSED\n");
	return 0;
}
