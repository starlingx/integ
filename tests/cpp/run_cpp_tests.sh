#!/bin/bash
#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
# Build and run C++ tests with coverage using gcov/lcov
set -e

PROJ_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC_DIR="$PROJ_ROOT/filesystem/luks/src/encryption"
TEST_DIR="$PROJ_ROOT/tests/cpp"
OUT_DIR="$PROJ_ROOT/UTCoverage"
BUILD_DIR="$TEST_DIR/build"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$OUT_DIR"

echo "=== Building C++ tests with coverage ==="

for tool in g++ gcov lcov genhtml; do
    if ! command -v $tool &>/dev/null; then
        echo "WARNING: $tool not found, skipping C++ coverage"
        echo "$tool not available" > "$OUT_DIR/coverage_c_skipped.txt"
        exit 0
    fi
done

# ── PassphraseGenerator tests (existing) ──

g++ -std=c++14 --coverage -fprofile-arcs -ftest-coverage \
    -I"$SRC_DIR" \
    -o "$BUILD_DIR/test_passphrase" \
    "$TEST_DIR/test_passphrase_generator.cpp" \
    "$SRC_DIR/PassphraseGenerator.cpp" \
    2>&1

g++ -std=c++14 -shared -fPIC \
    -o "$BUILD_DIR/mock_popen.so" \
    "$TEST_DIR/mock_popen.cpp" 2>&1

echo "=== Running PassphraseGenerator normal tests ==="
cd "$BUILD_DIR"
./test_passphrase 2>&1 | tee "$OUT_DIR/coverage_c_test_results.txt"

echo "=== Running PassphraseGenerator error-path tests ==="
MOCK_POPEN=1 LD_PRELOAD="$BUILD_DIR/mock_popen.so" \
    ./test_passphrase 2>&1 | tee -a "$OUT_DIR/coverage_c_test_results.txt"

# ── luks-fs-mgr tests (new) ──

echo "=== Building luks-fs-mgr mock library ==="
g++ -std=c++14 -shared -fPIC \
    -o "$BUILD_DIR/mock_system.so" \
    "$TEST_DIR/mock_system.cpp" 2>&1

# Also compile as object for direct linking (enables call-tracking assertions)
g++ -std=c++14 --coverage -fprofile-arcs -ftest-coverage \
    -c "$TEST_DIR/mock_system.cpp" \
    -o "$BUILD_DIR/mock_system.o" 2>&1

echo "=== Building luks-fs-mgr tests ==="
# Compile luks-fs-mgr.cpp as object with main renamed
g++ -std=c++14 --coverage -fprofile-arcs -ftest-coverage \
    -Dmain=luks_main \
    -I"$SRC_DIR" $(pkg-config --cflags json-c) \
    -c "$SRC_DIR/luks-fs-mgr.cpp" \
    -o "$BUILD_DIR/luks-fs-mgr.o" 2>&1

# Compile PassphraseGenerator.cpp as object (needed by luks-fs-mgr)
g++ -std=c++14 --coverage -fprofile-arcs -ftest-coverage \
    -I"$SRC_DIR" \
    -c "$SRC_DIR/PassphraseGenerator.cpp" \
    -o "$BUILD_DIR/PassphraseGenerator.o" 2>&1

# Compile test harness
g++ -std=c++14 --coverage -fprofile-arcs -ftest-coverage \
    -I"$SRC_DIR" $(pkg-config --cflags json-c) \
    -c "$TEST_DIR/test_luks_fs_mgr.cpp" \
    -o "$BUILD_DIR/test_luks_fs_mgr.o" 2>&1

# Link everything (mock linked directly for call-tracking assertions)
g++ -std=c++14 --coverage \
    "$BUILD_DIR/test_luks_fs_mgr.o" \
    "$BUILD_DIR/luks-fs-mgr.o" \
    "$BUILD_DIR/PassphraseGenerator.o" \
    "$BUILD_DIR/mock_system.o" \
    $(pkg-config --libs json-c) -ldaemon \
    -o "$BUILD_DIR/test_luks_fs_mgr" 2>&1

echo "=== Running luks-fs-mgr tests ==="
cd "$BUILD_DIR"
./test_luks_fs_mgr 2>&1 | tee -a "$OUT_DIR/coverage_c_test_results.txt"

# ── Coverage report generation ──

echo "=== Generating coverage report ==="
# Collect all gcda from build dir
lcov --capture --directory "$BUILD_DIR" \
     --output-file "$BUILD_DIR/coverage_raw.info" \
     --rc branch_coverage=1 \
     --ignore-errors source 2>/dev/null || true

if [ -f "$BUILD_DIR/coverage_raw.info" ] && [ -s "$BUILD_DIR/coverage_raw.info" ]; then
    lcov --extract "$BUILD_DIR/coverage_raw.info" \
         "*encryption/PassphraseGenerator*" \
         "*encryption/luks-fs-mgr*" \
         --output-file "$BUILD_DIR/coverage_filtered.info" \
         --rc branch_coverage=1 \
         --ignore-errors unused 2>/dev/null || true
    if [ -f "$BUILD_DIR/coverage_filtered.info" ] && [ -s "$BUILD_DIR/coverage_filtered.info" ]; then
        genhtml "$BUILD_DIR/coverage_filtered.info" \
                --output-directory "$OUT_DIR/htmlcov_cpp" \
                --rc branch_coverage=1 2>/dev/null || true
        # Text summary
        lcov --summary "$BUILD_DIR/coverage_filtered.info" \
             --rc branch_coverage=1 2>&1 | tee "$OUT_DIR/coverage_c_report.txt"
    fi
fi

rm -f "$SRC_DIR"/*.gcda "$SRC_DIR"/*.gcno 2>/dev/null || true
echo "=== C++ coverage complete ==="
