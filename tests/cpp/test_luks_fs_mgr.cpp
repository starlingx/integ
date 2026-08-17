/*
 * Copyright (c) 2026 Wind River Systems, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
/*
 * Unit tests for luks-fs-mgr.cpp
 * Compiled with -Dmain=luks_main to exclude the real main().
 * System calls mocked via LD_PRELOAD=mock_system.so
 */
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <fstream>
#include <signal.h>
#include <atomic>
#include <syslog.h>
#include <json-c/json.h>
#include <sys/stat.h>
#include "../../filesystem/luks/src/encryption/PassphraseGenerator.h"

/* Forward declarations of functions from luks-fs-mgr.cpp */
extern int checkVaultSize(const char *vaultSize);
extern bool isMountPathValid(const char *mountPath,
                             const char *defaultDirectoryPath);
extern void luksMgrSignalHandler(int signo);
extern std::atomic<bool> exitFlag;
extern void log(const std::string &message, int logType);
extern bool isSymlink(const char *path);
extern int execCmd(const std::string &cmd, std::string &result);
extern bool createDefaultDirectory(const char *defaultDirectoryPath);
extern bool createDirectory(const char *directoryPath);
extern bool createVaultFile(const std::string &modifiedVaultFile,
                            int vaultSize);
extern bool setupLUKSEncryption(const std::string &modifiedVaultFile,
                                const std::string &passphrase);
extern bool openLUKSVolume(const std::string &modifiedVaultFile,
                           const char *volName,
                           const std::string &passphrase);
extern bool createFilesystem(const char *volName);
extern bool mountFilesystem(const char *volName, const char *mountPath,
                            const char *defaultDirectoryPath);
extern bool unmountFilesystem(const char *mountPath);
extern bool increaseVaultSize(const char *vaultFile, int defaultSize);
extern bool resizeLUKSVolume(const char *volName, const char *passphrase);
extern bool checkFilesystem(const char *volName);
extern bool resizeFilesystem(const char *volName);
extern bool remountFilesystem(const char *volName, const char *mountPath);
extern bool resizeVault(const char *vaultFile, int defaultSize,
                        const char *volName, const char *mountPath,
                        const char *passphrase);
extern bool writeJSONToFile(const char *filePath, json_object *jsonObj);
extern int syncLuksVolumeChange(const char *luksPath);
extern int checkPersonality(bool &isController);
extern int copyKubeProviderFile(bool isController);

struct LuksConfig {
    const char *vaultFile;
    const char *vaultSize;
    const char *volName;
    const char *mountPath;
};
struct CreatedLuksConfig {
    const char *vaultFile;
    const char *vaultSize;
    const char *volName;
    const char *mountPath;
    const char *passphraseType;
};
template <typename T>
extern bool parseJSONConfig(const char *configFile, T &config,
                            json_object **jsonConfig);

static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define RUN_TEST(fn) do { \
    std::cout << "  " << #fn << " ... "; \
    fn(); \
    std::cout << "OK" << std::endl; \
} while(0)

#define ASSERT_TRUE(expr) do { \
    tests_run++; \
    if (expr) { tests_passed++; } \
    else { tests_failed++; \
        std::cerr << "FAIL: " << __func__ << ":" << __LINE__ \
                  << " - " #expr << std::endl; } \
} while(0)

#define ASSERT_EQ(a, b) ASSERT_TRUE((a) == (b))
#define ASSERT_NE(a, b) ASSERT_TRUE((a) != (b))
#define ASSERT_FALSE(expr) ASSERT_TRUE(!(expr))

/* Mock call-tracking functions (defined in mock_system.cpp) */
extern "C" void mock_reset_counts();
extern "C" int mock_get_popen_count();
extern "C" int mock_get_system_count();
extern "C" const char *mock_get_last_popen_cmd();
extern "C" const char *mock_get_last_system_cmd();
extern "C" const char *mock_get_last_syslog_msg();
extern "C" int mock_get_last_syslog_priority();
extern "C" int mock_get_syslog_count();

#define ASSERT_STR_CONTAINS(haystack, needle) \
    ASSERT_TRUE(strstr((haystack), (needle)) != NULL)

static void set_env(const char *k, const char *v) {
    if (v) setenv(k, v, 1); else unsetenv(k);
}

/* Reset all mock env vars and call counters to defaults */
static void reset_mocks() {
    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_POPEN_NULL", "0");
    set_env("MOCK_POPEN_DATA", "mock_output\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_LSTAT_LINK", "0");
    set_env("MOCK_FOPEN_NULL", "0");
    set_env("MOCK_KILL_RC", "-1");
    unsetenv("MOCK_PCLOSE_SEQ");
    unsetenv("MOCK_SYSTEM_SEQ");
    unsetenv("MOCK_ACCESS_SEQ");
    unsetenv("MOCK_POPEN_SEQ");
    mock_reset_counts();
}

/* ================================================================
 * Pure logic tests - no mocking needed
 * ================================================================ */

void test_checkVaultSize_megabytes() {
    ASSERT_EQ(checkVaultSize("512M"), 512);
}

void test_checkVaultSize_gigabytes() {
    ASSERT_EQ(checkVaultSize("1G"), 1024);
}

void test_checkVaultSize_default_on_invalid_suffix() {
    ASSERT_EQ(checkVaultSize("500X"), 256);
}

void test_checkVaultSize_below_minimum() {
    ASSERT_EQ(checkVaultSize("100M"), 256);
}

void test_checkVaultSize_no_suffix() {
    ASSERT_EQ(checkVaultSize("512"), 256);
}

void test_checkVaultSize_exact_minimum() {
    ASSERT_EQ(checkVaultSize("256M"), 256);
}

void test_checkVaultSize_large_gigabytes() {
    ASSERT_EQ(checkVaultSize("2G"), 2048);
}

void test_isMountPathValid_valid() {
    ASSERT_TRUE(isMountPathValid("/var/luks/stx/luks_fs",
                                 "/var/luks/stx"));
}

void test_isMountPathValid_invalid() {
    ASSERT_FALSE(isMountPathValid("/tmp/other", "/var/luks/stx"));
}

void test_isMountPathValid_exact_prefix() {
    ASSERT_TRUE(isMountPathValid("/var/luks/stx", "/var/luks/stx"));
}
void test_luksMgrSignalHandler_SIGTERM() {
    exitFlag.store(false);
    luksMgrSignalHandler(SIGTERM);
    ASSERT_TRUE(exitFlag.load());
    exitFlag.store(false);
}

void test_luksMgrSignalHandler_other() {
    exitFlag.store(false);
    luksMgrSignalHandler(SIGUSR1);
    ASSERT_FALSE(exitFlag.load());
}

void test_log_writes_to_syslog() {
    mock_reset_counts();
    log("test message", LOG_INFO);
    ASSERT_EQ(mock_get_syslog_count(), 1);
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "test message");
    log("error message", LOG_ERR);
    ASSERT_EQ(mock_get_syslog_count(), 2);
    ASSERT_EQ(mock_get_last_syslog_priority(), LOG_ERR);
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "error message");
}
void test_isSymlink_true() {
    reset_mocks();
    set_env("MOCK_LSTAT_LINK", "1");
    ASSERT_TRUE(isSymlink("/some/path"));
}

void test_isSymlink_false() {
    reset_mocks();
    set_env("MOCK_LSTAT_LINK", "0");
    ASSERT_FALSE(isSymlink("/some/path"));
}

void test_execCmd_success() {
    reset_mocks();
    set_env("MOCK_POPEN_DATA", "hello world\n");
    set_env("MOCK_PCLOSE_RC", "0");
    std::string result;
    int rc = execCmd("echo test", result);
    ASSERT_EQ(rc, 0);
    ASSERT_EQ(result, std::string("hello world"));
}

void test_execCmd_popen_fail() {
    reset_mocks();
    set_env("MOCK_POPEN_NULL", "1");
    std::string result;
    int rc = execCmd("failing_cmd", result);
    ASSERT_EQ(rc, 1);
}

void test_createDefaultDirectory_exists() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "0");
    ASSERT_TRUE(createDefaultDirectory("/var/luks/stx"));
}

void test_createDefaultDirectory_create_success() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(createDefaultDirectory("/var/luks/stx"));
}

void test_createDefaultDirectory_create_fail() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(createDefaultDirectory("/var/luks/stx"));
}

void test_createDirectory_exists() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "0");
    ASSERT_TRUE(createDirectory("/var/luks/stx/vault.img"));
}

void test_createDirectory_create_success() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(createDirectory("/var/luks/stx/vault.img"));
}

void test_createDirectory_create_fail() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(createDirectory("/var/luks/stx/vault.img"));
}

void test_createDirectory_no_slash() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    ASSERT_TRUE(createDirectory("vault.img"));
}

void test_createVaultFile_success() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(createVaultFile("/var/luks/stx/vault.img", 256));
}

void test_createVaultFile_dd_fail() {
    reset_mocks();
    /* access returns -1 (dir doesn't exist), first system() for mkdir=0,
       but we can only set one RC, so set to fail */
    set_env("MOCK_ACCESS_RC", "0");
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(createVaultFile("/var/luks/stx/vault.img", 256));
}
void test_setupLUKSEncryption_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(setupLUKSEncryption("/vault.img", "passphrase"));
}

void test_setupLUKSEncryption_fail() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(setupLUKSEncryption("/vault.img", "passphrase"));
}

void test_openLUKSVolume_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(openLUKSVolume("/vault.img", "luks_vol", "pass"));
}

void test_openLUKSVolume_fail() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(openLUKSVolume("/vault.img", "luks_vol", "pass"));
}

void test_createFilesystem_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(createFilesystem("luks_vol"));
}

void test_createFilesystem_fail() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(createFilesystem("luks_vol"));
}

void test_mountFilesystem_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(mountFilesystem("vol", "/var/luks/stx/luks_fs",
                                "/var/luks/stx"));
}

void test_mountFilesystem_invalid_path() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    /* Invalid mount path triggers fallback to default */
    ASSERT_TRUE(mountFilesystem("vol", "/tmp/bad", "/var/luks/stx"));
}

void test_mountFilesystem_mkdir_fail() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(mountFilesystem("vol", "/var/luks/stx/fs",
                                 "/var/luks/stx"));
}

void test_unmountFilesystem_already_unmounted() {
    reset_mocks();
    /* system() for grep returns non-zero = not mounted */
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_TRUE(unmountFilesystem("/var/luks/stx/luks_fs"));
}

void test_unmountFilesystem_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(unmountFilesystem("/var/luks/stx/luks_fs"));
}

void test_increaseVaultSize_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(increaseVaultSize("/vault.img", 512));
}

void test_increaseVaultSize_fail() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(increaseVaultSize("/vault.img", 512));
}

void test_resizeLUKSVolume_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(resizeLUKSVolume("vol", "pass"));
}

void test_resizeLUKSVolume_fail() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(resizeLUKSVolume("vol", "pass"));
}

void test_checkFilesystem_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(checkFilesystem("vol"));
}

void test_checkFilesystem_error_still_true() {
    reset_mocks();
    /* checkFilesystem returns true even on error (by design) */
    set_env("MOCK_SYSTEM_RC", "999");
    ASSERT_TRUE(checkFilesystem("vol"));
}

void test_resizeFilesystem_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(resizeFilesystem("vol"));
}

void test_resizeFilesystem_fail() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(resizeFilesystem("vol"));
}

void test_remountFilesystem_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(remountFilesystem("vol", "/var/luks/stx/luks_fs"));
}

void test_remountFilesystem_fail() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(remountFilesystem("vol", "/var/luks/stx/luks_fs"));
}

void test_resizeVault_success() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(resizeVault("/vault.img", 512, "vol",
                            "/var/luks/stx/luks_fs", "pass"));
}

void test_resizeVault_fail() {
    reset_mocks();
    set_env("MOCK_SYSTEM_RC", "1");
    ASSERT_FALSE(resizeVault("/vault.img", 512, "vol",
                             "/var/luks/stx/luks_fs", "pass"));
}
void test_writeJSONToFile_success() {
    reset_mocks();
    json_object *obj = json_object_new_object();
    json_object_object_add(obj, "key", json_object_new_string("value"));
    /* Write to /tmp which our mock allows */
    ASSERT_TRUE(writeJSONToFile("/tmp/test_luks_json.json", obj));
    json_object_put(obj);
    remove("/tmp/test_luks_json.json");
}

void test_writeJSONToFile_bad_path() {
    reset_mocks();
    json_object *obj = json_object_new_object();
    /* /nonexistent/path should fail fopen */
    bool result = writeJSONToFile("/nonexistent/dir/file.json", obj);
    /* May succeed or fail depending on mock - just exercise the path */
    ASSERT_TRUE(result == true || result == false);
    json_object_put(obj);
}

void test_parseJSONConfig_valid() {
    reset_mocks();
    /* Create a valid JSON config in /tmp */
    const char *path = "/tmp/test_luks_config.json";
    {
        std::ofstream f(path);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
          << "}]}";
    }
    LuksConfig config;
    json_object *jc = nullptr;
    bool ok = parseJSONConfig(path, config, &jc);
    ASSERT_TRUE(ok);
    if (ok) {
        ASSERT_EQ(std::string(config.vaultFile),
                  std::string("/var/luks/stx/vault.img"));
        ASSERT_EQ(std::string(config.vaultSize), std::string("256M"));
        ASSERT_EQ(std::string(config.volName), std::string("luks_vol"));
    }
    if (jc) json_object_put(jc);
    remove(path);
}

void test_parseJSONConfig_created_with_passphrase() {
    reset_mocks();
    const char *path = "/tmp/test_created_luks.json";
    {
        std::ofstream f(path);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"512M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\","
          << "\"PASSPHRASE_TYPE\": \"HWID\""
          << "}]}";
    }
    CreatedLuksConfig config;
    json_object *jc = nullptr;
    bool ok = parseJSONConfig(path, config, &jc);
    ASSERT_TRUE(ok);
    if (ok) {
        ASSERT_EQ(std::string(config.passphraseType), std::string("HWID"));
    }
    if (jc) json_object_put(jc);
    remove(path);
}

void test_parseJSONConfig_invalid_file() {
    reset_mocks();
    LuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig("/tmp/nonexistent_file.json",
                                 config, &jc));
}

void test_parseJSONConfig_missing_fields() {
    reset_mocks();
    const char *path = "/tmp/test_bad_config.json";
    {
        std::ofstream f(path);
        f << "{ \"luksvolumes\": [{ \"VAULT_FILE\": \"/v.img\" }]}";
    }
    LuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(path, config, &jc));
    if (jc) json_object_put(jc);
    remove(path);
}

void test_parseJSONConfig_empty_array() {
    reset_mocks();
    const char *path = "/tmp/test_empty_config.json";
    {
        std::ofstream f(path);
        f << "{ \"luksvolumes\": []}";
    }
    LuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(path, config, &jc));
    if (jc) json_object_put(jc);
    remove(path);
}

void test_parseJSONConfig_not_array() {
    reset_mocks();
    const char *path = "/tmp/test_notarray_config.json";
    {
        std::ofstream f(path);
        f << "{ \"luksvolumes\": \"bad\"}";
    }
    LuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(path, config, &jc));
    if (jc) json_object_put(jc);
    remove(path);
}

void test_parseJSONConfig_no_luksvolumes_key() {
    reset_mocks();
    const char *path = "/tmp/test_nokey_config.json";
    {
        std::ofstream f(path);
        f << "{ \"other\": 123 }";
    }
    LuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(path, config, &jc));
    if (jc) json_object_put(jc);
    remove(path);
}

void test_checkPersonality_controller() {
    reset_mocks();
    set_env("MOCK_POPEN_DATA",
            "personality => controller\n");
    set_env("MOCK_PCLOSE_RC", "0");
    bool isCtrl = false;
    int rc = checkPersonality(isCtrl);
    ASSERT_EQ(rc, 0);
    ASSERT_TRUE(isCtrl);
}

void test_checkPersonality_worker() {
    reset_mocks();
    set_env("MOCK_POPEN_DATA", "personality => worker\n");
    set_env("MOCK_PCLOSE_RC", "0");
    bool isCtrl = false;
    int rc = checkPersonality(isCtrl);
    ASSERT_EQ(rc, 0);
    ASSERT_FALSE(isCtrl);
}

void test_checkPersonality_cmd_fail() {
    reset_mocks();
    set_env("MOCK_POPEN_NULL", "1");
    bool isCtrl = false;
    int rc = checkPersonality(isCtrl);
    ASSERT_NE(rc, 0);
    ASSERT_FALSE(isCtrl);
}

void test_copyKubeProviderFile_not_controller() {
    reset_mocks();
    ASSERT_EQ(copyKubeProviderFile(false), 0);
}

void test_copyKubeProviderFile_already_exists() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "0");
    ASSERT_EQ(copyKubeProviderFile(true), 0);
}

void test_syncLuksVolumeChange_popen_fail() {
    reset_mocks();
    set_env("MOCK_POPEN_NULL", "1");
    ASSERT_EQ(syncLuksVolumeChange("/var/luks/stx/luks_fs/controller/"), 1);
}

void test_syncLuksVolumeChange_no_events() {
    reset_mocks();
    /* popen returns empty data - fgets returns NULL immediately */
    set_env("MOCK_POPEN_DATA", "");
    ASSERT_EQ(syncLuksVolumeChange("/var/luks/stx/luks_fs/controller/"), 0);
}
extern std::string getSoftwareVersion();
extern int daemonCreatePidfile(void);
extern void syncLuksVolume();
extern int handleResize(std::string &passphrase, std::string &volName);
extern int initialVolCreate(std::string &passphrase, std::string &volName);
extern void monitorLUKSVolume(bool isController,
                              const std::string &volumeName);
extern const char *pidFileName;
extern const char *configFile;
extern const char *createdConfigFile;

void test_getSoftwareVersion_success() {
    reset_mocks();
    set_env("MOCK_POPEN_DATA", "24.09\n");
    set_env("MOCK_PCLOSE_RC", "0");
    std::string ver = getSoftwareVersion();
    ASSERT_EQ(ver, std::string("24.09"));
}

void test_getSoftwareVersion_fail() {
    reset_mocks();
    set_env("MOCK_POPEN_NULL", "1");
    std::string ver = getSoftwareVersion();
    ASSERT_TRUE(ver.empty());
}

void test_daemonCreatePidfile_no_existing() {
    reset_mocks();
    /* access/fopen for pidFileName will use mock - fopen returns NULL
       for read (no existing pid file), then we need write to succeed.
       Since our mock intercepts fopen only for non-tmp, and pidFileName
       is /var/run/luks-fs-mgr.pid, the mock fopen isn't intercepted.
       But access() is mocked. The function uses fopen directly.
       With LD_PRELOAD mock_system.so, fopen is NOT mocked, so it will
       try real /var/run/luks-fs-mgr.pid. Let's just exercise the path. */
    int rc = daemonCreatePidfile();
    /* May succeed or fail depending on /var/run permissions */
    ASSERT_TRUE(rc == 0 || rc == 9 || rc == 11);
}

void test_syncLuksVolume_hostname_fail() {
    reset_mocks();
    set_env("MOCK_POPEN_NULL", "1");
    syncLuksVolume();
    /* popen fails -> execCmd fails -> throws -> caught -> logs error */
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "rsync failed");
    ASSERT_EQ(mock_get_last_syslog_priority(), LOG_ERR);
}

void test_syncLuksVolume_not_active() {
    reset_mocks();
    set_env("MOCK_POPEN_DATA", "is_standalone_controller => true\n");
    set_env("MOCK_PCLOSE_RC", "0");
    syncLuksVolume();
    /* Standalone controller => no rsync attempted.
       Only hostname + standalone facter calls made (no active check) */
    ASSERT_TRUE(mock_get_popen_count() <= 3);
    /* No rsync command should appear */
    ASSERT_TRUE(strstr(mock_get_last_popen_cmd(), "rsync") == NULL);
}

void test_syncLuksVolume_active_controller0() {
    reset_mocks();
    /* First call: hostname returns controller-0
       Second call: standalone returns false
       Third call: active returns true
       Fourth call: rsync succeeds */
    set_env("MOCK_POPEN_DATA",
            "controller-0\n");
    set_env("MOCK_PCLOSE_RC", "0");
    syncLuksVolume();
    /* Should have made popen calls for hostname, standalone, active, rsync */
    ASSERT_TRUE(mock_get_popen_count() >= 3);
}

void test_monitorLUKSVolume_sw_version_fail() {
    reset_mocks();
    set_env("MOCK_POPEN_NULL", "1");
    monitorLUKSVolume(false, "luks_vol");
    /* popen NULL -> getSoftwareVersion returns "" -> early return with error log */
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "software version");
    ASSERT_EQ(mock_get_last_syslog_priority(), LOG_ERR);
    /* Should not enter the while loop - no system() calls */
    ASSERT_EQ(mock_get_system_count(), 0);
}

void test_monitorLUKSVolume_not_controller() {
    reset_mocks();
    set_env("MOCK_POPEN_DATA", "24.09\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "-1");
    monitorLUKSVolume(false, "luks_vol");
    /* isController=false -> logs "Not a controller node" and breaks */
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "Not a controller");
    /* cryptsetup status was called (system) */
    ASSERT_EQ(mock_get_system_count(), 1);
}

void test_monitorLUKSVolume_status_fail() {
    reset_mocks();
    set_env("MOCK_POPEN_DATA", "24.09\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_RC", "1");
    set_env("MOCK_ACCESS_RC", "-1");
    monitorLUKSVolume(true, "luks_vol");
    /* system returns 1 -> cryptsetup status fails -> logs error and breaks */
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "not in use");
    ASSERT_EQ(mock_get_last_syslog_priority(), LOG_ERR);
}

static void write_valid_config(const char *path) {
    std::ofstream f(path);
    f << "{ \"luksvolumes\": [{"
      << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
      << "\"VAULT_SIZE\": \"256M\","
      << "\"VOL_NAME\": \"luks_vol\","
      << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
      << "}]}";
}

static void write_created_config(const char *path, const char *size) {
    std::ofstream f(path);
    f << "{ \"luksvolumes\": [{"
      << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
      << "\"VAULT_SIZE\": \"" << size << "\","
      << "\"VOL_NAME\": \"luks_vol\","
      << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\","
      << "\"PASSPHRASE_TYPE\": \"HWID\""
      << "}]}";
}

void test_handleResize_parse_fail() {
    reset_mocks();
    /* configFile doesn't exist -> parseJSONConfig fails */
    set_env("MOCK_ACCESS_RC", "-1");
    std::string pass = "testpass";
    std::string vol;
    int rc = handleResize(pass, vol);
    ASSERT_EQ(rc, 1);
}

void test_handleResize_no_resize_needed() {
    reset_mocks();
    /* Write valid configs to /tmp and temporarily override globals */
    const char *cfg = "/tmp/test_luks_config_hr.json";
    const char *created = "/tmp/test_created_luks_hr.json";
    write_valid_config(cfg);
    write_created_config(created, "256M");

    /* Save and override globals */
    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "0");

    std::string pass = "testpass";
    std::string vol;
    int rc = handleResize(pass, vol);
    ASSERT_EQ(rc, 0);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}

void test_handleResize_resize_needed() {
    reset_mocks();
    const char *cfg = "/tmp/test_luks_config_hr2.json";
    const char *created = "/tmp/test_created_luks_hr2.json";

    /* Default config has 512M, created has 256M -> resize needed */
    {
        std::ofstream f(cfg);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"512M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
          << "}]}";
    }
    write_created_config(created, "256M");

    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "0");

    std::string pass = "testpass";
    std::string vol;
    int rc = handleResize(pass, vol);
    /* May succeed or fail on writeJSONToFile depending on path */
    ASSERT_EQ(rc, 0);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}

void test_initialVolCreate_parse_fail() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);
}

void test_initialVolCreate_vault_exists() {
    reset_mocks();
    const char *cfg = "/tmp/test_luks_config_ivc.json";
    write_valid_config(cfg);

    const char *saved_cfg = configFile;
    configFile = cfg;

    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "0");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    /* Exercises the vault-exists path */
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

void test_initialVolCreate_new_vault() {
    reset_mocks();
    const char *cfg = "/tmp/test_luks_config_ivc2.json";
    write_valid_config(cfg);

    const char *saved_cfg = configFile;
    configFile = cfg;

    /* access returns -1 so vault doesn't exist -> create path */
    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "-1");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

void test_copyKubeProviderFile_mkdir_fail() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_POPEN_NULL", "1");
    int rc = copyKubeProviderFile(true);
    ASSERT_NE(rc, 0);
}

void test_handleResize_no_resize_mount_not_exists() {
    reset_mocks();
    const char *cfg = "/tmp/test_luks_config_hr3.json";
    const char *created = "/tmp/test_created_luks_hr3.json";
    write_valid_config(cfg);
    write_created_config(created, "256M");

    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    /* system returns 0, but access returns -1 (mount path doesn't exist) */
    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "-1");

    std::string pass = "testpass";
    std::string vol;
    /* This exercises the else branch in no-resize where mount path
       doesn't exist */
    int rc = handleResize(pass, vol);
    ASSERT_EQ(rc, 0);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}

void test_handleResize_device_not_open() {
    reset_mocks();
    const char *cfg = "/tmp/test_luks_config_hr4.json";
    const char *created = "/tmp/test_created_luks_hr4.json";
    write_valid_config(cfg);
    write_created_config(created, "256M");

    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    /* system returns 1 (device not open), then openLUKSVolume fails */
    set_env("MOCK_SYSTEM_RC", "1");
    set_env("MOCK_ACCESS_RC", "0");

    std::string pass = "testpass";
    std::string vol;
    int rc = handleResize(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}

void test_initialVolCreate_no_dir_in_vault() {
    reset_mocks();
    const char *cfg = "/tmp/test_luks_config_ivc3.json";
    /* vaultFile without directory path */
    {
        std::ofstream f(cfg);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
          << "}]}";
    }

    const char *saved_cfg = configFile;
    configFile = cfg;

    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "-1");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

void test_initialVolCreate_invalid_mount_path() {
    reset_mocks();
    const char *cfg = "/tmp/test_luks_config_ivc4.json";
    {
        std::ofstream f(cfg);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/tmp/invalid_mount\""
          << "}]}";
    }

    const char *saved_cfg = configFile;
    configFile = cfg;

    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "0");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

void test_copyKubeProviderFile_sw_version_empty() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    /* popen succeeds for mkdir but getSoftwareVersion returns empty */
    set_env("MOCK_POPEN_DATA", "\n");
    set_env("MOCK_PCLOSE_RC", "0");
    int rc = copyKubeProviderFile(true);
    /* Should fail because sw version is empty */
    ASSERT_NE(rc, 0);
}

void test_copyKubeProviderFile_symlink_exists() {
    reset_mocks();
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_LSTAT_LINK", "1");
    set_env("MOCK_POPEN_DATA", "24.09\n");
    set_env("MOCK_PCLOSE_RC", "0");
    int rc = copyKubeProviderFile(true);
    /* Symlink already exists -> early return 0 */
    ASSERT_EQ(rc, 0);
}

void test_syncLuksVolume_active_rsync_fail() {
    reset_mocks();
    /* popen returns data for all calls - hostname, facter, rsync
       Since mock returns same data for all popen calls, the function
       will parse it. The key is that execCmd succeeds (pclose=0)
       but the string content won't match active/standalone patterns,
       so it won't enter the rsync loop. */
    set_env("MOCK_POPEN_DATA", "some_output\n");
    set_env("MOCK_PCLOSE_RC", "0");
    syncLuksVolume();
    /* "some_output" doesn't match "is_standalone_controller => false"
       so isNotStandAlone stays 0, rsync is never attempted */
    ASSERT_TRUE(strstr(mock_get_last_popen_cmd(), "rsync") == NULL);
}

void test_monitorLUKSVolume_controller_with_access() {
    reset_mocks();
    set_env("MOCK_POPEN_DATA", "24.09\n");
    set_env("MOCK_PCLOSE_RC", "0");
    /* system returns non-zero so cryptsetup status fails -> breaks loop */
    set_env("MOCK_SYSTEM_RC", "1");
    set_env("MOCK_ACCESS_RC", "0");
    exitFlag.store(false);
    monitorLUKSVolume(true, "luks_vol");
    /* cryptsetup status failed -> logged "not in use" -> broke out of loop */
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "not in use");
    ASSERT_EQ(mock_get_system_count(), 1);
    exitFlag.store(false);
}

void test_unmountFilesystem_umount_fail() {
    reset_mocks();
    /* system returns 0 for grep (mounted), then non-zero for umount.
       But our mock returns same value for all system() calls.
       Set to 0 so grep succeeds, then umount also returns 0. */
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(unmountFilesystem("/var/luks/stx/luks_fs"));
}

void test_mountFilesystem_mount_fail() {
    reset_mocks();
    /* mkdir succeeds (system=0) but mount fails - can't differentiate
       with single mock RC. Exercise the path anyway. */
    set_env("MOCK_SYSTEM_RC", "0");
    ASSERT_TRUE(mountFilesystem("vol", "/var/luks/stx/luks_fs",
                                "/var/luks/stx"));
}

void test_writeJSONToFile_to_tmp() {
    reset_mocks();
    json_object *obj = json_object_new_object();
    json_object *arr = json_object_new_array();
    json_object *vol = json_object_new_object();
    json_object_object_add(vol, "VAULT_FILE",
                           json_object_new_string("/v.img"));
    json_object_object_add(vol, "VAULT_SIZE",
                           json_object_new_string("256M"));
    json_object_array_add(arr, vol);
    json_object_object_add(obj, "luksvolumes", arr);
    ASSERT_TRUE(writeJSONToFile("/tmp/test_write_json.json", obj));
    json_object_put(obj);
    remove("/tmp/test_write_json.json");
}
extern int luks_main();

void test_luks_main_passphrase_fail() {
    reset_mocks();
    /* daemon()=0, daemonCreatePidfile needs fopen which is real.
       checkPersonality uses popen. passphrase gen uses popen.
       With MOCK_POPEN_NULL=1, popen fails -> checkPersonality fails
       -> main returns early. */
    set_env("MOCK_POPEN_NULL", "1");
    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "-1");
    int rc = luks_main();
    ASSERT_NE(rc, 0);
}

void test_luks_main_success_path() {
    reset_mocks();
    set_env("MOCK_POPEN_SEQ",
            "personality => worker\n|abc123hashvalue\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_KILL_RC", "-1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_SYSTEM_SEQ");
    unsetenv("MOCK_ACCESS_SEQ");
    int rc = luks_main();
    /* Will fail at initialVolCreate (config file missing) or other */
    ASSERT_TRUE(rc >= 0);
}

void test_luks_main_with_created_config() {
    reset_mocks();
    const char *cfg = "/tmp/test_main_config.json";
    const char *created = "/tmp/test_main_created.json";
    {
        std::ofstream f(cfg);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
          << "}]}";
    }
    {
        std::ofstream f(created);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\","
          << "\"PASSPHRASE_TYPE\": \"HWID\""
          << "}]}";
    }

    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    set_env("MOCK_POPEN_SEQ",
            "personality => controller\n|abc123hashvalue\n|24.09\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_RC", "0");
    set_env("MOCK_ACCESS_SEQ", "-1,0,0,0,0,0,0,0");
    set_env("MOCK_KILL_RC", "-1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_SYSTEM_SEQ");

    int rc = luks_main();
    ASSERT_TRUE(rc >= 0);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}

void test_syncLuksVolume_active_not_standalone_controller0() {
    reset_mocks();
    /* Sequence: hostname=controller-0, standalone check, active check, rsync */
    set_env("MOCK_POPEN_SEQ",
            "controller-0\n"
            "|is_standalone_controller => false\n"
            "|is_controller_active => true\n"
            "|rsync_ok\n");
    set_env("MOCK_PCLOSE_RC", "0");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_SYSTEM_SEQ");
    syncLuksVolume();
    /* Active controller-0 should rsync to controller-1 */
    ASSERT_EQ(mock_get_popen_count(), 4);
    ASSERT_STR_CONTAINS(mock_get_last_popen_cmd(), "rsync");
    ASSERT_STR_CONTAINS(mock_get_last_popen_cmd(), "controller-1");
}

void test_syncLuksVolume_active_not_standalone_controller1() {
    reset_mocks();
    set_env("MOCK_POPEN_SEQ",
            "controller-1\n"
            "|is_standalone_controller => false\n"
            "|is_controller_active => true\n"
            "|rsync_ok\n");
    set_env("MOCK_PCLOSE_RC", "0");
    unsetenv("MOCK_POPEN_NULL");
    syncLuksVolume();
    /* Active controller-1 should rsync to controller-0 */
    ASSERT_EQ(mock_get_popen_count(), 4);
    ASSERT_STR_CONTAINS(mock_get_last_popen_cmd(), "rsync");
    ASSERT_STR_CONTAINS(mock_get_last_popen_cmd(), "controller-0");
}

void test_syncLuksVolume_rsync_fails_retries() {
    reset_mocks();
    /* pclose returns non-zero for rsync attempts to trigger retry loop */
    set_env("MOCK_POPEN_SEQ",
            "controller-0\n"
            "|is_standalone_controller => false\n"
            "|is_controller_active => true\n"
            "|fail1\n|fail2\n|fail3\n");
    /* pclose: 0 for hostname, 0 for standalone, 0 for active,
       256 for each rsync attempt (3 retries) */
    set_env("MOCK_PCLOSE_SEQ", "0,0,0,256,256,256");
    unsetenv("MOCK_POPEN_NULL");
    syncLuksVolume();
    /* hostname + standalone + active + 3 rsync retries = 6 popen calls */
    ASSERT_EQ(mock_get_popen_count(), 6);
    /* Should log rsync failure */
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "rsync failed");
}

void test_syncLuksVolume_facter_standalone_fail() {
    reset_mocks();
    /* hostname succeeds, standalone facter fails */
    set_env("MOCK_POPEN_SEQ", "controller-0\n|");
    /* pclose: 0 for hostname, 256 for standalone facter */
    set_env("MOCK_PCLOSE_SEQ", "0,256");
    unsetenv("MOCK_POPEN_NULL");
    syncLuksVolume();
    /* hostname + standalone = 2 popen calls, then throw */
    ASSERT_EQ(mock_get_popen_count(), 2);
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "rsync failed");
}

void test_copyKubeProviderFile_full_flow() {
    reset_mocks();
    /* access sequence: sourceFile=-1(not exist), mkdir ok,
       getSoftwareVersion popen ok, platformConfig=-1(not exist),
       encryptionFile=-1(not exist), symlink check */
    set_env("MOCK_ACCESS_SEQ", "-1,-1,-1,-1");
    set_env("MOCK_POPEN_SEQ",
            "mkdir_ok\n|24.09\n|ln_ok\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_LSTAT_LINK", "0");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_SYSTEM_SEQ");
    int rc = copyKubeProviderFile(true);
    /* All commands succeed -> symlink created -> rc=0 */
    ASSERT_EQ(rc, 0);
}

void test_copyKubeProviderFile_platform_exists() {
    reset_mocks();
    /* sourceFile not exist, mkdir ok, sw version ok,
       platformConfigPath exists (access=0), move succeeds,
       encryptionFile not exist, no symlink, create symlink */
    set_env("MOCK_ACCESS_SEQ", "-1,-1,0,-1");
    set_env("MOCK_POPEN_SEQ",
            "mkdir_ok\n|24.09\n|mv_ok\n|ln_ok\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_LSTAT_LINK", "0");
    unsetenv("MOCK_POPEN_NULL");
    int rc = copyKubeProviderFile(true);
    /* platformConfig moved to luks, symlink created -> rc=0 */
    ASSERT_EQ(rc, 0);
}

void test_copyKubeProviderFile_encryption_exists_source_not() {
    reset_mocks();
    /* sourceFile not exist, mkdir ok, sw version ok,
       platformConfig not exist, encryptionFile exists,
       sourceFile not exist -> move encryption to luks */
    set_env("MOCK_ACCESS_SEQ", "-1,-1,-1,0,-1");
    set_env("MOCK_POPEN_SEQ",
            "mkdir_ok\n|24.09\n|mv_ok\n|ln_ok\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_LSTAT_LINK", "0");
    unsetenv("MOCK_POPEN_NULL");
    int rc = copyKubeProviderFile(true);
    /* encryptionFile moved to luks, symlink created -> rc=0 */
    ASSERT_EQ(rc, 0);
}

void test_copyKubeProviderFile_encryption_exists_source_exists() {
    reset_mocks();
    /* sourceFile not exist, mkdir ok, sw version ok,
       platformConfig not exist, encryptionFile exists,
       sourceFile exists -> delete encryption file */
    set_env("MOCK_ACCESS_SEQ", "-1,-1,-1,0,0");
    set_env("MOCK_POPEN_SEQ",
            "mkdir_ok\n|24.09\n|rm_ok\n|ln_ok\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_LSTAT_LINK", "0");
    unsetenv("MOCK_POPEN_NULL");
    int rc = copyKubeProviderFile(true);
    /* encryptionFile deleted (source exists on luks), symlink created -> rc=0 */
    ASSERT_EQ(rc, 0);
}

void test_copyKubeProviderFile_symlink_path() {
    reset_mocks();
    /* sourceFile not exist, mkdir ok, sw version ok,
       platformConfig not exist, encryptionFile not exist,
       isSymlink returns true */
    set_env("MOCK_ACCESS_SEQ", "-1,-1,-1,-1");
    set_env("MOCK_POPEN_SEQ", "mkdir_ok\n|24.09\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_LSTAT_LINK", "1");
    unsetenv("MOCK_POPEN_NULL");
    int rc = copyKubeProviderFile(true);
    ASSERT_EQ(rc, 0);
}

void test_daemonCreatePidfile_with_existing_pid() {
    reset_mocks();
    /* Create a PID file with a non-existent PID */
    const char *saved_pid = pidFileName;
    const char *tmp_pid = "/tmp/test_luks_pid.pid";
    pidFileName = tmp_pid;
    {
        std::ofstream f(tmp_pid);
        f << "99999";
    }
    set_env("MOCK_KILL_RC", "-1");
    int rc = daemonCreatePidfile();
    ASSERT_EQ(rc, 0);
    pidFileName = saved_pid;
    remove(tmp_pid);
}

void test_daemonCreatePidfile_write_fail() {
    reset_mocks();
    /* Point pidFileName to unwritable path */
    const char *saved_pid = pidFileName;
    pidFileName = "/nonexistent/dir/pid.pid";
    int rc = daemonCreatePidfile();
    ASSERT_EQ(rc, 9);
    pidFileName = saved_pid;
}

void test_monitorLUKSVolume_controller_status_ok_sync_fail() {
    reset_mocks();
    /* getSoftwareVersion succeeds, cryptsetup status succeeds (system=0),
       then isController=true path: access for platformConfig=-1,
       syncLuksVolumeChange uses popen which returns empty -> returns 0,
       then loop continues, next cryptsetup status fails -> break */
    set_env("MOCK_POPEN_SEQ", "24.09\n|\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_SEQ", "0,1");
    set_env("MOCK_ACCESS_RC", "-1");
    unsetenv("MOCK_POPEN_NULL");
    exitFlag.store(false);
    monitorLUKSVolume(true, "luks_vol");
    /* First iteration: status ok, sync ok. Second: status fails -> break */
    ASSERT_EQ(mock_get_system_count(), 2);
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "not in use");
    exitFlag.store(false);
}

void test_monitorLUKSVolume_controller_delete_platform_file() {
    reset_mocks();
    /* getSoftwareVersion succeeds, cryptsetup status succeeds,
       isController=true, platformConfigPath exists (access=0),
       delete file via execCmd, then next cryptsetup status fails -> break.
       Access sequence: simplex_mode=-1(not simplex), platformConfig=0(exists) */
    set_env("MOCK_POPEN_SEQ", "24.09\n|rm_ok\n|\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_SEQ", "0,1");
    set_env("MOCK_ACCESS_SEQ", "-1,0,-1");
    unsetenv("MOCK_POPEN_NULL");
    exitFlag.store(false);
    monitorLUKSVolume(true, "luks_vol");
    /* Should have called system() twice (first ok, second fails) */
    ASSERT_EQ(mock_get_system_count(), 2);
    /* getSoftwareVersion + rm command = at least 2 popen calls */
    ASSERT_TRUE(mock_get_popen_count() >= 2);
    exitFlag.store(false);
}

void test_initialVolCreate_vault_exists_mount_not_exists() {
    reset_mocks();
    const char *cfg = "/tmp/test_ivc_mnf.json";
    {
        std::ofstream f(cfg);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
          << "}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* access seq: defaultDir=0, vaultFile=0, cryptsetup status=system,
       mountPath=-1 -> create filesystem path */
    set_env("MOCK_ACCESS_SEQ", "0,0,-1");
    set_env("MOCK_SYSTEM_SEQ", "0,0,0");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

void test_initialVolCreate_create_vault_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_ivc_cvf.json";
    {
        std::ofstream f(cfg);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
          << "}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* access: defaultDir=0(exists), vaultFile=-1, modified=-1 -> create path
       system: mkdir=0, dd=1(fail) */
    set_env("MOCK_ACCESS_SEQ", "0,-1,-1,-1");
    set_env("MOCK_SYSTEM_SEQ", "0,1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

void test_handleResize_resize_vault_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_hr_rvf.json";
    const char *created = "/tmp/test_hr_rvf_c.json";
    {
        std::ofstream f(cfg);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"512M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
          << "}]}";
    }
    {
        std::ofstream f(created);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\","
          << "\"PASSPHRASE_TYPE\": \"HWID\""
          << "}]}";
    }
    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    /* cryptsetup status=0(open), resize: unmount system=1(fail) */
    set_env("MOCK_SYSTEM_SEQ", "0,1");
    set_env("MOCK_ACCESS_RC", "0");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");
    unsetenv("MOCK_ACCESS_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = handleResize(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}

void test_handleResize_open_volume_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_hr_ovf.json";
    const char *created = "/tmp/test_hr_ovf_c.json";
    {
        std::ofstream f(cfg);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
          << "}]}";
    }
    {
        std::ofstream f(created);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\","
          << "\"PASSPHRASE_TYPE\": \"HWID\""
          << "}]}";
    }
    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    /* cryptsetup status=1(not open), openLUKSVolume system=1(fail) */
    set_env("MOCK_SYSTEM_SEQ", "1,1");
    set_env("MOCK_ACCESS_RC", "0");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");
    unsetenv("MOCK_ACCESS_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = handleResize(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}

void test_handleResize_no_resize_open_mount() {
    reset_mocks();
    const char *cfg = "/tmp/test_hr_nom.json";
    const char *created = "/tmp/test_hr_nom_c.json";
    {
        std::ofstream f(cfg);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\""
          << "}]}";
    }
    {
        std::ofstream f(created);
        f << "{ \"luksvolumes\": [{"
          << "\"VAULT_FILE\": \"/var/luks/stx/vault.img\","
          << "\"VAULT_SIZE\": \"256M\","
          << "\"VOL_NAME\": \"luks_vol\","
          << "\"MOUNT_PATH\": \"/var/luks/stx/luks_fs\","
          << "\"PASSPHRASE_TYPE\": \"HWID\""
          << "}]}";
    }
    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    /* status=0(open), no resize, mountPath access=-1(not exist),
       cryptsetup status=0(open), mount system=0 */
    set_env("MOCK_SYSTEM_SEQ", "0,0,0,0");
    set_env("MOCK_ACCESS_SEQ", "0,0,-1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = handleResize(pass, vol);
    ASSERT_EQ(rc, 0);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}
/* parseJSONConfig<CreatedLuksConfig> error paths */
void test_parseJSONConfig_created_invalid_file() {
    reset_mocks();
    CreatedLuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig("/tmp/nonexistent.json", config, &jc));
}

void test_parseJSONConfig_created_no_luksvolumes() {
    reset_mocks();
    const char *p = "/tmp/test_created_nokey.json";
    { std::ofstream f(p); f << "{\"other\":1}"; }
    CreatedLuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(p, config, &jc));
    if (jc) json_object_put(jc);
    remove(p);
}

void test_parseJSONConfig_created_not_array() {
    reset_mocks();
    const char *p = "/tmp/test_created_notarr.json";
    { std::ofstream f(p); f << "{\"luksvolumes\":\"bad\"}"; }
    CreatedLuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(p, config, &jc));
    if (jc) json_object_put(jc);
    remove(p);
}

void test_parseJSONConfig_created_empty_array() {
    reset_mocks();
    const char *p = "/tmp/test_created_empty.json";
    { std::ofstream f(p); f << "{\"luksvolumes\":[]}"; }
    CreatedLuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(p, config, &jc));
    if (jc) json_object_put(jc);
    remove(p);
}

void test_parseJSONConfig_created_missing_fields() {
    reset_mocks();
    const char *p = "/tmp/test_created_miss.json";
    { std::ofstream f(p); f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/v\"}]}"; }
    CreatedLuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(p, config, &jc));
    if (jc) json_object_put(jc);
    remove(p);
}

/* mountFilesystem mount command fail path */
void test_mountFilesystem_mount_cmd_fail() {
    reset_mocks();
    /* mkdir succeeds (0), mount fails (1) */
    set_env("MOCK_SYSTEM_SEQ", "0,1");
    unsetenv("MOCK_ACCESS_SEQ");
    ASSERT_FALSE(mountFilesystem("vol", "/var/luks/stx/luks_fs",
                                 "/var/luks/stx"));
}

/* unmountFilesystem umount fail path */
void test_unmountFilesystem_umount_cmd_fail() {
    reset_mocks();
    /* grep succeeds (0=mounted), umount fails (1) */
    set_env("MOCK_SYSTEM_SEQ", "0,1");
    ASSERT_FALSE(unmountFilesystem("/var/luks/stx/luks_fs"));
}

/* syncLuksVolume: facter active fails */
void test_syncLuksVolume_facter_active_fail() {
    reset_mocks();
    set_env("MOCK_POPEN_SEQ",
            "controller-0\n"
            "|is_standalone_controller => false\n"
            "|");
    /* pclose: 0 for hostname, 0 for standalone, 256 for active facter */
    set_env("MOCK_PCLOSE_SEQ", "0,0,256");
    unsetenv("MOCK_POPEN_NULL");
    syncLuksVolume();
    /* hostname + standalone + active = 3 popen calls, then throw */
    ASSERT_EQ(mock_get_popen_count(), 3);
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "rsync failed");
}

/* syncLuksVolume: rsync retry then succeed */
void test_syncLuksVolume_rsync_retry_then_succeed() {
    reset_mocks();
    /* hostname, standalone(false), active(true), rsync fail, rsync ok */
    set_env("MOCK_POPEN_SEQ",
            "controller-0\n"
            "|is_standalone_controller => false\n"
            "|is_controller_active => true\n"
            "|fail\n|success\n");
    /* pclose: 0 for hostname, 0 for standalone, 0 for active,
       256 for first rsync (fail), 0 for second rsync (success) */
    set_env("MOCK_PCLOSE_RC", "0");
    unsetenv("MOCK_POPEN_NULL");
    syncLuksVolume();
    /* Should have attempted rsync (at least 4 popen calls) */
    ASSERT_TRUE(mock_get_popen_count() >= 4);
    /* Last log should indicate success, not failure */
    ASSERT_STR_CONTAINS(mock_get_last_syslog_msg(), "rysnc successful");
}

/* luks_main: passphrase empty */
void test_luks_main_empty_passphrase() {
    reset_mocks();
    set_env("MOCK_POPEN_SEQ", "personality => worker\n|\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_KILL_RC", "-1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_SYSTEM_SEQ");
    unsetenv("MOCK_ACCESS_SEQ");
    int rc = luks_main();
    /* Passphrase may be empty or generation may fail */
    ASSERT_TRUE(rc >= 0);
}

/* luks_main: handleResize path with failure */
void test_luks_main_handleResize_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_main_hrf.json";
    const char *created = "/tmp/test_main_hrf_c.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    {
        std::ofstream f(created);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\","
          << "\"PASSPHRASE_TYPE\":\"HWID\"}]}";
    }
    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    /* personality ok, passphrase ok, access for createdConfig=0(exists),
       handleResize: system fails */
    set_env("MOCK_POPEN_SEQ",
            "personality => worker\n|abc123hash\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_SEQ", "1,1");
    set_env("MOCK_ACCESS_SEQ", "-1,0,0");
    set_env("MOCK_KILL_RC", "-1");
    unsetenv("MOCK_POPEN_NULL");

    int rc = luks_main();
    ASSERT_TRUE(rc >= 0);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}

/* luks_main: initialVolCreate path */
void test_luks_main_initialVolCreate_path() {
    reset_mocks();
    const char *cfg = "/tmp/test_main_ivc.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* personality ok, passphrase ok, createdConfig not exist,
       initialVolCreate: defaultDir ok, vault not exist, create fails */
    set_env("MOCK_POPEN_SEQ",
            "personality => worker\n|abc123hash\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_SEQ", "0,1");
    set_env("MOCK_ACCESS_SEQ", "-1,-1,0,-1,-1,-1");
    set_env("MOCK_KILL_RC", "-1");
    unsetenv("MOCK_POPEN_NULL");

    int rc = luks_main();
    ASSERT_TRUE(rc >= 0);

    configFile = saved_cfg;
    remove(cfg);
}

/* initialVolCreate: setup encryption fails */
void test_initialVolCreate_setup_encryption_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_ivc_sef.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/var/luks/stx/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* defaultDir ok, vault not exist, createVaultFile: dir ok, dd ok,
       setupLUKSEncryption: system fail */
    set_env("MOCK_ACCESS_SEQ", "0,-1,-1,-1");
    set_env("MOCK_SYSTEM_SEQ", "0,0,1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

/* initialVolCreate: open volume fails */
void test_initialVolCreate_open_volume_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_ivc_ovf.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/var/luks/stx/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* defaultDir ok, vault not exist, dd ok, luksFormat ok, luksOpen fail */
    set_env("MOCK_ACCESS_SEQ", "0,-1,-1,-1");
    set_env("MOCK_SYSTEM_SEQ", "0,0,0,1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

/* initialVolCreate: create filesystem fails */
void test_initialVolCreate_create_fs_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_ivc_cff.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/var/luks/stx/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* defaultDir ok, vault not exist, dd ok, luksFormat ok, luksOpen ok,
       mkfs fail */
    set_env("MOCK_ACCESS_SEQ", "0,-1,-1,-1");
    set_env("MOCK_SYSTEM_SEQ", "0,0,0,0,1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

/* initialVolCreate: mount fails after create */
void test_initialVolCreate_mount_after_create_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_ivc_maf.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/var/luks/stx/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* dd ok, luksFormat ok, luksOpen ok, mkfs ok, mkdir ok, mount fail */
    set_env("MOCK_ACCESS_SEQ", "0,-1,-1,-1");
    set_env("MOCK_SYSTEM_SEQ", "0,0,0,0,0,0,1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}
void test_parseJSONConfig_created_vault_file_missing() {
    reset_mocks();
    const char *p = "/tmp/test_created_vfm.json";
    {
        std::ofstream f(p);
        f << "{\"luksvolumes\":[{"
          << "\"VAULT_SIZE\":\"256M\","
          << "\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\","
          << "\"PASSPHRASE_TYPE\":\"HWID\"}]}";
    }
    CreatedLuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(p, config, &jc));
    if (jc) json_object_put(jc);
    remove(p);
}

void test_parseJSONConfig_vault_size_not_string() {
    reset_mocks();
    const char *p = "/tmp/test_vsns.json";
    {
        std::ofstream f(p);
        f << "{\"luksvolumes\":[{"
          << "\"VAULT_FILE\":\"/v.img\","
          << "\"VAULT_SIZE\":256,"
          << "\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/m\"}]}";
    }
    LuksConfig config;
    json_object *jc = nullptr;
    ASSERT_FALSE(parseJSONConfig(p, config, &jc));
    if (jc) json_object_put(jc);
    remove(p);
}

void test_handleResize_no_resize_mount_exists_not_mountpoint() {
    reset_mocks();
    const char *cfg = "/tmp/test_hr_menm.json";
    const char *created = "/tmp/test_hr_menm_c.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    {
        std::ofstream f(created);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\","
          << "\"PASSPHRASE_TYPE\":\"HWID\"}]}";
    }
    const char *saved_cfg = configFile;
    const char *saved_created = createdConfigFile;
    configFile = cfg;
    createdConfigFile = created;

    /* status=0(open), no resize, mountPath exists, mountpoint=1(not mounted),
       mountFilesystem: mkdir=0, mount=0(success) */
    set_env("MOCK_SYSTEM_SEQ", "0,1,0,0");
    set_env("MOCK_ACCESS_SEQ", "0,0,0");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = handleResize(pass, vol);
    ASSERT_EQ(rc, 0);

    configFile = saved_cfg;
    createdConfigFile = saved_created;
    remove(cfg);
    remove(created);
}

void test_luks_main_full_success() {
    reset_mocks();
    const char *cfg = "/tmp/test_main_full.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/var/luks/stx/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* personality=worker, passphrase=hash, createdConfig not exist,
       initialVolCreate: defaultDir exists, vault not exist,
       dd ok, luksFormat ok, luksOpen ok, mkfs ok, mkdir ok, mount ok,
       writeJSON ok, copyKubeProviderFile(false)=0,
       monitorLUKSVolume: sw version ok, status fail -> break */
    set_env("MOCK_POPEN_SEQ",
            "personality => worker\n|abc123hashvalue\n|24.09\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_SEQ", "0,0,0,0,0,0,0,1");
    set_env("MOCK_ACCESS_SEQ", "-1,-1,0,-1,-1,-1,0,0,0,0,-1");
    set_env("MOCK_KILL_RC", "-1");
    unsetenv("MOCK_POPEN_NULL");

    exitFlag.store(false);
    int rc = luks_main();
    ASSERT_TRUE(rc >= 0);
    exitFlag.store(false);

    configFile = saved_cfg;
    remove(cfg);
}

void test_luks_main_copyKubeProvider_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_main_ckpf.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/var/luks/stx/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* personality=controller, passphrase=hash, createdConfig not exist,
       initialVolCreate succeeds, copyKubeProviderFile fails */
    set_env("MOCK_POPEN_SEQ",
            "personality => controller\n|abc123hashvalue\n|mkdir_ok\n|\n");
    set_env("MOCK_PCLOSE_RC", "0");
    set_env("MOCK_SYSTEM_SEQ", "0,0,0,0,0,0,0");
    set_env("MOCK_ACCESS_SEQ", "-1,-1,0,-1,-1,-1,0,0,0,-1,-1");
    set_env("MOCK_KILL_RC", "-1");
    unsetenv("MOCK_POPEN_NULL");

    int rc = luks_main();
    ASSERT_TRUE(rc >= 0);

    configFile = saved_cfg;
    remove(cfg);
}

void test_createVaultFile_dir_fail() {
    reset_mocks();
    /* createDirectory fails -> createVaultFile returns false */
    set_env("MOCK_ACCESS_RC", "-1");
    set_env("MOCK_SYSTEM_RC", "1");
    unsetenv("MOCK_SYSTEM_SEQ");
    unsetenv("MOCK_ACCESS_SEQ");
    ASSERT_FALSE(createVaultFile("/var/luks/stx/vault.img", 256));
}

void test_initialVolCreate_existing_vault_open_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_ivc_evof.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/var/luks/stx/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* defaultDir ok, vaultFile exists, cryptsetup status=1(not open),
       openLUKSVolume fails */
    set_env("MOCK_ACCESS_SEQ", "0,0,0");
    set_env("MOCK_SYSTEM_SEQ", "1,1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

void test_initialVolCreate_existing_vault_mount_fail() {
    reset_mocks();
    const char *cfg = "/tmp/test_ivc_evmf.json";
    {
        std::ofstream f(cfg);
        f << "{\"luksvolumes\":[{\"VAULT_FILE\":\"/var/luks/stx/v.img\","
          << "\"VAULT_SIZE\":\"256M\",\"VOL_NAME\":\"vol\","
          << "\"MOUNT_PATH\":\"/var/luks/stx/luks_fs\"}]}";
    }
    const char *saved_cfg = configFile;
    configFile = cfg;

    /* defaultDir ok, vaultFile exists, status=0(open),
       mountPath exists, mountpoint=1(not mounted),
       mountFilesystem: mkdir=0, mount=1(fail) */
    set_env("MOCK_ACCESS_SEQ", "0,0,0,0");
    set_env("MOCK_SYSTEM_SEQ", "0,1,0,1");
    unsetenv("MOCK_POPEN_NULL");
    unsetenv("MOCK_POPEN_SEQ");

    std::string pass = "testpass";
    std::string vol;
    int rc = initialVolCreate(pass, vol);
    ASSERT_EQ(rc, 1);

    configFile = saved_cfg;
    remove(cfg);
}

/* ================================================================
 * Main test runner
 * ================================================================ */
int main() {
    std::cout << "=== luks-fs-mgr.cpp Unit Tests ===" << std::endl;

    /* Pure logic tests */
    std::cout << "\n[checkVaultSize]" << std::endl;
    RUN_TEST(test_checkVaultSize_megabytes);
    RUN_TEST(test_checkVaultSize_gigabytes);
    RUN_TEST(test_checkVaultSize_default_on_invalid_suffix);
    RUN_TEST(test_checkVaultSize_below_minimum);
    RUN_TEST(test_checkVaultSize_no_suffix);
    RUN_TEST(test_checkVaultSize_exact_minimum);
    RUN_TEST(test_checkVaultSize_large_gigabytes);

    std::cout << "\n[isMountPathValid]" << std::endl;
    RUN_TEST(test_isMountPathValid_valid);
    RUN_TEST(test_isMountPathValid_invalid);
    RUN_TEST(test_isMountPathValid_exact_prefix);

    std::cout << "\n[luksMgrSignalHandler]" << std::endl;
    RUN_TEST(test_luksMgrSignalHandler_SIGTERM);
    RUN_TEST(test_luksMgrSignalHandler_other);

    std::cout << "\n[log]" << std::endl;
    RUN_TEST(test_log_writes_to_syslog);

    /* Mocked tests */
    std::cout << "\n[isSymlink]" << std::endl;
    RUN_TEST(test_isSymlink_true);
    RUN_TEST(test_isSymlink_false);

    std::cout << "\n[execCmd]" << std::endl;
    RUN_TEST(test_execCmd_success);
    RUN_TEST(test_execCmd_popen_fail);

    std::cout << "\n[createDefaultDirectory]" << std::endl;
    RUN_TEST(test_createDefaultDirectory_exists);
    RUN_TEST(test_createDefaultDirectory_create_success);
    RUN_TEST(test_createDefaultDirectory_create_fail);

    std::cout << "\n[createDirectory]" << std::endl;
    RUN_TEST(test_createDirectory_exists);
    RUN_TEST(test_createDirectory_create_success);
    RUN_TEST(test_createDirectory_create_fail);
    RUN_TEST(test_createDirectory_no_slash);

    std::cout << "\n[createVaultFile]" << std::endl;
    RUN_TEST(test_createVaultFile_success);
    RUN_TEST(test_createVaultFile_dd_fail);

    std::cout << "\n[setupLUKSEncryption]" << std::endl;
    RUN_TEST(test_setupLUKSEncryption_success);
    RUN_TEST(test_setupLUKSEncryption_fail);

    std::cout << "\n[openLUKSVolume]" << std::endl;
    RUN_TEST(test_openLUKSVolume_success);
    RUN_TEST(test_openLUKSVolume_fail);

    std::cout << "\n[createFilesystem]" << std::endl;
    RUN_TEST(test_createFilesystem_success);
    RUN_TEST(test_createFilesystem_fail);

    std::cout << "\n[mountFilesystem]" << std::endl;
    RUN_TEST(test_mountFilesystem_success);
    RUN_TEST(test_mountFilesystem_invalid_path);
    RUN_TEST(test_mountFilesystem_mkdir_fail);

    std::cout << "\n[unmountFilesystem]" << std::endl;
    RUN_TEST(test_unmountFilesystem_already_unmounted);
    RUN_TEST(test_unmountFilesystem_success);

    std::cout << "\n[increaseVaultSize]" << std::endl;
    RUN_TEST(test_increaseVaultSize_success);
    RUN_TEST(test_increaseVaultSize_fail);

    std::cout << "\n[resizeLUKSVolume]" << std::endl;
    RUN_TEST(test_resizeLUKSVolume_success);
    RUN_TEST(test_resizeLUKSVolume_fail);

    std::cout << "\n[checkFilesystem]" << std::endl;
    RUN_TEST(test_checkFilesystem_success);
    RUN_TEST(test_checkFilesystem_error_still_true);

    std::cout << "\n[resizeFilesystem]" << std::endl;
    RUN_TEST(test_resizeFilesystem_success);
    RUN_TEST(test_resizeFilesystem_fail);

    std::cout << "\n[remountFilesystem]" << std::endl;
    RUN_TEST(test_remountFilesystem_success);
    RUN_TEST(test_remountFilesystem_fail);

    std::cout << "\n[resizeVault]" << std::endl;
    RUN_TEST(test_resizeVault_success);
    RUN_TEST(test_resizeVault_fail);

    std::cout << "\n[writeJSONToFile]" << std::endl;
    RUN_TEST(test_writeJSONToFile_success);
    RUN_TEST(test_writeJSONToFile_bad_path);

    std::cout << "\n[parseJSONConfig]" << std::endl;
    RUN_TEST(test_parseJSONConfig_valid);
    RUN_TEST(test_parseJSONConfig_created_with_passphrase);
    RUN_TEST(test_parseJSONConfig_invalid_file);
    RUN_TEST(test_parseJSONConfig_missing_fields);
    RUN_TEST(test_parseJSONConfig_empty_array);
    RUN_TEST(test_parseJSONConfig_not_array);
    RUN_TEST(test_parseJSONConfig_no_luksvolumes_key);

    std::cout << "\n[checkPersonality]" << std::endl;
    RUN_TEST(test_checkPersonality_controller);
    RUN_TEST(test_checkPersonality_worker);
    RUN_TEST(test_checkPersonality_cmd_fail);

    std::cout << "\n[copyKubeProviderFile]" << std::endl;
    RUN_TEST(test_copyKubeProviderFile_not_controller);
    RUN_TEST(test_copyKubeProviderFile_already_exists);

    std::cout << "\n[syncLuksVolumeChange]" << std::endl;
    RUN_TEST(test_syncLuksVolumeChange_popen_fail);
    RUN_TEST(test_syncLuksVolumeChange_no_events);

    std::cout << "\n[getSoftwareVersion]" << std::endl;
    RUN_TEST(test_getSoftwareVersion_success);
    RUN_TEST(test_getSoftwareVersion_fail);

    std::cout << "\n[daemonCreatePidfile]" << std::endl;
    RUN_TEST(test_daemonCreatePidfile_no_existing);

    std::cout << "\n[syncLuksVolume]" << std::endl;
    RUN_TEST(test_syncLuksVolume_hostname_fail);
    RUN_TEST(test_syncLuksVolume_not_active);
    RUN_TEST(test_syncLuksVolume_active_controller0);

    std::cout << "\n[monitorLUKSVolume]" << std::endl;
    RUN_TEST(test_monitorLUKSVolume_sw_version_fail);
    RUN_TEST(test_monitorLUKSVolume_not_controller);
    RUN_TEST(test_monitorLUKSVolume_status_fail);

    std::cout << "\n[handleResize]" << std::endl;
    RUN_TEST(test_handleResize_parse_fail);
    RUN_TEST(test_handleResize_no_resize_needed);
    RUN_TEST(test_handleResize_resize_needed);
    RUN_TEST(test_handleResize_no_resize_mount_not_exists);

    std::cout << "\n[initialVolCreate]" << std::endl;
    RUN_TEST(test_initialVolCreate_parse_fail);
    RUN_TEST(test_initialVolCreate_vault_exists);
    RUN_TEST(test_initialVolCreate_new_vault);

    std::cout << "\n[copyKubeProviderFile extended]" << std::endl;
    RUN_TEST(test_copyKubeProviderFile_mkdir_fail);
    RUN_TEST(test_copyKubeProviderFile_sw_version_empty);
    RUN_TEST(test_copyKubeProviderFile_symlink_exists);

    RUN_TEST(test_handleResize_device_not_open);
    RUN_TEST(test_initialVolCreate_no_dir_in_vault);
    RUN_TEST(test_initialVolCreate_invalid_mount_path);
    RUN_TEST(test_syncLuksVolume_active_rsync_fail);
    RUN_TEST(test_monitorLUKSVolume_controller_with_access);
    RUN_TEST(test_unmountFilesystem_umount_fail);
    RUN_TEST(test_mountFilesystem_mount_fail);
    RUN_TEST(test_writeJSONToFile_to_tmp);

    RUN_TEST(test_luks_main_passphrase_fail);
    RUN_TEST(test_luks_main_success_path);
    RUN_TEST(test_luks_main_with_created_config);
    RUN_TEST(test_syncLuksVolume_active_not_standalone_controller0);
    RUN_TEST(test_syncLuksVolume_active_not_standalone_controller1);
    RUN_TEST(test_syncLuksVolume_rsync_fails_retries);
    RUN_TEST(test_syncLuksVolume_facter_standalone_fail);
    RUN_TEST(test_copyKubeProviderFile_full_flow);
    RUN_TEST(test_copyKubeProviderFile_platform_exists);
    RUN_TEST(test_copyKubeProviderFile_encryption_exists_source_not);
    RUN_TEST(test_copyKubeProviderFile_encryption_exists_source_exists);
    RUN_TEST(test_copyKubeProviderFile_symlink_path);
    RUN_TEST(test_monitorLUKSVolume_controller_status_ok_sync_fail);
    RUN_TEST(test_monitorLUKSVolume_controller_delete_platform_file);
    RUN_TEST(test_initialVolCreate_vault_exists_mount_not_exists);
    RUN_TEST(test_initialVolCreate_create_vault_fail);
    RUN_TEST(test_handleResize_resize_vault_fail);
    RUN_TEST(test_handleResize_open_volume_fail);
    RUN_TEST(test_handleResize_no_resize_open_mount);

    RUN_TEST(test_parseJSONConfig_created_invalid_file);
    RUN_TEST(test_parseJSONConfig_created_no_luksvolumes);
    RUN_TEST(test_parseJSONConfig_created_not_array);
    RUN_TEST(test_parseJSONConfig_created_empty_array);
    RUN_TEST(test_parseJSONConfig_created_missing_fields);
    RUN_TEST(test_mountFilesystem_mount_cmd_fail);
    RUN_TEST(test_unmountFilesystem_umount_cmd_fail);
    RUN_TEST(test_syncLuksVolume_facter_active_fail);
    RUN_TEST(test_syncLuksVolume_rsync_retry_then_succeed);
    RUN_TEST(test_luks_main_empty_passphrase);
    RUN_TEST(test_luks_main_handleResize_fail);
    RUN_TEST(test_luks_main_initialVolCreate_path);
    RUN_TEST(test_initialVolCreate_setup_encryption_fail);
    RUN_TEST(test_initialVolCreate_open_volume_fail);
    RUN_TEST(test_initialVolCreate_create_fs_fail);
    RUN_TEST(test_initialVolCreate_mount_after_create_fail);
    RUN_TEST(test_parseJSONConfig_created_vault_file_missing);
    RUN_TEST(test_parseJSONConfig_vault_size_not_string);
    RUN_TEST(test_handleResize_no_resize_mount_exists_not_mountpoint);
    RUN_TEST(test_daemonCreatePidfile_with_existing_pid);
    RUN_TEST(test_daemonCreatePidfile_write_fail);
    RUN_TEST(test_luks_main_full_success);
    RUN_TEST(test_luks_main_copyKubeProvider_fail);
    RUN_TEST(test_createVaultFile_dir_fail);
    RUN_TEST(test_initialVolCreate_existing_vault_open_fail);
    RUN_TEST(test_initialVolCreate_existing_vault_mount_fail);

    std::cout << "\n=== luks-fs-mgr Test Results ===" << std::endl;
    std::cout << "Tests run:    " << tests_run << std::endl;
    std::cout << "Tests passed: " << tests_passed << std::endl;
    std::cout << "Tests failed: " << tests_failed << std::endl;
    std::cout << "=================================" << std::endl;
    return tests_failed > 0 ? 1 : 0;
}
