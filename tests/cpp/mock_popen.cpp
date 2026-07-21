/*
 * Copyright (c) 2026 Wind River Systems, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
/*
 * Mock popen() to return NULL, forcing error paths in PassphraseGenerator.
 * Usage: LD_PRELOAD=./mock_popen.so ./test_passphrase
 */
#include <cstdio>

extern "C" FILE* popen(const char* command, const char* type) {
    (void)command;
    (void)type;
    return NULL;
}

extern "C" int pclose(FILE* stream) {
    (void)stream;
    return 0;
}
