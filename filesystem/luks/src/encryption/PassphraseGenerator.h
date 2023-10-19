/*
 * Copyright (c) 2023 Wind River Systems, Inc.
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

enum PassphraseMechanism {
    HWID_Firmware,
    SGX_EncryptedFile,
    TPM_EncryptedFile
};

// PassphraseGenerator abstract class
class PassphraseGenerator {
 public:
    virtual bool generatePassphrase(std::string &shaPhrase) = 0;
};

class PassphraseGeneratorFactory {
 public:
    static std::unique_ptr<PassphraseGenerator>
           createPassphraseGenerator(PassphraseMechanism mechanism);
};

#endif  // PASSPHRASE_GENERATOR_H
