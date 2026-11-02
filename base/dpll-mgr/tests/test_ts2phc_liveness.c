/*
 * test_ts2phc_liveness.c unit test
 *
 * Proves the GNSS-side (ts2phc) liveness state machine in ts2phc_liveness_tick():
 *   - probe cadence: calls within TS2PHC_PROBE_INTERVAL_SEC do NOT re-probe.
 *   - 2 consecutive probe failures -> ts2phc_down, REF4P driven DISCONNECTED once
 *     (idempotent: a 3rd failure does not re-drive).
 *   - a single failure then success -> counter resets, no down action.
 *   - recovery: fail->down, then a success -> REF4P driven SELECTABLE once,
 *     ts2phc_down cleared.
 *   - SW_BASED-only: HW_BASED mode or an unconfigured ts2_0 socket -> no-op.
 *
 * ts2phc_liveness_tick + handle_gnss_source_down/up are in dpll_manager.c; we
 * include that TU and control ts2phc_probe_alive() (gearshift.c, not included)
 * via a stub, and capture the REF4P writes via a dpll_pin_set_state() stub. No
 * framework; non-zero exit = failed assertion.
 *
 * Build/run:  make -f Makefile.test test
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define UNIT_TEST_BUILD 1

/* Controlled ts2phc liveness probe result (gearshift.c, not included here). */
static int g_probe_alive = 1;          /* what ts2phc_probe_alive() returns */
static int g_probe_calls  = 0;         /* how many times it was called */

/* Device IDs used by the test. EEC is deliberately 0 — matching the real
 * hardware (EEC=device 0, PPS=device 1) — so the test catches any `if (id)`
 * truthiness guard that would wrongly skip the EEC device. */
#define TEST_PPS_DEV 1
#define TEST_EEC_DEV 0

/* Captured REF4P writes (dpll_utils.c dpll_pin_set_state(), not included).
 * Track total count + the last requested state per DPLL device so the tests can
 * assert BOTH the PPS and the EEC engine are driven. */
static int  g_set_calls   = 0;
static char g_last_label[32]  = {0};
static int  g_last_state      = -1;    /* last state written to ANY device */
static int  g_pps_state       = -1;    /* last state written to the PPS device */
static int  g_eec_state       = -1;    /* last state written to the EEC device */

#include "../hdr/dpll_manager.h"

/* Pull in the unit under test (brings in ts2phc_liveness_tick +
 * handle_gnss_source_down/up + all daemon types). Daemon-symbol stubs follow. */
#include "../src/dpll_manager.c"

/* --- controlled deps ------------------------------------------------------- */
GlobalConfig g_config;

/* The liveness probe — return value controlled by g_probe_alive. */
bool ts2phc_probe_alive(AppState *s) { (void)s; g_probe_calls++; return g_probe_alive; }

/* Capture REF4P enable/disable writes driven by handle_gnss_source_down/up,
 * per DPLL device so both-engine behavior is observable. */
int dpll_pin_set_state(struct ynl_sock *ys, __u32 device_id, char *package_label,
                       int state) {
    (void)ys;
    g_set_calls++;
    strncpy(g_last_label, package_label, sizeof(g_last_label) - 1);
    g_last_state = state;
    if (device_id == TEST_PPS_DEV) g_pps_state = state;
    else if (device_id == TEST_EEC_DEV) g_eec_state = state;
    return 0;
}

/* refresh_pin_states_and_write() -> update_pin_states() -> dpll_pin_dump();
 * return NULL so the refresh is a harmless no-op (no pin writes of its own).
 * dpll_pin_get_list_free() comes from the real YNL object (handles NULL). */
struct dpll_pin_get_list* dpll_pin_dump(struct ynl_sock *ys, __u32 device_id) {
    (void)ys; (void)device_id; return NULL;
}
void write_status_json(const AppState *s) { (void)s; }

/* --- remaining daemon-symbol stubs so dpll_manager.c links ----------------- */
void reconcile_ptp_pins(AppState *s) { (void)s; }
void handle_ptp_port_up(AppState *s) { (void)s; }
void handle_ptp_port_down(AppState *s) { (void)s; }
int  send_get_request(int sockfd, struct sockaddr_un *peer_addr,
                      uint16_t mgmt_id, uint16_t *seq) {
    (void)sockfd; (void)peer_addr; (void)mgmt_id; (void)seq; return 0; }
void process_ptp_messages(AppState *s) { (void)s; }
int  get_and_wait_reply(AppState *s, uint16_t mgmt_id, int deadline_ms) {
    (void)s; (void)mgmt_id; (void)deadline_ms; return 0; }
void forward_clock_parameters(AppState *s) { (void)s; }
void handle_sw_based_failover(AppState *s, enum pin_source m) { (void)s; (void)m; }
bool check_free_running_mode(int sock_fd, struct sockaddr_un *peer_addr,
                             uint16_t *sequence_id) {
    (void)sock_fd; (void)peer_addr; (void)sequence_id; return false; }
const char *lock_status_to_string(enum dpll_lock_status st) { (void)st; return "test"; }
int  dpll_pin_set_priority(struct ynl_sock *y, __u32 d, char *l, int p) {
    (void)y; (void)d; (void)l; (void)p; return 0; }
int  dpll_pin_get_priority(struct ynl_sock *y, __u32 d, char *l) {
    (void)y; (void)d; (void)l; return 0; }
int  init_dpll(void) { return 0; }
int  dpll_find_device_id_by_type(struct ynl_sock *y, enum dpll_type t) {
    (void)y; (void)t; return 0; }
int  dpll_get_device_state_and_connected_pin(struct ynl_sock *ys, __u32 device_id,
         enum dpll_lock_status *lock_status, enum dpll_mode *mode,
         __u32 *connected_pin_id, enum pin_source *connected_pin_source,
         __u32 *ptp_pin_id, enum dpll_pin_state *ptp_pin_state) {
    (void)ys; (void)device_id; (void)lock_status; (void)mode;
    (void)connected_pin_id; (void)connected_pin_source;
    (void)ptp_pin_id; (void)ptp_pin_state; return 0; }
struct ynl_sock *ys;
int  gnss_init(const gnss_config_t *config) { (void)config; return 0; }
const ChannelConfig* config_get_channel(const char *name) { (void)name; return NULL; }

/* --- helpers --------------------------------------------------------------- */
/* A ready-to-tick state: SW_BASED, ts2_0 configured, DPLL socket up. A dummy
 * non-NULL dpll_sock satisfies the !state->dpll_sock guard (never dereferenced
 * here because dpll_pin_dump/dpll_pin_set_state are stubbed). */
static int g_dummy_sock;
static void reset_state(AppState *st) {
    memset(st, 0, sizeof(*st));
    st->pps_dpll_device_id = TEST_PPS_DEV;
    st->eec_dpll_device_id = TEST_EEC_DEV;
    st->ts2phc_socket_fd   = 3;                 /* ts2_0 configured */
    st->dpll_sock          = (struct ynl_sock *)&g_dummy_sock;
    g_config.manager.operation_mode = OPERATION_MODE_SW_BASED;
    g_probe_alive = 1;
    g_probe_calls = 0;
    g_set_calls   = 0;
    g_last_state  = -1;
    g_pps_state   = -1;
    g_eec_state   = -1;
    g_last_label[0] = '\0';
}

/* Force the cadence gate open: pretend the last probe was long ago. */
static void allow_probe(AppState *st) {
    st->last_ts2phc_probe.tv_sec = 0;   /* now - 0 >> interval */
}

#define CHECK(cond, msg) do { \
    if (!(cond)) { printf("FAIL %s\n", msg); failures++; } \
    else         { printf("PASS %s\n", msg); } \
} while (0)

int main(void)
{
    int failures = 0;
    AppState st;

    /* --- cadence: a just-probed state does NOT re-probe ------------------ */
    reset_state(&st);
    clock_gettime(CLOCK_MONOTONIC, &st.last_ts2phc_probe);  /* probed "now" */
    ts2phc_liveness_tick(&st);
    CHECK(g_probe_calls == 0, "cadence: within interval -> no probe");

    /* --- single failure then success: counter resets, no down ----------- */
    reset_state(&st);
    g_probe_alive = 0;
    allow_probe(&st);
    ts2phc_liveness_tick(&st);
    CHECK(st.ts2phc_probe_fail_count == 1 && !st.ts2phc_down && g_set_calls == 0,
          "1 fail: counter=1, not down, no REF4P write");
    g_probe_alive = 1;
    allow_probe(&st);
    ts2phc_liveness_tick(&st);
    CHECK(st.ts2phc_probe_fail_count == 0 && !st.ts2phc_down && g_set_calls == 0,
          "fail then ok: counter reset, no write (transient ignored)");

    /* --- 2 consecutive failures -> down + REF4P DISCONNECTED on BOTH devices */
    reset_state(&st);
    g_probe_alive = 0;
    allow_probe(&st); ts2phc_liveness_tick(&st);   /* strike 1 */
    allow_probe(&st); ts2phc_liveness_tick(&st);   /* strike 2 -> down */
    CHECK(st.ts2phc_down && g_set_calls == 2 &&
          strcmp(g_last_label, "REF4P") == 0 &&
          g_pps_state == DPLL_PIN_STATE_DISCONNECTED &&
          g_eec_state == DPLL_PIN_STATE_DISCONNECTED,
          "2 fails: ts2phc_down + REF4P->DISCONNECTED on BOTH PPS+EEC (two writes)");

    /* --- idempotent: a 3rd failure does NOT re-drive -------------------- */
    allow_probe(&st); ts2phc_liveness_tick(&st);
    CHECK(st.ts2phc_down && g_set_calls == 2,
          "3rd fail: still down, no further write (idempotent)");

    /* --- recovery: success after down (REF4P left DISCONNECTED by the down
     *     handler) -> re-enable REF4P->SELECTABLE on BOTH devices. SELECTABLE is
     *     only a candidate, not a lock: if GNSS is really absent the DPLL just
     *     never selects it, so re-enabling is harmless. */
    st.pin_states[GNSS_REF4P].state = DPLL_PIN_STATE_DISCONNECTED; /* PPS, as left by down */
    g_probe_alive = 1;
    allow_probe(&st); ts2phc_liveness_tick(&st);
    CHECK(!st.ts2phc_down && st.ts2phc_probe_fail_count == 0 &&
          g_set_calls == 4 &&          /* 2 (down) + 2 (up: PPS+EEC) */
          strcmp(g_last_label, "REF4P") == 0 &&
          g_pps_state == DPLL_PIN_STATE_SELECTABLE &&
          g_eec_state == DPLL_PIN_STATE_SELECTABLE,
          "recovery: ok after down -> REF4P->SELECTABLE on BOTH PPS+EEC, not down");

    /* --- recovery no-demote (PPS): PPS pin already CONNECTED (DPLL selected
     *     it) -> the recovery edge must NOT demote the PPS pin back to
     *     SELECTABLE; the EEC pin (left DISCONNECTED by the down handler) is
     *     still re-enabled. So up writes EEC only. */
    reset_state(&st);
    g_probe_alive = 0;
    allow_probe(&st); ts2phc_liveness_tick(&st);   /* strike 1 */
    allow_probe(&st); ts2phc_liveness_tick(&st);   /* strike 2 -> down (2 writes) */
    st.pin_states[GNSS_REF4P].state = DPLL_PIN_STATE_CONNECTED; /* PPS already active */
    g_eec_state = -1;                              /* clear to observe the up-phase EEC write */
    g_probe_alive = 1;
    allow_probe(&st); ts2phc_liveness_tick(&st);
    CHECK(!st.ts2phc_down && g_set_calls == 3 &&   /* 2 (down) + 1 (up: EEC only) */
          g_eec_state == DPLL_PIN_STATE_SELECTABLE,
          "recovery no-demote: PPS already CONNECTED -> PPS not re-written, EEC re-enabled");

    /* --- SW_BASED-only: HW_BASED mode -> no-op -------------------------- */
    reset_state(&st);
    g_config.manager.operation_mode = OPERATION_MODE_HW_BASED;
    g_probe_alive = 0;
    allow_probe(&st); ts2phc_liveness_tick(&st);
    CHECK(g_probe_calls == 0 && g_set_calls == 0 && !st.ts2phc_down,
          "HW_BASED: tick is a no-op");

    /* --- ts2_0 unconfigured (socket < 0) -> no-op ----------------------- */
    reset_state(&st);
    st.ts2phc_socket_fd = -1;
    g_probe_alive = 0;
    allow_probe(&st); ts2phc_liveness_tick(&st);
    CHECK(g_probe_calls == 0 && g_set_calls == 0 && !st.ts2phc_down,
          "ts2_0 unconfigured: tick is a no-op");

    if (failures) {
        printf("\n%d ts2phc_liveness assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("\nAll ts2phc_liveness assertions PASSED\n");
    return 0;
}
