/*
 * Copyright (c) 2023,2026 Wind River Systems, Inc.
*
* SPDX-License-Identifier: Apache-2.0
*
 */

/**
  * @Header File
  * Passphrase Generator Header file.
  *
  */

#ifndef PASSPHRASE_GENERATOR_H
#define PASSPHRASE_GENERATOR_H

#include <string>
#include <memory>

enum PassphraseMechanism {
    HWID_Firmware,          // legacy: SHA256(uuid + baseboard + chassis)
    HWID_SystemUUID,        // new: SHA256(system-uuid)
    SGX_EncryptedFile,
    TPM_EncryptedFile
};

// PassphraseGenerator abstract class
class PassphraseGenerator {
 public:
    virtual ~PassphraseGenerator() = default;
    virtual bool generatePassphrase(std::string &shaPhrase) = 0;
    virtual bool generateLegacyPassphrase(std::string &shaPhrase) {
        (void)shaPhrase;
        return false;
    }
};

class PassphraseGeneratorFactory {
 public:
    static std::unique_ptr<PassphraseGenerator>
           createPassphraseGenerator(PassphraseMechanism mechanism);
};

#endif  // PASSPHRASE_GENERATOR_H
