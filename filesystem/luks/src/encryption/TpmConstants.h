/*
 * Copyright (c) 2026 Wind River Systems, Inc.
*
* SPDX-License-Identifier: Apache-2.0
*
 */

/**
  * @Header File
  * TPM constants used by the TPM passphrase generator.
  *
  */

#ifndef TPM_CONSTANTS_H
#define TPM_CONSTANTS_H

#include <cstdint>
#include <string>

// NV index that holds the LUKS passphrase (owner hierarchy)
static const uint32_t TPM_NV_INDEX = 0x01800001;
static const char* const TPM_NV_INDEX_STR = "0x01800001";

// Passphrase size in bytes
static const int TPM_PASSPHRASE_SIZE = 32;

// NV index allocation size in bytes
static const int TPM_NV_SIZE = 32;

// Timeouts and retries
static const int TPM_DETECT_TIMEOUT_SECS = 10;
static const int TPM_OP_TIMEOUT_SECS = 5;
static const int TPM_MAX_RETRIES = 3;
static const int TPM_RETRY_DELAY_SECS = 2;

// TCTI for the tpm2-abrmd resource manager
static const char* const TPM_TCTI = "tabrmd:";

// Shared platform owner-auth file. Created by platform provisioning;
// luks-fs-mgr only reads it.
static const char* const TPM_OWNER_AUTH_FILE =
    "/etc/platform/.tpm_owner_auth";

// Read the shared platform owner auth. Never generates or changes it.
bool readPlatformOwnerAuth(std::string &auth);

#endif  // TPM_CONSTANTS_H
