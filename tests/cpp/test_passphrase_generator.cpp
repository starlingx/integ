/*
 * Copyright (c) 2026 Wind River Systems, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
/*
 * Combined test: normal tests + error-path tests using LD_PRELOAD detection.
 * When MOCK_POPEN env var is set, only error-path tests run.
 * Otherwise, normal tests run.
 */

#include <cassert>
#include <cstdlib>
#include <iostream>
#include <string>
#include <memory>
#include "../../filesystem/luks/src/encryption/PassphraseGenerator.h"

static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define ASSERT_TRUE(expr) do { \
    tests_run++; \
    if (expr) { tests_passed++; } \
    else { tests_failed++; \
        std::cerr << "FAIL: " << __func__ << ":" << __LINE__ \
                  << " - " #expr << std::endl; } \
} while(0)

#define ASSERT_NOT_NULL(ptr) ASSERT_TRUE((ptr) != nullptr)
#define ASSERT_NE(a, b) ASSERT_TRUE((a) != (b))
#define ASSERT_EQ(a, b) ASSERT_TRUE((a) == (b))

// ── Factory tests (always run) ──

void test_factory_hwid() {
    auto g = PassphraseGeneratorFactory::createPassphraseGenerator(HWID_Firmware);
    ASSERT_NOT_NULL(g.get());
}

void test_factory_sgx() {
    auto g = PassphraseGeneratorFactory::createPassphraseGenerator(SGX_EncryptedFile);
    ASSERT_NOT_NULL(g.get());
}

void test_factory_tpm() {
    auto g = PassphraseGeneratorFactory::createPassphraseGenerator(TPM_EncryptedFile);
    ASSERT_NOT_NULL(g.get());
}

void test_factory_default() {
    auto g = PassphraseGeneratorFactory::createPassphraseGenerator(
        static_cast<PassphraseMechanism>(999));
    ASSERT_NOT_NULL(g.get());
}

void test_factory_unique() {
    auto g1 = PassphraseGeneratorFactory::createPassphraseGenerator(HWID_Firmware);
    auto g2 = PassphraseGeneratorFactory::createPassphraseGenerator(HWID_Firmware);
    ASSERT_NE(g1.get(), g2.get());
}


// ── Normal path tests (run without LD_PRELOAD) ──

void test_hwid_runs() {
    auto g = PassphraseGeneratorFactory::createPassphraseGenerator(HWID_Firmware);
    std::string p;
    bool r = g->generatePassphrase(p);
    /* HWID uses dmidecode via popen - succeeds if popen works.
       Consistency: success implies non-empty passphrase */
    ASSERT_TRUE(r == true);
    ASSERT_TRUE(!p.empty());
}

void test_sgx_runs() {
    auto g = PassphraseGeneratorFactory::createPassphraseGenerator(SGX_EncryptedFile);
    std::string p;
    bool r = g->generatePassphrase(p);
    /* SGX is a stub - returns true (implicit cast from string literal)
       but does not populate passphrase */
    ASSERT_TRUE(r == true);
}

void test_tpm_runs() {
    auto g = PassphraseGeneratorFactory::createPassphraseGenerator(TPM_EncryptedFile);
    std::string p;
    bool r = g->generatePassphrase(p);
    /* TPM is a stub - returns true (implicit cast from string literal)
       but does not populate passphrase */
    ASSERT_TRUE(r == true);
}

// ── Error path tests (run with LD_PRELOAD=mock_popen.so) ──

void test_hwid_popen_fail() {
    auto g = PassphraseGeneratorFactory::createPassphraseGenerator(HWID_Firmware);
    std::string p;
    bool r = g->generatePassphrase(p);
    // popen returns NULL -> runCmd returns false -> throw -> catch -> false
    ASSERT_TRUE(r == false);
}

int main() {
    const char* mock = std::getenv("MOCK_POPEN");

    // Always run factory tests
    test_factory_hwid();
    test_factory_sgx();
    test_factory_tpm();
    test_factory_default();
    test_factory_unique();

    if (mock && std::string(mock) == "1") {
        // Error path tests
        test_hwid_popen_fail();
    } else {
        // Normal path tests
        test_hwid_runs();
        test_sgx_runs();
        test_tpm_runs();
    }

    std::cout << "\n=== C++ Test Results ===" << std::endl;
    std::cout << "Mode:         " << (mock ? "error-path" : "normal") << std::endl;
    std::cout << "Tests run:    " << tests_run << std::endl;
    std::cout << "Tests passed: " << tests_passed << std::endl;
    std::cout << "Tests failed: " << tests_failed << std::endl;
    std::cout << "========================" << std::endl;
    return tests_failed > 0 ? 1 : 0;
}
