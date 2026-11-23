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

// TPM passphrase generator. The passphrase is stored in a TPM NV index
// under the owner hierarchy (see TpmConstants.h).
class TPMPassphraseGenerator : public PassphraseGenerator {
 public:
    bool generatePassphrase(std::string &shaPhrase) override;

    // TPM-specific operations
    bool detectTPM();
    bool unsealPassphrase(std::string &passphrase);
    bool sealPassphrase(const std::string &passphrase);
    bool removeNVIndex();
    bool nvIndexExists();
    bool nvIndexOwnedByUs();

 private:
    bool runTpmCmd(const std::string &cmd, std::string &result,
                   int timeoutSecs);
    bool generateRandomBytes(std::string &bytes, int count);
    bool defineNVIndex();
    bool writeNVIndex(const std::string &data);
    bool readNVIndex(std::string &data);
    void clearSensitiveString(std::string &s);
};

class PassphraseGeneratorFactory {
 public:
    static std::unique_ptr<PassphraseGenerator>
           createPassphraseGenerator(PassphraseMechanism mechanism);
};

#endif  // PASSPHRASE_GENERATOR_H
