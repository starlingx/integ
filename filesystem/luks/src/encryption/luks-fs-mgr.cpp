/*
 * Copyright (c) 2023 Wind River Systems, Inc.
*
* SPDX-License-Identifier: Apache-2.0
*
 */

/**
  * @file
  * StarlingX Luks FileSystem Management Service
  *
  */

#include <iostream>
#include <string>
#include <cstdlib>
#include <json-c/json.h>
#include <syslog.h>
#include <unistd.h>
#include <cstring>
#include "PassphraseGenerator.h"

using namespace std;

// Global constants
const char *configFile = "/etc/luks-fs-mgr.d/luks_config.json";
const char *defaultDirectoryPath = "/var/luks/stx";
const char *defaultMountPath = "/var/luks/stx/luks_fs";

// Define a struct to hold configuration variables
struct LuksConfig {
    const char *vaultFile;
    const char *vaultSize;
    const char *volName;
    const char *mountPath;
};

/* ***********************************************************************
 *
 * Name       : log
 *
 * Description: Defined to log info/error messages using the 'syslog' utility.
 *
 * ************************************************************************/

void log(const string &message, int logType) {
    openlog("luks-fs-mgr", LOG_PID | LOG_NDELAY, LOG_DAEMON);
    syslog(logType, "%s", message.c_str());
    closelog();
}

/* ***********************************************************************
 *
 * Name       : parseJSONConfig
 *
 * Description: This function parses a JSON configuration file (luks_config.json)
 *              and extracts LUKS volume attributes, such as vault file,
 *              vault size, volume name, and mount path.
 *
 * ************************************************************************/

bool parseJSONConfig(const char *configFile, LuksConfig &luksConfig,
                     json_object **jsonConfig) {
    bool valid = true;
    *jsonConfig = json_object_from_file(configFile);
    if (*jsonConfig == nullptr) {
        log("Error opening or parsing config file", LOG_ERR);
        return false;
    }

    json_object *luksvolumes;
    if (!json_object_object_get_ex(*jsonConfig, "luksvolumes", &luksvolumes)) {
        log("Unable to get 'luksvolumes' array from JSON", LOG_ERR);
        return false;
    }

    if (!json_object_is_type(luksvolumes, json_type_array)) {
        log("'luksvolumes' is not an array", LOG_ERR);
        return false;
    }

    int numVolumes = json_object_array_length(luksvolumes);
    if (numVolumes == 0) {
        log("'luksvolumes' array is empty", LOG_ERR);
        return false;
    }

    json_object *volumeObj = json_object_array_get_idx(luksvolumes, 0);

    json_object *vaultFileObj = json_object_object_get(volumeObj, "VAULT_FILE");
    json_object *vaultSizeObj = json_object_object_get(volumeObj, "VAULT_SIZE");
    json_object *volNameObj = json_object_object_get(volumeObj, "VOL_NAME");
    json_object *mountPathObj = json_object_object_get(volumeObj, "MOUNT_PATH");

    if (!vaultFileObj || json_object_get_type(vaultFileObj)
                         != json_type_string) {
        log(" - 'VAULT_FILE' attribute is missing or not a string.", LOG_ERR);
        valid = false;
    }
    if (!vaultSizeObj || json_object_get_type(vaultSizeObj)
                         != json_type_string) {
        log(" - 'VAULT_SIZE' attribute is missing or not a string.", LOG_ERR);
        valid = false;
    }
    if (!volNameObj || json_object_get_type(volNameObj)
                       != json_type_string) {
        log(" - 'VOL_NAME' attribute is missing or not a string.", LOG_ERR);
        valid = false;
    }
    if (!mountPathObj || json_object_get_type(mountPathObj)
                         != json_type_string) {
        log(" - 'MOUNT_PATH' attribute is missing or not a string.", LOG_ERR);
        valid = false;
    }

    if (!valid) {
        log("Missing or invalid attributes in JSON configuration", LOG_ERR);
        return false;
    }

    luksConfig.vaultFile = json_object_get_string(vaultFileObj);
    luksConfig.vaultSize = json_object_get_string(vaultSizeObj);
    luksConfig.volName = json_object_get_string(volNameObj);
    luksConfig.mountPath = json_object_get_string(mountPathObj);

    return true;
}

/* ***********************************************************************
 *
 * Name       : createDefaultDirectory
 *
 * Description: This function is to establish the directory structure required
 *              for mounting the LUKS-encrypted filesystem. It helps ensure
 *              that the specified directory path (defaultDirectoryPath) exists.
 *
 * ************************************************************************/

bool createDefaultDirectory(const char *defaultDirectoryPath) {
    if (access(defaultDirectoryPath, F_OK) == 0) {
        // Default directory already exists
        return true;
    } else {
        string mkdirCommand = "mkdir -p " + string(defaultDirectoryPath);
        int status = system(mkdirCommand.c_str());
        // An exit status of zero indicates success, and a nonzero value
        // indicates failure.
        if (status != 0) {
            log("Error creating default mount directory: " +
                      string(defaultDirectoryPath), LOG_ERR);
            log("Create directory failed with status: " +
                      to_string(status), LOG_ERR);
            return false;
        }
        return true;
    }
}

/* ***********************************************************************
 *
 * Name       :  createDirectory
 *
 * Description:  This function is to ensure that a directory exists before
 *               creating a LUKS vault file within it. It handles the creation
 *               of both the specified directory and any parent directories
 *               if necessary.
 *
 * ************************************************************************/

bool createDirectory(const char *directoryPath) {
    if (access(directoryPath, F_OK) == 0) {
        // Directory already exists
        return true;
    } else {
        string vaultDirectory = directoryPath;
        size_t lastSlashPos = vaultDirectory.rfind('/');
        if (lastSlashPos != string::npos) {
            string directoryPath = vaultDirectory.substr(0, lastSlashPos);
            string mkdirCommand = "mkdir -p " + directoryPath;
            int status = system(mkdirCommand.c_str());
            // An exit status of zero indicates success, and a nonzero value
            // indicates failure.
            if (status != 0) {
                log("Error creating directory for vault file: " +
                           string(directoryPath), LOG_ERR);
                log("Create directory failed with status: " +
                           to_string(status), LOG_ERR);
                return false;
            }
        }
        return true;
    }
}

/* ***********************************************************************
 *
 * Name       : createVaultFile
 *
 * Description: This function is responsible for creating a LUKS vault file
 *              with a specified size and a random key using the dd and
 *              cryptsetup utilities.
 *
 * Note:       If the size is not specified or is invalid, it sets a default
 *             size of 256 megabytes.
 *
 * ************************************************************************/

bool createVaultFile(const string &modifiedVaultFile, const char *vaultSize) {
    // Create the directory path if it doesn't exist
    if (!createDirectory(modifiedVaultFile.c_str())) {
        // Directory creation failed
        return false;
    }

    // Convert const char* to string
    string vaultSizeStr = vaultSize;
    // Find the first non-numeric character
    size_t firstNonNumeric = vaultSizeStr.find_first_not_of("0123456789");
    if (firstNonNumeric != string::npos) {
        // Extract the numeric portion and the suffix
        string sizeStr = vaultSizeStr.substr(0, firstNonNumeric);
        string suffix = vaultSizeStr.substr(firstNonNumeric);

        // Convert the extracted string to an integer
        int size = stoi(sizeStr);

        // Determine the multiplier based on the suffix
        if (suffix == "M") {
            // Megabytes
            size *= 1;
        } else if (suffix == "G") {
            // Gigabytes
            size *= 1024;
        } else {
            string log_message = "Invalid vault file size provided: " +
                                  string(vaultSize) +
                          ".Using default size for vault file creation.";
            log(log_message, LOG_INFO);
            // Set to the default size
            size = 256;
        }

        // Set a minimum size of 256MB
        if (size < 256) {
            log("Vault file size below default: The specified size is less"
                     " than the default size of 256MB. Using default size for"
                     " vault file creation.", LOG_INFO);
            // Set to the minimum default size
            size = 256;
        }
        string command = "dd if=/dev/urandom of=" + string(modifiedVaultFile) +
                         " bs=1M count=" + to_string(size);
        int status = system(command.c_str());
        // An exit status of zero indicates success, and a nonzero value
        //  indicates failure.
        if (status == 0) {
            // Command executed successfully
            return true;
        } else {
            log("Error creating LUKS vault image file: " +
                       string(modifiedVaultFile), LOG_ERR);
            log("Command failed with return status: " +
                       to_string(status), LOG_ERR);
            return false;
         }
    } else {
        log("Invalid vault file size format: No size type found."
                 " Using default size of 256MB", LOG_INFO);
        string command = "dd if=/dev/urandom of=" + string(modifiedVaultFile) +
                         " bs=1M count=256";
        int status = system(command.c_str());
        // An exit status of zero indicates success, and a nonzero value
        //  indicates failure.
        if (status == 0) {
            // Command executed successfully
            return true;
        } else {
            // Command failed
            log("Error creating LUKS vault image file: " +
                       string(modifiedVaultFile), LOG_ERR);
            log("Command failed with return status:" +
                       to_string(status), LOG_ERR);
            return false;
         }
     }
}

/* ***********************************************************************
 *
 * Name       : setupLUKSEncryption
 *
 * Description: This function is to secure the data within the vault file by
 *              encrypting it using LUKS encryption. It prepares the vault
 *              file for use as an encrypted volume.
 *
 * ************************************************************************/

bool setupLUKSEncryption(const string &modifiedVaultFile,
                         const string &passphrase) {
    string command = "echo -n \"" + string(passphrase) +
                     "\" | cryptsetup luksFormat " +
                     string(modifiedVaultFile) + " -";
    int status = system(command.c_str());
    // Cryptsetup returns 0 on success and a non-zero value on error.
    // Return codes on failure:
    // 1 wrong parameters, 2 no permission (badpassphrase),
    // 3 out of memory, 4 wrong device specified,
    // 5 device already exists or device is busy.
    if (status == 0) {
        // Command executed successfully
        return true;
    } else {
        // Command failed
        log("Error setting up LUKS encryption for vault file: " +
                         string(modifiedVaultFile), LOG_ERR);
        log("Command failed with return status: " +
                         to_string(status), LOG_ERR);
        return false;
    }
}

/* ***********************************************************************
 *
 * Name       : openLUKSVolume
 *
 * Description: This function is to make the encrypted data within the LUKS
 *              vault accessible as a device that can be used for file
 *              operations.
 *
 * ************************************************************************/

bool openLUKSVolume(const string &modifiedVaultFile, const char *volName,
                    const string &passphrase) {
    string command = "echo -n \"" + string(passphrase) +
                     "\" | cryptsetup luksOpen " +
                     string(modifiedVaultFile) + " " + string(volName);
    int status = system(command.c_str());
    // Cryptsetup returns 0 on success and a non-zero value on error.
    // Return codes on failure:
    // 1 wrong parameters, 2 no permission (badpassphrase),
    // 3 out of memory, 4 wrong device specified,
    // 5 device already exists or device is busy.
    if (status == 0) {
        // Command executed successfully
        return true;
    } else {
        // Command failed
        log("Error opening LUKS volume for volume: " +
                           string(volName), LOG_ERR);
        log("Command failed with return status: " +
                           to_string(status), LOG_ERR);
        return false;
    }
}

/* ***********************************************************************
 *
 * Name       : createFilesystem
 *
 * Description: This function is responsible for creating an Ext4 filesystem
 *              on a specified LUKS volume.
 *
 * ************************************************************************/

bool createFilesystem(const char *volName) {
    string mkfs_command = "mkfs.ext4 /dev/mapper/" + string(volName);
    // Execute the mkfs command and capture the return status
    int status = system(mkfs_command.c_str());
    // The exit status returned by mkfs is 0 on success and 1 on failure.
    if (status == 0) {
        // Command executed successfully
        return true;
    } else {
        // Command failed
        log("Error creating filesystem for volume: " +
                             string(volName), LOG_ERR);
        log("Command failed with return status: " +
                             to_string(status), LOG_ERR);
        return false;
    }
}

/* ***********************************************************************
 *
 * Name       : isMountPathValid
 *
 * Description: This function is to determine whether the provided mount path
 *              is within the expected directory structure or if it needs to
 *              be adjusted to a default mount path.
 *
 * ************************************************************************/

bool isMountPathValid(const char *mountPath, const char *defaultDirectoryPath) {
    // Check if the provided mount path starts with the default directory path
    if (strncmp(mountPath, defaultDirectoryPath,
                strlen(defaultDirectoryPath)) != 0) {
        return false;
    }
    return true;
}

/* ***********************************************************************
 *
 * Name       : mountFilesystem
 *
 * Description: This function is responsible for mounting the LUKS-encrypted
 *              filesystem to a specified or default mount path.
 *
 * ************************************************************************/

bool mountFilesystem(const char *volName, const char *mountPath,
                     const char *defaultDirectoryPath) {
    if (!isMountPathValid(mountPath, defaultDirectoryPath)) {
        log("Mount path is not valid, using default mount path.", LOG_INFO);
        mountPath = defaultMountPath;  // Use default mount path
    }

    string mkdir_command = "mkdir -p " + string(mountPath);
    int status_check = system(mkdir_command.c_str());
    // An exit status of zero indicates success, and a nonzero value
    // indicates failure.
    if (status_check != 0) {
        log("Creation of mount path directory failed with return"
                  "status: " + to_string(status_check), LOG_ERR);
        return false;
    }

    string mount_command = "mount /dev/mapper/" + string(volName) + " " +
                            string(mountPath);
    int status = system(mount_command.c_str());
    // On success, zero is returned.  On error, -1 is returned, and
    // errno is set to indicate the error.
    if (status == 0) {
        log("Mounting filesystem successful.", LOG_INFO);
        return true;
    } else {
        log("Error mounting filesystem for volume: " +
                                string(volName), LOG_ERR);
        log("Mount command failed with return status: " +
                               to_string(status), LOG_ERR);
        return false;
     }
}

int main() {
    json_object *jsonConfig;
    LuksConfig luksConfig;
    string passphrase;

    PassphraseMechanism selectedMechanism = HWID_Firmware;
    auto passphraseGenerator =
      PassphraseGeneratorFactory::createPassphraseGenerator(selectedMechanism);
    bool ret = passphraseGenerator->generatePassphrase(passphrase);

    if (passphrase.empty() || ret == false) {
        log("Passphrase generation failed or"
                            " returned an empty passphrase.", LOG_ERR);
        json_object_put(jsonConfig);
        return 1;
    }

    // Create default directory for the service to create FS and mount
    if (!createDefaultDirectory(defaultDirectoryPath)) {
        json_object_put(jsonConfig);
        return 1;
    }

    // Parse JSON configuration and extract volume attributes
    if (!parseJSONConfig(configFile, luksConfig, &jsonConfig)) {
        // Release the JSON object memory
        json_object_put(jsonConfig);
        return 1;
    }
    // Logging the successfully parsed attributes
    string log_message = "Vault File: " + string(luksConfig.vaultFile) +
                         ", Vault Size: " + string(luksConfig.vaultSize) +
                         ", Volume Name: " + string(luksConfig.volName) +
                         ", Mount Path: " + string(luksConfig.mountPath);
    log(log_message, LOG_INFO);

    // Create a new string to hold the path+file
    string modifiedVaultFile = luksConfig.vaultFile;
    // Check if directory path is provided in vaultFile
    size_t lastSlashPos = modifiedVaultFile.rfind('/');
    if (lastSlashPos == string::npos) {
        // No directory path provided, use default directory
        modifiedVaultFile = "/var/luks/stx/" + modifiedVaultFile;
    }

    // Check if the vault file exists
    if ((access(luksConfig.vaultFile, F_OK) == 0) ||
               (access(modifiedVaultFile.c_str(), F_OK) == 0)) {
        // The vault file exists, proceed to unseal
        string statusCommand = "sudo cryptsetup status " +
            string(luksConfig.volName) + " 2>/dev/null";
        int status = system(statusCommand.c_str());
        // Cryptsetup returns 0 on success and a non-zero value on error.
        // Return codes on failure:
        // 1 wrong parameters, 2 no permission (badpassphrase),
        // 3 out of memory, 4 wrong device specified,
        // 5 device already exists or device is busy.
        if (status == 0) {
            log("LUKS device is already open", LOG_INFO);
        } else {
            log("LUKS device is not open. Try opening", LOG_INFO);
            if (!openLUKSVolume(modifiedVaultFile.c_str(), luksConfig.volName,
                                passphrase.c_str())) {
                json_object_put(jsonConfig);
                return 1;
            }
            log("LUKS device is successfully opened", LOG_INFO);
        }
        // Check if the mount path exists
        if (access(luksConfig.mountPath, F_OK) == 0) {
        string mount_command = "mountpoint -q " + string(luksConfig.mountPath);
            int mountpoint_status = system(mount_command.c_str());
            // mountpoint has the following exit status values:
            // 0: success; the directory is a mountpoint,
            // or device is block device
            // 1: failure; incorrect invocation, permissions or system error
            // 32: failure; the directory is not a mountpoint,
            // or device is not a block device on
            if (mountpoint_status != 0) {
                // Mount path directory is not mount point, proceed to mount it
                if (!mountFilesystem(luksConfig.volName, luksConfig.mountPath,
                                     defaultDirectoryPath)) {
                    json_object_put(jsonConfig);
                    return 1;
                }
                log("Encrypted vault is mounted.", LOG_INFO);
            } else {
                 log("Encrypted vault is already mounted.", LOG_INFO);
              }
         } else {
               // Mount path does not exist, create filesystem and then mount
               if (!createFilesystem(luksConfig.volName)) {
                   log("Error creating filesystem", LOG_ERR);
                   json_object_put(jsonConfig);
                   return 1;
               }
               if (!mountFilesystem(luksConfig.volName, luksConfig.mountPath,
                                    defaultDirectoryPath)) {
                   json_object_put(jsonConfig);
                   return 1;
               }
               log("Encrypted vault is mounted.", LOG_INFO);
           }
    } else {
        // The vault file does not exist, create it
        // Create the necessary directories if they don't exist
        log("The vault image file does not exist, creating one", LOG_INFO);
        if (!createVaultFile(modifiedVaultFile.c_str(),
                             luksConfig.vaultSize)) {
            log("Error creating LUKS vault image file", LOG_ERR);
            json_object_put(jsonConfig);
            return 1;
        }

        // Set up LUKS encryption
        if (!setupLUKSEncryption(modifiedVaultFile.c_str(),
                                 passphrase.c_str())) {
            log("Error setting up LUKS encryption", LOG_ERR);
            json_object_put(jsonConfig);
            return 1;
        }

        // Open LUKS Volume
        if (!openLUKSVolume(modifiedVaultFile.c_str(), luksConfig.volName,
                            passphrase.c_str())) {
            log("Error opening LUKS volume", LOG_ERR);
            json_object_put(jsonConfig);
            return 1;
        }

        // Create filesystem
        if (!createFilesystem(luksConfig.volName)) {
            log("Error creating filesystem", LOG_ERR);
            json_object_put(jsonConfig);
            return 1;
        }

        // Mount filesystem
        if (!mountFilesystem(luksConfig.volName, luksConfig.mountPath,
                             defaultDirectoryPath)) {
            json_object_put(jsonConfig);
            return 1;
        }
        log("Encrypted vault is set up and mounted.", LOG_INFO);
    }

    // Clean up JSON object
    json_object_put(jsonConfig);

    return 0;
}
