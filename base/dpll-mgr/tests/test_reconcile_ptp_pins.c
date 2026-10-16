/*
 * test_reconcile_ptp_pins.c unit test
 *
 * Proves the autonomous, GM-gated, write-on-change pin maintenance:
 *   - desired_ptp_pin_state(): pure GM-presence -> SELECTABLE/DISCONNECTED.
 *   - reconcile_ptp_pins(): drives handle_ptp_port_up/down ONLY when the live
 *     pin state differs from desired (never set-to-same-state), and treats a
 *     live CONNECTED pin as already satisfying a SELECTABLE desire.
 *
 * These assertions encode the Known-Issue table:
 *   Issue 12  : GM present + REF0N disconnected -> SELECTABLE asserted (enables failover)
 *   decay     : GM present + REF0N decayed to disconnected -> re-asserted (self-heal)
 *   steady    : GM present + REF0N already selectable/connected -> NO write
 *   Issue 17  : GM absent  + REF0N selectable -> DISCONNECTED asserted (false-lock guard)
 *   steady    : GM absent  + REF0N already disconnected -> NO write
 *
 * reconcile_ptp_pins lives in ptp_protocol.c; we include that TU and stub the
 * two actuators (handle_ptp_port_up/down) with call counters. No framework;
 * non-zero exit = failed assertion.
 *
 * Build/run:  make -f Makefile.test test
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define UNIT_TEST_BUILD 1

#include "../hdr/dpll_manager.h"

/* --- actuator call counters (the "did we write HW?" observable) ------------ */
static int g_up_calls;
static int g_down_calls;

/* Stub the actuators BEFORE including the TU, so reconcile_ptp_pins calls these.
 * The TU's own handle_ptp_port_up/down definitions are compiled out via the
 * UNIT_TEST_STUB_ACTUATORS guard added around them. */
#define UNIT_TEST_STUB_ACTUATORS 1
void handle_ptp_port_up(AppState *s)   { (void)s; g_up_calls++; }
void handle_ptp_port_down(AppState *s) { (void)s; g_down_calls++; }

/* Pull in the unit under test. */
#include "../src/ptp_protocol.c"

/* --- daemon-symbol stubs that ptp_protocol.c references ------------------- */
GlobalConfig g_config;
/* Logging globals live in dpll_manager.c (not included here); define them so
 * ptp_protocol.c's pr_* macros link. */
FILE *g_log_file = NULL;
LogLevel g_log_level = DPLL_LOG_LEVEL_INFO;
/* ptp_protocol.c references this (dpll_manager.c, not included here). */
void process_dpll_master_state(AppState *s, struct ynl_sock *d) { (void)s; (void)d; }

/* helper: run one reconcile with a given gm_present + live REF0N state,
 * return via out-params how many up/down writes happened. */
static void run(bool gm_present, enum dpll_pin_state live,
                int *ups, int *downs)
{
    AppState st;
    memset(&st, 0, sizeof(st));
    st.pps_dpll_device_id = 1;              /* non-zero so reconcile proceeds */
    st.is_ptp_connected_to_gm = gm_present;
    st.pin_states[SDP0_REF0N].state = live;
    g_up_calls = 0;
    g_down_calls = 0;
    reconcile_ptp_pins(&st);
    *ups = g_up_calls;
    *downs = g_down_calls;
}

#define CHECK(cond, msg) do { \
    if (!(cond)) { printf("FAIL %s\n", msg); failures++; } \
    else         { printf("PASS %s\n", msg); } \
} while (0)

int main(void)
{
    int failures = 0;
    int ups, downs;

    /* --- pure function --------------------------------------------------- */
    CHECK(desired_ptp_pin_state(true)  == DPLL_PIN_STATE_SELECTABLE,
          "desired(gm=true)=SELECTABLE");
    CHECK(desired_ptp_pin_state(false) == DPLL_PIN_STATE_DISCONNECTED,
          "desired(gm=false)=DISCONNECTED");

    /* --- Issue 12: GM present, pin disconnected -> assert SELECTABLE ------ */
    run(true, DPLL_PIN_STATE_DISCONNECTED, &ups, &downs);
    CHECK(ups == 1 && downs == 0,
          "Issue12: gm+disconnected -> one UP (SELECTABLE) write");

    /* --- decay self-heal: same as above (decay returns pin to disconnected) */
    run(true, DPLL_PIN_STATE_DISCONNECTED, &ups, &downs);
    CHECK(ups == 1 && downs == 0,
          "decay: gm+disconnected -> re-assert SELECTABLE");

    /* --- steady (already selectable): NO write --------------------------- */
    run(true, DPLL_PIN_STATE_SELECTABLE, &ups, &downs);
    CHECK(ups == 0 && downs == 0,
          "steady: gm+selectable -> no write");

    /* --- live CONNECTED satisfies SELECTABLE desire: NO write ------------ */
    run(true, DPLL_PIN_STATE_CONNECTED, &ups, &downs);
    CHECK(ups == 0 && downs == 0,
          "connected satisfies selectable -> no write (don't force down)");

    /* --- Issue 17: GM absent, pin selectable -> assert DISCONNECTED ------- */
    run(false, DPLL_PIN_STATE_SELECTABLE, &ups, &downs);
    CHECK(ups == 0 && downs == 1,
          "Issue17: no-gm+selectable -> one DOWN (DISCONNECTED) write");

    /* --- Issue 17: GM absent, pin connected -> assert DISCONNECTED -------- */
    run(false, DPLL_PIN_STATE_CONNECTED, &ups, &downs);
    CHECK(ups == 0 && downs == 1,
          "Issue17: no-gm+connected -> one DOWN (DISCONNECTED) write");

    /* --- steady (already disconnected): NO write ------------------------- */
    run(false, DPLL_PIN_STATE_DISCONNECTED, &ups, &downs);
    CHECK(ups == 0 && downs == 0,
          "steady: no-gm+disconnected -> no write");

    if (failures) {
        printf("\n%d reconcile_ptp_pins assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("\nAll reconcile_ptp_pins assertions PASSED\n");
    return 0;
}
