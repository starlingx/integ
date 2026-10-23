/*
 * test_update_pin_states.c regression test
 *
 * Proves update_pin_states() serializes LIVE DPLL pin state (from dpll_pin_dump)
 * rather than the in-memory ptp_pin_state flag. These assertions FAIL against the
 * pre-fix synthesis implementation and PASS against the live-read fix.
 *
 * update_pin_states() is static, so we #include the translation unit and stub the
 * DPLL / IO dependencies it calls. No external test framework (first harness for
 * this package); a non-zero exit means a failed assertion.
 *
 * Build/run:  make -f Makefile.test test
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* ---- stub the heavy deps BEFORE including the unit under test -------------- */
/* We only need update_pin_states + its direct callees to link. The real
 * dpll_pin_dump is replaced by a test double whose return value we control. */

#define UNIT_TEST_BUILD 1

/* Controlled live-dump the stub returns. Each test sets g_test_live_state for the
 * target pin's package_label (g_test_label). */
static int                 g_test_has_pin   = 0;
static char                g_test_label[32] = {0};
static int                 g_test_live_state = 0;   /* enum dpll_pin_state value */

/* Dual-parent modelling for the EEC-vs-PPS selection test (Finding 1). When
 * g_test_dual is set, the double returns two parent_device entries carrying
 * distinct parent_id/state so we can prove selection is by device identity,
 * not array index. parent_device[g_test_eec_idx] is the EEC device
 * (DISCONNECTED), the other is the PPS device (= g_test_live_state). */
static int                 g_test_dual      = 0;
static int                 g_test_eec_idx   = 0;     /* which index holds EEC */
static unsigned int        g_test_pps_id    = 0;     /* __u32 value, declared early */
static unsigned int        g_test_eec_id    = 0;

/* Minimal stand-ins pulled in via the real headers below; the included .c uses
 * dpll_pin_dump() / dpll_pin_get_list_free() / write_status_json() etc. We
 * provide those symbols here so the test links without the full daemon. */

#include "../hdr/dpll_manager.h"
#include "../ynl/dpll-user.h"
/* YNL_LIST_END sentinel — declared locally to avoid pulling ynl-priv.h's
 * netlink-header cascade into the test. We only need its address. */
struct ynl_dump_list_type;
extern struct ynl_dump_list_type *YNL_LIST_END;

/* --- test double for the live dump (struct from dpll-user.h, included above) */
struct dpll_pin_get_list* dpll_pin_dump(struct ynl_sock *ys, __u32 device_id) {
    (void)ys; (void)device_id;
    if (!g_test_has_pin) return NULL;
    /* Heap-allocate so the real dpll_pin_get_list_free() can free it. */
    struct dpll_pin_get_list *node = calloc(1, sizeof(*node));
    struct dpll_pin_parent_device *pdev = calloc(2, sizeof(*pdev));
    node->next = (struct dpll_pin_get_list *)YNL_LIST_END;  /* ynl list terminator */
    node->obj.package_label = strdup(g_test_label);
    node->obj.n_parent_device = 2;
    node->obj.parent_device = pdev;
    if (g_test_dual) {
        /* EEC device at g_test_eec_idx (permanently DISCONNECTED), PPS at the
         * other index (carries the hardware truth). Both _present.state set. */
        int eec = g_test_eec_idx ? 1 : 0;
        int pps = eec ? 0 : 1;
        pdev[eec]._present.state = 1;
        pdev[eec]._present.parent_id = 1;
        pdev[eec].parent_id = g_test_eec_id;
        pdev[eec].state = (enum dpll_pin_state)DPLL_PIN_STATE_DISCONNECTED;
        pdev[pps]._present.state = 1;
        pdev[pps]._present.parent_id = 1;
        pdev[pps].parent_id = g_test_pps_id;
        pdev[pps].state = (enum dpll_pin_state)g_test_live_state;
    } else {
        pdev[1]._present.state = 1;
        pdev[1].state = (enum dpll_pin_state)g_test_live_state;
    }
    return node;
}

/* Pull in the unit under test (brings in static update_pin_states + all the
 * daemon types/headers). Stubs for the daemon symbols the TU references are
 * defined AFTER this include so all required types are in scope. */
#include "../src/dpll_manager.c"

/* --- daemon-symbol stubs (not exercised by update_pin_states) -------------- */
static int g_write_status_json_calls = 0;
void write_status_json(const AppState *s) { (void)s; g_write_status_json_calls++; }
GlobalConfig g_config;
void handle_ptp_port_up(AppState *s) { (void)s; }
void handle_ptp_port_down(AppState *s) { (void)s; }
int  send_get_request(int sockfd, struct sockaddr_un *peer_addr,
                      uint16_t mgmt_id, uint16_t *seq) {
    (void)sockfd; (void)peer_addr; (void)mgmt_id; (void)seq; return 0; }
void process_ptp_messages(AppState *s) { (void)s; }
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
/* Added by the stacked reconcile/GET-reply commits; not exercised by update_pin_states. */

/* --- helpers --------------------------------------------------------------- */
static void seed_one_pin(AppState *st, const char *pin_name, const char *pkg, int prio) {
    memset(st, 0, sizeof(*st));
    strncpy(st->eec_priority_table[0].pin_name, pin_name, sizeof(st->eec_priority_table[0].pin_name)-1);
    strncpy(st->eec_priority_table[0].package_label, pkg, sizeof(st->eec_priority_table[0].package_label)-1);
    st->eec_priority_table[0].priority = prio;
    st->lock_status = DPLL_LOCK_STATUS_LOCKED_HO_ACQ;
    st->current_master = PIN_SOURCE_UNKNOWN;   /* not master */
    /* Device identities used by the PPS-by-parent_id selection (Finding 1). */
    st->pps_dpll_device_id = 2;
    st->eec_dpll_device_id = 1;
    strncpy(g_test_label, pkg, sizeof(g_test_label)-1);
    g_test_has_pin = 1;
    /* default: single-parent (index-1) modelling, no dual-parent */
    g_test_dual    = 0;
    g_test_eec_idx = 0;
    g_test_pps_id  = st->pps_dpll_device_id;
    g_test_eec_id  = st->eec_dpll_device_id;
}

int main(void) {
    AppState st;
    struct ynl_sock *sock = (struct ynl_sock *)0x1;  /* non-NULL so !dpll_sock guard passes */
    int fails = 0;

    /* CASE 1 — CROSS-PROCESS AMNESIA: hardware SELECTABLE but flag says DISCONNECTED.
     * Pre-fix serialized DISCONNECTED (the bug). Fix must serialize SELECTABLE. */
    seed_one_pin(&st, "SDP0_REF0N", "REF0N", 7);
    st.ptp_pin_state = DPLL_PIN_STATE_DISCONNECTED;       /* stale flag */
    g_test_live_state = DPLL_PIN_STATE_SELECTABLE;        /* hardware truth */
    update_pin_states(&st, sock);
    enum pin_source src = pin_name_to_enum("SDP0_REF0N");
    if (st.pin_states[src].state != DPLL_PIN_STATE_SELECTABLE) {
        printf("FAIL case1: expected SELECTABLE from hardware, got %d (flag leaked)\n",
               st.pin_states[src].state); fails++;
    } else printf("PASS case1: amnesia — serialized hardware SELECTABLE despite stale flag\n");

    /* CASE 2 — hardware DISCONNECTED, flag SELECTABLE: must follow hardware. */
    seed_one_pin(&st, "SDP0_REF0N", "REF0N", 7);
    st.ptp_pin_state = DPLL_PIN_STATE_SELECTABLE;
    g_test_live_state = DPLL_PIN_STATE_DISCONNECTED;
    update_pin_states(&st, sock);
    if (st.pin_states[src].state != DPLL_PIN_STATE_DISCONNECTED) {
        printf("FAIL case2: expected DISCONNECTED from hardware, got %d\n",
               st.pin_states[src].state); fails++;
    } else printf("PASS case2: serialized hardware DISCONNECTED despite SELECTABLE flag\n");

    /* CASE 3 — hardware CONNECTED is reflected regardless of master bookkeeping. */
    seed_one_pin(&st, "SDP0_REF0N", "REF0N", 7);
    st.ptp_pin_state = DPLL_PIN_STATE_DISCONNECTED;
    g_test_live_state = DPLL_PIN_STATE_CONNECTED;
    update_pin_states(&st, sock);
    if (st.pin_states[src].state != DPLL_PIN_STATE_CONNECTED) {
        printf("FAIL case3: expected CONNECTED from hardware, got %d\n",
               st.pin_states[src].state); fails++;
    } else printf("PASS case3: serialized hardware CONNECTED\n");

    /* CASE 4 — Finding 1: pin parented by BOTH engines, EEC entry sorts FIRST
     * (index 0, permanently DISCONNECTED), PPS entry second (SELECTABLE).
     * Index-based selection would publish the EEC's DISCONNECTED; selection by
     * parent_id must pick the PPS device -> SELECTABLE. */
    seed_one_pin(&st, "SDP0_REF0N", "REF0N", 7);
    g_test_dual = 1; g_test_eec_idx = 0;        /* EEC at index 0 */
    g_test_live_state = DPLL_PIN_STATE_SELECTABLE;  /* PPS hardware truth */
    update_pin_states(&st, sock);
    if (st.pin_states[src].state != DPLL_PIN_STATE_SELECTABLE) {
        printf("FAIL case4: EEC-first ordering — expected PPS SELECTABLE, got %d\n",
               st.pin_states[src].state); fails++;
    } else printf("PASS case4: dual-parent EEC-first — chose PPS by parent_id (SELECTABLE)\n");

    /* CASE 5 — same, but PPS entry sorts first (index 0) and EEC second.
     * Selection by parent_id must still land on the PPS device. */
    seed_one_pin(&st, "SDP0_REF0N", "REF0N", 7);
    g_test_dual = 1; g_test_eec_idx = 1;        /* EEC at index 1, PPS at 0 */
    g_test_live_state = DPLL_PIN_STATE_SELECTABLE;
    update_pin_states(&st, sock);
    if (st.pin_states[src].state != DPLL_PIN_STATE_SELECTABLE) {
        printf("FAIL case5: PPS-first ordering — expected PPS SELECTABLE, got %d\n",
               st.pin_states[src].state); fails++;
    } else printf("PASS case5: dual-parent PPS-first — chose PPS by parent_id (SELECTABLE)\n");

    /* CASE 6 — Finding 2: a PTP pin that settles DISCONNECTED -> SELECTABLE with
     * no master/lock transition must trigger exactly one status.json write so
     * the file converges instead of latching the transient value. */
    seed_one_pin(&st, "SDP0_REF0N", "REF0N", 7);
    g_test_live_state = DPLL_PIN_STATE_DISCONNECTED;     /* transient after apply */
    update_pin_states(&st, sock);                        /* publishes DISCONNECTED */
    g_write_status_json_calls = 0;
    g_test_live_state = DPLL_PIN_STATE_SELECTABLE;        /* backhaul settled */
    update_pin_states(&st, sock);
    if (st.pin_states[src].state != DPLL_PIN_STATE_SELECTABLE || g_write_status_json_calls != 1) {
        printf("FAIL case6: expected SELECTABLE + 1 write on change, got state=%d writes=%d\n",
               st.pin_states[src].state, g_write_status_json_calls); fails++;
    } else printf("PASS case6: PTP pin change -> wrote status.json once (converges after apply)\n");

    /* CASE 7 — no change on a steady tick: no extra write. */
    g_write_status_json_calls = 0;
    update_pin_states(&st, sock);                        /* still SELECTABLE */
    if (g_write_status_json_calls != 0) {
        printf("FAIL case7: expected no write when unchanged, got writes=%d\n",
               g_write_status_json_calls); fails++;
    } else printf("PASS case7: steady PTP pin -> no redundant status.json write\n");

    if (fails) { printf("\n%d assertion(s) FAILED\n", fails); return 1; }
    printf("\nAll update_pin_states live-read assertions PASSED\n");
    return 0;
}
