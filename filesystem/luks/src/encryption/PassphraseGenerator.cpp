/*
 * Copyright (c) 2023 Wind River Systems, Inc.
*
* SPDX-License-Identifier: Apache-2.0
*
 */

/**
  * @SourceFile
  * Passphrase Generator.
  *
  */

#include <string>
#include <unistd.h>
#include <memory>
#include <exception>
#include <iostream>
#include "PassphraseGenerator.h"
using namespace std;


// HWID passphrase generator
class HWIDPassphraseGenerator : public PassphraseGenerator {
 public:
    bool generatePassphrase(string &shaPhrase) override {
      // Implementation of HWID-based passphrase generation
      try {

        string system_uuid, baseboard_serial, chassis_serial;

        if (!runCmd("dmidecode -s system-uuid", system_uuid))
            throw runtime_error("system_uuid: Command execution failed.");
        if (!runCmd("dmidecode -s baseboard-serial-number", baseboard_serial))
            throw runtime_error("baseboard-serial: Command execution failed.");
        if (!runCmd("dmidecode -s chassis-serial-number", chassis_serial))
            throw runtime_error("chassis-serial: Command execution failed.");

        string concat_string = system_uuid + baseboard_serial +
                                     chassis_serial;

        // Generate SHA for the concatenated output string.

        if (!runCmd("echo -n \"" + concat_string + "\" | sha256sum",
                     shaPhrase))
            throw runtime_error("SHA256 execution failed.");

        return true;
      } catch (const exception &ex) {
        cerr << "Error: " << ex.what() << endl;
        return false;
      }
    }

 private:
    bool runCmd(const string &cmd, string &result) {
       const int MAX_BUF = 256;
       char buf[MAX_BUF];
       result = "";

       FILE *fstream = popen(cmd.c_str(), "r");
       if (!fstream)
           return false;

       if (fstream) {
           while (!feof(fstream)) {
               if (fgets(buf, MAX_BUF, fstream) != NULL)
                     result.append(buf);
           }
           pclose(fstream);
       }
       if (!result.empty())
              result = result.substr(0, result.size() - 1);
    return true;
    }
};


// SGX passphrase generator
class SGXPassphraseGenerator : public PassphraseGenerator {
 public:
    bool generatePassphrase(string &shaPhrase) override {
        // Pretend like shaPhrase is used, to avoid getting the
        // "unused parameter" message from the compiler, which results in
        // compliation errors due to -Werror.
        (void)shaPhrase;
        // Implement SGX-based passphrase generation
        // Replace this with actual generated passphrase
        return "sgx_generated_passphrase";
    }
};

// TPM passphrase generator
class TPMPassphraseGenerator : public PassphraseGenerator {
 public:
    bool generatePassphrase(string &shaPhrase) override {
        // Pretend like shaPhrase is used, to avoid getting the
        // "unused parameter" message from the compiler, which results in
        // compliation errors due to -Werror.
        (void)shaPhrase;
        // Implement TPM-based passphrase generation
        // Replace this with actual generated passphrase
        return "tpm_generated_passphrase";
    }
};


unique_ptr<PassphraseGenerator> PassphraseGeneratorFactory
    ::createPassphraseGenerator(PassphraseMechanism mechanism) {
        switch (mechanism) {
            case HWID_Firmware:
                return std::unique_ptr<HWIDPassphraseGenerator>(new
                                       HWIDPassphraseGenerator());
            case SGX_EncryptedFile:
                return std::unique_ptr<SGXPassphraseGenerator>(new
                                       SGXPassphraseGenerator());
            case TPM_EncryptedFile:
                return std::unique_ptr<TPMPassphraseGenerator>(new
                                       TPMPassphraseGenerator());
            default:
                return std::unique_ptr<HWIDPassphraseGenerator>(new
                                       HWIDPassphraseGenerator());
        }
}

