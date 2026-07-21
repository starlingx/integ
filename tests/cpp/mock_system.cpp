/*
 * Copyright (c) 2026 Wind River Systems, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
/*
 * Mock library for luks-fs-mgr.cpp tests via LD_PRELOAD.
 *
 * Single-value env vars (backward compatible):
 *   MOCK_SYSTEM_RC, MOCK_ACCESS_RC, MOCK_POPEN_NULL, MOCK_POPEN_DATA,
 *   MOCK_PCLOSE_RC, MOCK_LSTAT_LINK, MOCK_KILL_RC
 *
 * Sequence env vars (comma-separated, consumed left to right):
 *   MOCK_SYSTEM_SEQ  - e.g. "0,1,0" -> first call returns 0, second 1, third 0
 *   MOCK_ACCESS_SEQ  - e.g. "-1,0,-1"
 *   MOCK_PCLOSE_SEQ  - e.g. "0,0,0,256" (per-call pclose return values)
 *   MOCK_POPEN_SEQ   - e.g. "data1|data2|data3" (pipe-separated)
 *
 * Call tracking (for assertions in tests):
 *   mock_reset_counts() - reset all counters
 *   mock_get_popen_count() - number of popen() calls since last reset
 *   mock_get_system_count() - number of system() calls since last reset
 *   mock_get_last_popen_cmd() - last command passed to popen()
 *   mock_get_last_system_cmd() - last command passed to system()
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sys/stat.h>
#include <sys/types.h>
#include <cerrno>
#include <signal.h>
#include <unistd.h>
#include <stdarg.h>
#include <syslog.h>

/* ── Call tracking state ── */
static int s_popen_count = 0;
static int s_system_count = 0;
static int s_syslog_count = 0;
static char s_last_popen_cmd[4096] = {0};
static char s_last_system_cmd[4096] = {0};
static char s_last_syslog_msg[4096] = {0};
static int s_last_syslog_priority = 0;

extern "C" void mock_reset_counts() {
    s_popen_count = 0;
    s_system_count = 0;
    s_syslog_count = 0;
    s_last_popen_cmd[0] = '\0';
    s_last_system_cmd[0] = '\0';
    s_last_syslog_msg[0] = '\0';
    s_last_syslog_priority = 0;
}

extern "C" int mock_get_popen_count() { return s_popen_count; }
extern "C" int mock_get_system_count() { return s_system_count; }
extern "C" const char *mock_get_last_popen_cmd() { return s_last_popen_cmd; }
extern "C" const char *mock_get_last_system_cmd() { return s_last_system_cmd; }
extern "C" const char *mock_get_last_syslog_msg() { return s_last_syslog_msg; }
extern "C" int mock_get_last_syslog_priority() { return s_last_syslog_priority; }
extern "C" int mock_get_syslog_count() { return s_syslog_count; }

/* ── Helpers ── */

static int get_env_int(const char *name, int def) {
    const char *v = getenv(name);
    return v ? atoi(v) : def;
}

/* Parse next int from a comma-separated sequence env var.
   Advances the env var past the consumed value. */
static int next_seq_int(const char *seq_name, const char *fallback_name,
                        int def) {
    char *seq = getenv(seq_name);
    if (seq && seq[0]) {
        int val = atoi(seq);
        char *comma = strchr(seq, ',');
        if (comma) {
            setenv(seq_name, comma + 1, 1);
        } else {
            /* Last value - keep returning it */
        }
        return val;
    }
    return get_env_int(fallback_name, def);
}

/* Parse next string from a pipe-separated sequence env var. */
static const char *next_seq_str(const char *seq_name,
                                const char *fallback_name) {
    static char buf[4096];
    char *seq = getenv(seq_name);
    if (seq && seq[0]) {
        char *pipe = strchr(seq, '|');
        if (pipe) {
            size_t len = pipe - seq;
            if (len >= sizeof(buf)) len = sizeof(buf) - 1;
            memcpy(buf, seq, len);
            buf[len] = '\0';
            setenv(seq_name, pipe + 1, 1);
        } else {
            strncpy(buf, seq, sizeof(buf) - 1);
            buf[sizeof(buf) - 1] = '\0';
        }
        return buf;
    }
    const char *v = getenv(fallback_name);
    return v ? v : "mock_output\n";
}

/* ── Mocked system calls ── */

extern "C" int system(const char *cmd) {
    s_system_count++;
    if (cmd) {
        strncpy(s_last_system_cmd, cmd, sizeof(s_last_system_cmd) - 1);
        s_last_system_cmd[sizeof(s_last_system_cmd) - 1] = '\0';
    }
    return next_seq_int("MOCK_SYSTEM_SEQ", "MOCK_SYSTEM_RC", 0);
}

extern "C" FILE *popen(const char *cmd, const char *mode) {
    (void)mode;
    s_popen_count++;
    if (cmd) {
        strncpy(s_last_popen_cmd, cmd, sizeof(s_last_popen_cmd) - 1);
        s_last_popen_cmd[sizeof(s_last_popen_cmd) - 1] = '\0';
    }
    const char *null_env = getenv("MOCK_POPEN_NULL");
    if (null_env && strcmp(null_env, "1") == 0)
        return NULL;
    const char *data = next_seq_str("MOCK_POPEN_SEQ", "MOCK_POPEN_DATA");
    if (!data || !data[0]) data = "\n";
    static char popen_buf[4096];
    strncpy(popen_buf, data, sizeof(popen_buf) - 1);
    popen_buf[sizeof(popen_buf) - 1] = '\0';
    return fmemopen(popen_buf, strlen(popen_buf), "r");
}

extern "C" int pclose(FILE *fp) {
    if (fp) fclose(fp);
    return next_seq_int("MOCK_PCLOSE_SEQ", "MOCK_PCLOSE_RC", 0);
}

extern "C" int access(const char *path, int mode) {
    (void)mode;
    if (path && (strncmp(path, "/tmp/", 5) == 0 ||
                 strcmp(path, "/dev/null") == 0)) {
        return next_seq_int("MOCK_ACCESS_SEQ", "MOCK_ACCESS_RC", -1);
    }
    return next_seq_int("MOCK_ACCESS_SEQ", "MOCK_ACCESS_RC", -1);
}

extern "C" int lstat(const char *path, struct stat *buf) {
    (void)path;
    memset(buf, 0, sizeof(*buf));
    const char *v = getenv("MOCK_LSTAT_LINK");
    if (v && strcmp(v, "1") == 0) {
        buf->st_mode = S_IFLNK | 0777;
        return 0;
    }
    buf->st_mode = S_IFREG | 0644;
    return 0;
}

extern "C" int daemon(int nochdir, int noclose) {
    (void)nochdir; (void)noclose;
    return 0;
}

extern "C" int kill(pid_t pid, int sig) {
    (void)pid; (void)sig;
    return get_env_int("MOCK_KILL_RC", -1);
}

extern "C" unsigned int sleep(unsigned int seconds) {
    (void)seconds;
    return 0;
}

extern "C" void openlog(const char *ident, int option, int facility) {
    (void)ident; (void)option; (void)facility;
}

extern "C" void syslog(int priority, const char *format, ...) {
    s_syslog_count++;
    s_last_syslog_priority = priority;
    va_list args;
    va_start(args, format);
    vsnprintf(s_last_syslog_msg, sizeof(s_last_syslog_msg), format, args);
    va_end(args);
}

extern "C" void closelog(void) {}
