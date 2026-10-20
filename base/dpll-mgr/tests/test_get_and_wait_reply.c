/*
 * test_get_and_wait_reply.c — unit test for the bounded, seq-matched GET/reply
 * helper that replaces the legacy send+usleep(100ms)+process pattern.
 *
 * Proves (off-hardware, deterministic via a socketpair):
 *   T1  a reply whose sequenceId matches the request is accepted (returns 0).
 *   T2  a STALE reply (seq = want-1, the State-2 reply-lag mis-dispatch
 *       signature) is DISCARDED and the following MATCHING reply is accepted —
 *       the helper never consumes a prior request's reply as the current one.
 *   T3  no reply within the deadline returns -1 (the "no reply this cycle"
 *       outcome) and does so within ~deadline (bounded wait).
 *
 * We include the TU (ptp_protocol.c) like the sibling tests and drive a real
 * AF_UNIX socketpair so send_get_request()/poll()/recvfrom() all run for real.
 * Replies are crafted with the real build_management_message() so the wire
 * format (and the sequenceId the helper matches on) is authentic. The real
 * dataset handlers run; we assert on the helper's return + the observable that
 * the stale datagram was drained (socket empty after a successful match).
 *
 * Build/run:  make -f Makefile.test test
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <sys/socket.h>
#include <sys/ioctl.h>

#define UNIT_TEST_BUILD 1

#include "../hdr/dpll_manager.h"
#include "../src/ptp_protocol.c"

/* daemon-symbol stubs ptp_protocol.c references (defined in dpll_manager.c). */
GlobalConfig g_config;
FILE *g_log_file = NULL;
LogLevel g_log_level = DPLL_LOG_LEVEL_INFO;
void process_dpll_master_state(AppState *s, struct ynl_sock *d) { (void)s; (void)d; }
/* Further externals reachable from dispatch -> port/parent/time handlers. */
int dpll_pin_set_state(struct ynl_sock *ys, __u32 device_id, char *package_label, int state) {
    (void)ys; (void)device_id; (void)package_label; (void)state; return 0; }
void refresh_pin_states_and_write(AppState *state) { (void)state; }

static int g_failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { printf("FAIL %s\n", msg); g_failures++; } \
    else         { printf("PASS %s\n", msg); } \
} while (0)

/* How many bytes are queued on our read end. */
static int pending_bytes(int fd)
{
    int n = 0;
    ioctl(fd, FIONREAD, &n);
    return n;
}

int main(void)
{
    /* Two bound PATHNAME AF_UNIX datagram sockets, wired like the daemon: local
     * (dpll-mgr) fd + a "ptp4l" fd. local_peer_addr points at the ptp4l socket
     * so send_get_request()'s sendto() delivers. NOTE: send_get_request passes
     * sizeof(sockaddr_un) as the addrlen, so we must use PATHNAME sockets (not
     * abstract — abstract names need an exact addrlen and would ECONNREFUSED). */
    int local_fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    int ptp_fd   = socket(AF_UNIX, SOCK_DGRAM, 0);
    assert(local_fd >= 0 && ptp_fd >= 0);

    struct sockaddr_un local_addr, ptp_addr;
    memset(&local_addr, 0, sizeof local_addr);
    memset(&ptp_addr, 0, sizeof ptp_addr);
    local_addr.sun_family = AF_UNIX;
    ptp_addr.sun_family   = AF_UNIX;
    snprintf(local_addr.sun_path, sizeof(local_addr.sun_path), "/tmp/gwr-test-local-%d", (int)getpid());
    snprintf(ptp_addr.sun_path,   sizeof(ptp_addr.sun_path),   "/tmp/gwr-test-ptp4l-%d", (int)getpid());
    unlink(local_addr.sun_path);
    unlink(ptp_addr.sun_path);
    assert(bind(local_fd, (struct sockaddr *)&local_addr, sizeof(local_addr)) == 0);
    assert(bind(ptp_fd,   (struct sockaddr *)&ptp_addr,   sizeof(ptp_addr))   == 0);

    AppState st;
    memset(&st, 0, sizeof(st));
    st.local_socket_fd = local_fd;
    st.local_peer_addr = ptp_addr;     /* GETs go here; we drain them */
    st.local_sequence_id = 0;

    /* inject a crafted reply from ptp_fd -> local_fd */
    #define INJECT(seq, mid) do { \
        uint8_t _m[512]; uint8_t _p[64] = {0}; \
        int _l = build_management_message(_m, sizeof(_m), (uint16_t)(seq), (mid), RESPONSE, _p, 4); \
        assert(_l > 0); \
        assert(sendto(ptp_fd, _m, (size_t)_l, 0, (struct sockaddr *)&local_addr, sizeof(local_addr)) == _l); \
    } while (0)
    /* drain the GET the helper sent to ptp_fd */
    #define DRAIN_GET() do { uint8_t _b[512]; (void)recv(ptp_fd, _b, sizeof(_b), MSG_DONTWAIT); } while (0)

    /* --- T1: matching reply accepted -------------------------------------- */
    INJECT(0, MGMT_ID_PORT_DATA_SET);       /* send_get_request will send seq=0 */
    int r1 = get_and_wait_reply(&st, MGMT_ID_PORT_DATA_SET, GM_GET_REPLY_DEADLINE_MS);
    DRAIN_GET();
    CHECK(r1 == 0, "T1: matching-seq reply returns 0");
    CHECK(pending_bytes(local_fd) == 0, "T1: socket drained");

    /* --- T2: stale reply discarded, matching one then accepted ------------ */
    uint16_t want = st.local_sequence_id;                 /* == 1 */
    INJECT((uint16_t)(want - 1), MGMT_ID_PARENT_DATA_SET); /* stale (seq=want-1) */
    INJECT(want,                 MGMT_ID_TIME_STATUS_NP);  /* ours */
    int r2 = get_and_wait_reply(&st, MGMT_ID_TIME_STATUS_NP, GM_GET_REPLY_DEADLINE_MS);
    DRAIN_GET();
    CHECK(r2 == 0, "T2: returns 0 after discarding the stale reply");
    CHECK(pending_bytes(local_fd) == 0,
          "T2: both stale and matching datagrams consumed (stale discarded, ours dispatched)");

    /* --- T3: no reply -> -1 within ~deadline ------------------------------ */
    struct timespec a, b;
    clock_gettime(CLOCK_MONOTONIC, &a);
    int r3 = get_and_wait_reply(&st, MGMT_ID_PORT_DATA_SET, GM_GET_REPLY_DEADLINE_MS);
    clock_gettime(CLOCK_MONOTONIC, &b);
    DRAIN_GET();
    long elapsed_ms = (b.tv_sec - a.tv_sec) * 1000 + (b.tv_nsec - a.tv_nsec) / 1000000;
    CHECK(r3 == -1, "T3: no reply returns -1");
    CHECK(elapsed_ms >= GM_GET_REPLY_DEADLINE_MS - 5 &&
          elapsed_ms <= GM_GET_REPLY_DEADLINE_MS + 50,
          "T3: returned at ~deadline (bounded wait)");

    close(local_fd); close(ptp_fd);
    unlink(local_addr.sun_path); unlink(ptp_addr.sun_path);
    printf("\n%s (%d failures)\n", g_failures ? "TESTS FAILED" : "ALL TESTS PASSED", g_failures);
    return g_failures ? 1 : 0;
}
