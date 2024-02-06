/*
 * Copyright (c) 2023-2024 Wind River Systems, Inc.
*
* SPDX-License-Identifier: Apache-2.0
*
 */
/**
  * @file
  * StarlingX Luks FileSystem Management Service
  *
  */
#include <json-c/json.h>
#include <signal.h>
#include <sys/inotify.h>
#include <syslog.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <libdaemon/daemon.h>
#include <iostream>
#include <string>
#include <cstdlib>
#include <cstring>
#include <type_traits>
#include <atomic>
#include "PassphraseGenerator.h"
#define CONTROLLER_0 "controller-0"
#define CONTROLLER_1 "controller-1"
#define BUFFER                1024
#define MAX_BUF_SIZE          4096
#define FAIL_FILE_WRITE       (11)
#define FAIL_PID_OPEN         (9)
#define K8_PROVIDER_FILE "encryption-provider.yaml"

using namespace std;
// Global constants
const char *configFile = "/etc/luks-fs-mgr.d/luks_config.json";
const char *defaultDirectoryPath = "/var/luks/stx";
const char *defaultMountPath = "/var/luks/stx/luks_fs";
const char *createdConfigFile = "/etc/luks-fs-mgr.d/created_luks.json";
const char *luksControllerDataPath = "/var/luks/stx/luks_fs/controller/";
const char *pidFileName = "/var/run/luks-fs-mgr.pid";
atomic<bool> exitFlag(false);
// Define a struct to hold configuration variables
struct LuksConfig {
    const char *vaultFile;
    const char *vaultSize;
    const char *volName;
    const char *mountPath;
};
// Define a struct to hold configuration variables for created volume
struct CreatedLuksConfig {
    const char *vaultFile;
    const char *vaultSize;
    const char *volName;
    const char *mountPath;
    const char *passphraseType;
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
// A helper function for parsing passphraseType when ConfigType
// is CreatedLuksConfig
template <typename ConfigType>
typename enable_if<is_same<ConfigType, CreatedLuksConfig>::value, bool>::type
parsePassphraseType(ConfigType &config, json_object *passPhraseObj) {
    config.passphraseType = json_object_get_string(passPhraseObj);
    return true;
}
// A helper function for parsing passphraseType when ConfigType
// is LuksConfig
template <typename ConfigType>
typename enable_if<!is_same<ConfigType, CreatedLuksConfig>::value, bool>::type
parsePassphraseType(ConfigType &, json_object *) {
    // No-op when ConfigType is not CreatedLuksConfig
    return true;
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
template <typename ConfigType>
bool parseJSONConfig(const char *configFile, ConfigType &config,
                     json_object **jsonConfig) {
    log("Parsing " + string(configFile), LOG_INFO);
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
    json_object *passPhraseObj = json_object_object_get(volumeObj,
                                                             "PASSPHRASE_TYPE");
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
    config.vaultFile = json_object_get_string(vaultFileObj);
    config.vaultSize = json_object_get_string(vaultSizeObj);
    config.volName = json_object_get_string(volNameObj);
    config.mountPath = json_object_get_string(mountPathObj);
    parsePassphraseType(config, passPhraseObj);
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
        string mkdirCommand = "/usr/bin/mkdir -p " +
                                           string(defaultDirectoryPath);
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
            string mkdirCommand = "/usr/bin/mkdir -p " + directoryPath;
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
 * Name       : checkVaultSize
 *
 * Description: This function is responsible for checking the vaultSize
 *
 * Note:       If the size is not specified or is invalid, it sets a default
 *             size of 256 megabytes.
 *
 * ************************************************************************/
int checkVaultSize(const char *vaultSize) {
    int size = 256;
    // Convert const char* to string
    string vaultSizeStr = vaultSize;
    // Find the first non-numeric character
    size_t firstNonNumeric = vaultSizeStr.find_first_not_of("0123456789");
    if (firstNonNumeric != string::npos) {
        // Extract the numeric portion and the suffix
        string sizeStr = vaultSizeStr.substr(0, firstNonNumeric);
        string suffix = vaultSizeStr.substr(firstNonNumeric);
        // Convert the extracted string to an integer
        size = stoi(sizeStr);
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
    } else {
        log("Invalid vault file size format: No size type found."
                  " Using default size of 256MB", LOG_INFO);
    }
    return size;
}
/* ***********************************************************************
 *
 * Name       : createVaultFile
 *
 * Description: This function is responsible for creating a LUKS vault file
 *              with a specified size and a random key using the dd and
 *              cryptsetup utilities.
 *
 * ************************************************************************/
bool createVaultFile(const string &modifiedVaultFile, int vaultSize) {
    // Create the directory path if it doesn't exist
    if (!createDirectory(modifiedVaultFile.c_str())) {
        // Directory creation failed
        return false;
    }
    string command = "dd if=/dev/urandom of=" + string(modifiedVaultFile) +
                     " bs=1M count=" + to_string(vaultSize);
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
    log("Encrypting LUKS Volume", LOG_INFO);
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
    log("Unsealing LUKS Volume", LOG_INFO);
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
    log("Creating EXT4 Filesystem", LOG_INFO);
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
    log("Mounting Filesystem", LOG_INFO);
    if (!isMountPathValid(mountPath, defaultDirectoryPath)) {
        log("Mount path is not valid, using default mount path.", LOG_INFO);
        mountPath = defaultMountPath;  // Use default mount path
    }
    string mkdir_command = "/usr/bin/mkdir -p " + string(mountPath);
    int status_check = system(mkdir_command.c_str());
    // An exit status of zero indicates success, and a nonzero value
    // indicates failure.
    if (status_check != 0) {
        log("Creation of mount path directory failed with return"
                  "status: " + to_string(status_check), LOG_ERR);
        return false;
    }
    string mount_command = "/usr/bin/mount /dev/mapper/" +
                            string(volName) + " " +
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
/* ***********************************************************************
 *
 * Name       : writeJSONToFile
 *
 * Description: This function writes a provided JSON object to a specified file
 *              It handles file opening, JSON-to-string conversion,
 *              error detection, and file closure, returning true on successful
 *              write and false on failure.
 *
 * ************************************************************************/
bool writeJSONToFile(const char *filePath, json_object *jsonObj) {
    log("Creating json config file", LOG_INFO);
    FILE *file = fopen(filePath, "w");
    if (file == nullptr) {
        log("Error opening file for writing JSON.", LOG_ERR);
        return false;
    }
    // Convert JSON object to a string
    const char *jsonStr = json_object_to_json_string_ext(jsonObj,
                                        JSON_C_TO_STRING_PRETTY);
    if (jsonStr == nullptr) {
        log("Error converting JSON to string.", LOG_ERR);
        fclose(file);
        return false;
    }
    // Write the JSON string to the file
    if (fprintf(file, "%s\n", jsonStr) < 0) {
        log("Error writing JSON to file.", LOG_ERR);
        fclose(file);
        return false;
    }
    fclose(file);
    return true;
}
/* ***********************************************************************
 *
 * Name       : getPassPhraseType
 *
 * Description: This function simply returns "HWID"
 *              indicating the type of passphrase as "Hardware Identifier."
 *
 * ************************************************************************/
string getPassPhraseType() {
    return "HWID";
}
/* ***********************************************************************
 *
 * Name       : passPhraseType
 *
 * Description: This function simply returns passPhraseType
 *              indicating the type of passphrase as "Hardware Identifier."
 *
 * ************************************************************************/
PassphraseMechanism passPhraseType() {
    return HWID_Firmware;
}
/* ***********************************************************************
 *
 * Name       : unmountFilesystem
 *
 * Description: This function is responsible to umount filesystem at
 *              specified 'mountPath'.
 *
 * ************************************************************************/
bool unmountFilesystem(const char* mountPath) {
    log("Unmounting Filesystem", LOG_INFO);
    // Check if the filesystem is already unmounted
    string check_mount_command = "/usr/bin/mount | grep " + string(mountPath);
    if (system(check_mount_command.c_str()) == 0) {
        string umount_command = "/usr/bin/umount " + string(mountPath);
        if (system(umount_command.c_str()) != 0) {
            log("Error unmounting the filesystem.", LOG_ERR);
            return false;
        }
    } else {
        // The filesystem is already unmounted, no action needed
        log("Filesystem is already unmounted.", LOG_INFO);
    }
    return true;
}
/* ***********************************************************************
 *
 * Name       : increaseVaultSize
 *
 * Description: This function is resposible to increase the size of vaultfile
 *              to a given defaultSize in megabytes.
 *
 * ************************************************************************/
bool increaseVaultSize(const char* vaultFile, int defaultSize) {
    log("Increasing Vault file size", LOG_INFO);
    string increase_size_command = "/usr/bin/truncate -s " +
        to_string(defaultSize) + "M " + string(vaultFile);
    if (system(increase_size_command.c_str()) != 0) {
        log("Error increasing the size of the vault file.", LOG_ERR);
        return false;
    }
    return true;
}
/* ***********************************************************************
 *
 * Name       : resizeLUKSVolume
 *
 * Description: This function resizes a LUKS-encrypted
 *              volume specified by volName using the provided passphrase
 *
 * ************************************************************************/
bool resizeLUKSVolume(const char* volName, const char* passphrase) {
    log("Resizing LUKS Volume", LOG_INFO);
    string resize_command = "echo -n \"" + string(passphrase) +
                  "\" | /usr/sbin/cryptsetup resize " + string(volName) + " -";
    if (system(resize_command.c_str()) != 0) {
        log("Error resizing the LUKS volume.", LOG_ERR);
        return false;
    }
    return true;
}
/* ***********************************************************************
 *
 * Name       : checkFilesystem
 *
 * Description: This function performs a filesystem check using e2fsck on a
 *              specified volume (volName).
 *
 * ************************************************************************/
bool checkFilesystem(const char* volName) {
    log("Checking Filesystem for errors", LOG_INFO);
    string e2fsck_command = "/usr/sbin/e2fsck -fy /dev/mapper/" +
        string(volName);
    int status = system(e2fsck_command.c_str());
    if ((status == 0) || (status == 2048)) {
        // Command executed successfully
        return true;
    } else {
        log("Error checking the filesystem.", LOG_ERR);
        return true;
    }
}
/* ***********************************************************************
 *
 * Name       : resizeFilesystem
 *
 * Description: This function resizes the filesystem on a specified
 *              volume (volName).
 *
 * ************************************************************************/
bool resizeFilesystem(const char* volName) {
    log("Resizing Filesystem", LOG_INFO);
    string resize_fs_command = "/usr/sbin/resize2fs /dev/mapper/" +
        string(volName);
    if (system(resize_fs_command.c_str()) != 0) {
        log("Error resizing the filesystem.", LOG_ERR);
        return false;
    }
    return true;
}
/* ***********************************************************************
 *
 * Name       : remountFilesystem
 *
 * Description: This function is used to remount a previously
 *              unmounted filesystem onto a specified mountPath
 *
 * ************************************************************************/
bool remountFilesystem(const char* volName, const char* mountPath) {
    log("Re-mounting Filesystem", LOG_INFO);
    string mount_command = "/usr/bin/mount /dev/mapper/" +
        string(volName) + " " + string(mountPath);
    if (system(mount_command.c_str()) != 0) {
        log("Error mounting the filesystem back.", LOG_ERR);
        return false;
    }
    return true;
}
/* ***********************************************************************
 *
 * Name       : resizeVault
 *
 * Description: This function function orchestrates the process of resizing
 *              a LUKS-encrypted vault file and its associated filesystem.
 *              It performs a sequence of steps, including unmounting the
 *              filesystem, increasing the vault size, checking the
 *              filesystem, resizing the LUKS volume, checking the filesystem
 *              again, resizing the filesystem, and remounting the filesystem.
 *
 * ************************************************************************/
bool resizeVault(const char* vaultFile,
                 int defaultSize,
                 const char* volName,
                 const char* mountPath,
                 const char* passphrase) {
    if (unmountFilesystem(mountPath) &&
        increaseVaultSize(vaultFile, defaultSize) &&
        checkFilesystem(volName) &&
        resizeLUKSVolume(volName, passphrase) &&
        checkFilesystem(volName) &&
        resizeFilesystem(volName) &&
        remountFilesystem(volName, mountPath)) {
        log("Resize successful for LUKS volume", LOG_INFO);
        return true;
    } else {
        log("Resize failed for LUKS Volume", LOG_ERR);
        return false;
    }
}
/* ***********************************************************************
 *
 * Name       : isSymlink
 *
 * Description: This function checks if file is symlink or not.
 *
 * ************************************************************************/
bool isSymlink(const char* path) {
    struct stat buf;
    if (lstat(path, &buf) != -1) {
        return S_ISLNK(buf.st_mode);
    }
    return false;
}
/* ***********************************************************************
 *
 * Name       : execCmd
 *
 * Description: This function execute command on shell and collect output.
 *
 * ************************************************************************/
int execCmd(const string &cmd, string &result) {
    const int MAX_BUF = 256;
    char buf[MAX_BUF];
    result = "";
    int cmdStatus;
    int errorCode = 0;

    FILE *fstream = popen(cmd.c_str(), "r");
    if (!fstream) {
        log("popen error for " + cmd +  " OS err no: "
             + to_string(errno), LOG_ERR);
        return 1;
    }

    if (fstream) {
        while (!feof(fstream)) {
            if (fgets(buf, MAX_BUF, fstream) != NULL)
                  result.append(buf);
        }
        cmdStatus = pclose(fstream);
    }
    if (!result.empty())
           result = result.substr(0, result.size() - 1);

    errorCode = WEXITSTATUS(cmdStatus);

    if (WIFEXITED(cmdStatus) && errorCode == 0) {
        return 0;
    }
    return errorCode;
}
/* ***********************************************************************
 *
 * Name       : syncLuksVolume
 *
 * Description: This function checks for active controller and pushes
 *              the LUKS volume files on to standby controller's LUKS
 *              volume.
 *
 * ************************************************************************/
void syncLuksVolume() {
    string output = "";
    string hostname = "";
    string logMsg = "";
    string standbyHostname = "";
    string facterActiveCmd = "FACTERLIB=/usr/share/puppet/modules/"
                             "platform/lib/facter/ facter | egrep \"active\"";
    string facterStandAloneCmd = "FACTERLIB=/usr/share/puppet/modules/"
                          "platform/lib/facter/ facter | egrep \"standalone\"";
    int isNotStandAlone = 0, isActive = 0;
    int maxRetries = 3;
    int retryDelay = 5;
    size_t strFound = 0;
    int rc = 0;
    try {
        // Get the hostname
        rc = execCmd("/usr/bin/hostname", hostname);
        if (rc != 0) {
            logMsg = "Command failed: Unable to retrieve hostname: Error code: "
                     +to_string(rc);
            log(logMsg, LOG_ERR);
            throw std::runtime_error("Command Hostname failed.");
        }
        // Check if controller is not standalone/simplex
        rc = execCmd(facterStandAloneCmd, output);
        if (rc != 0) {
            logMsg = "Command failed: Unable to fetch FACTER standalone. "
                     " Error code: "+to_string(rc);
            log(logMsg, LOG_ERR);
            throw std::runtime_error("Command: FACTER standalone failed.");
        }
        strFound = output.find("is_standalone_controller => false");
        if (strFound != string::npos) {
            isNotStandAlone = 1;
        }
        // Check if the controller is active
        // Use the FACTER to get the active status of controller
        rc = execCmd(facterActiveCmd, output);
        if (rc != 0) {
            logMsg = "Command failed: Unable to fetch active FACTER."
                     " Error code: " + to_string(rc);
            log(logMsg, LOG_ERR);
            throw std::runtime_error("Command: FACTER active failed.");
        }
        // Check if controller is active and then
        // rsync the changes to standby controller.
        strFound = output.find("is_controller_active => true");
        if (strFound != string::npos) {
            isActive = 1;
        }
        if (isActive && isNotStandAlone) {
            logMsg = "Active controller found is " + hostname;
            log(logMsg, LOG_INFO);
            // Check the name of standby controller
            if (strcmp(CONTROLLER_0, hostname.c_str()) == 0) {
                standbyHostname = CONTROLLER_1;
            } else {
                standbyHostname = CONTROLLER_0;
            }
            // Loop to retry rsyncing
            for (int attempt = 1; attempt <= maxRetries; ++attempt) {
                string rsyncCmd = "rsync -v -acv --delete "
                       "/var/luks/stx/luks_fs/controller/ rsync://";
                rsyncCmd.append(standbyHostname);
                rsyncCmd += "/luksdata/";
                rc = execCmd(rsyncCmd, output);
                if (rc != 0) {
                    logMsg = "rysnc failed: Command execution "
                        "failed: " + rsyncCmd + " Error code:"+to_string(rc);
                    log(logMsg, LOG_ERR);
                    if (attempt < maxRetries) {
                        log("Retrying...", LOG_INFO);
                        sleep(retryDelay);  // Wait for 5 secs
                        continue;  // Retry rsync
                    } else {
                        throw runtime_error("rsync failed after "
                                            "multiple retries");
                    }
                } else {
                    logMsg = "rysnc successful: " + rsyncCmd;
                    log(logMsg, LOG_INFO);
                    break;  // Exit on rysnc success
                }
            }  // Loop ends
        }
    } catch (const exception &ex) {
        string errorStr = "rsync failed, error: " + string(ex.what());
        log(errorStr, LOG_ERR);
    }
    return;
}
/* ***********************************************************************
 *
 * Name       : syncLuksVolumeChange
 *
 * Description: This function watches LUKS volume for any changes such as
 *              create/modify/delete and accordingly generates notification
 *              event and sync the luks volume with standby controller.
 *
 * ************************************************************************/
int syncLuksVolumeChange(const char* luksPath) {
    FILE *fp;
    char notifyWaitCmd[MAX_BUF_SIZE] = {0};
    char output[BUFFER] = {0};

    (void)snprintf(notifyWaitCmd, (MAX_BUF_SIZE - 1), "timeout 5s "
                      "inotifywait -m -r -e "
                      "create,modify,delete,attrib,move --format "
                      "'%%e %%w%%f' %s 2>/dev/null", luksPath);
    fp = popen(notifyWaitCmd, "r");
    if (fp == NULL) {
        log("Error opening inotifywait pipe", LOG_ERR);
        return 1;
    }
    // Read inotifywait output
    while (fgets(output, sizeof(output), fp) != NULL) {
        // Initiate rsync on change detected
        syncLuksVolume();
        break;
    }
    pclose(fp);
    return 0;
}
/* ***********************************************************************
 *
 * Name       : daemonCreatePidfile
 *
 * Description: Creates PID file and adds the pid.
 *
 * ************************************************************************/
int daemonCreatePidfile(void) {
    FILE * pid_file_stream  = NULL;
    string errorMessage = "";
    /* Create PID file */
    pid_t mypid = getpid();

    /* Check for another instance running by trying to open in read only mode.
     * If it opens then there "may" be another process running.
     * If it opens then read the pid and see if that pID exists.
     * If it does then this is a duplicate process so exit. */
    pid_file_stream = fopen(pidFileName, "r");
    if (pid_file_stream) {
        int   rc  = 0;
        pid_t pid = 0;
        char buffer[BUFFER];
        if (fgets(buffer, BUFFER, pid_file_stream) != NULL) {
            rc = sscanf(&buffer[0], "%d",  &pid);
            if (rc == 1) {
                rc = kill(pid, 0);
                if (rc == 0) {
                    errorMessage = "Refusing to start duplicate process pid: "
                         + to_string(pid);
                    log(errorMessage, LOG_ERR);
                    fclose(pid_file_stream);
                    exit(0);
                }
            }
        }
    }
    if (pid_file_stream)
        fclose(pid_file_stream);

    /* if we got here then we are ok to run */
    pid_file_stream = fopen(pidFileName, "w");
    if (pid_file_stream == NULL) {
        syslog(LOG_ERR, "Failed to open or create %s\n", pidFileName);
        return (FAIL_PID_OPEN);
    } else if (!fprintf(pid_file_stream, "%d", mypid)) {
        syslog(LOG_ERR, "Failed to write pid file for %s\n", pidFileName);
        fclose(pid_file_stream);
        return(FAIL_FILE_WRITE);
    }
    syslog(LOG_INFO, "opened and written PID file:(pid:%d) FileName: %s\n",
        mypid, pidFileName);

    fflush(pid_file_stream);
    fclose(pid_file_stream);
    return (0);
}
/* ***********************************************************************
 *
 * Name       : luksMgrSignalHandler
 *
 * Description: Signal handler to handle termination signals
 *
 * ************************************************************************/
void luksMgrSignalHandler(int signo) {
    if (signo == SIGTERM) {
        // Cleanup tasks and exit the daemon
        log("luks daemon: Received SIGTERM. Exiting", LOG_INFO);
        exitFlag.store(true);
    }
}
/* ***********************************************************************
 *
 * Name       : getSoftwareVersion
 *
 * Description: This function gets the current software version.
 *
* ************************************************************************/
string getSoftwareVersion() {
    string swVersionCmd = "grep 'SW_VERSION' /etc/build.info | "
                          "cut -d'=' -f2 | tr -d '\"'";
    string outResult;
    int rc = execCmd(swVersionCmd, outResult);
    if (rc != 0) {
        log("Command failed: "+ swVersionCmd + " Error code: "
            +to_string(rc), LOG_ERR);
        return "";
    }
    return outResult;
}
/* ***********************************************************************
 *
 * Name       : copyKubeProviderFile
 *
 * Description: This function creates "/controller/etc/kubernetes/" directory
 *              on the LUKS volume. Then it copies encryption-provider.yaml
 *              in the directory and creates symlink for
 *              /etc/kubernetes/encryption-provider.yaml file.
 *              encryption-provider.yaml is generated during bootstrap and
 *              copied to LUKS volume.
 *              This function is written specifically for the patch-back 
 *              and upgrade case to move encryption-provider.yaml to LUKS
 *              volume.
 *
 * ************************************************************************/
int copyKubeProviderFile(bool isController) {
    int rc = 0;
    // If not a controller node then return.
    if (isController == false) {
        return 0;
    }

    string luksKubernetesDirPath = string(luksControllerDataPath)
                                   + "etc/kubernetes/";
    string sourceFilePath = luksKubernetesDirPath + K8_PROVIDER_FILE;
    // Check if the encryption-provider.yaml file already exists on LUKS
    if (access(sourceFilePath.c_str(), F_OK) == 0) {
        log("encryption-provider.yaml file is already present on "
            "LUKS filesystem.", LOG_INFO);
        return 0;
    }

    // Create controller directory on luks volume if doesnt exist.
    // This directory is needed for syncing files between active-standby
    // controllers.
    // Note: Do not delete this directory in failure path of this function.
    // This is to avoid rsync failure in standby controller.
    string kubernetesDirCmd = "/usr/bin/mkdir -p " + luksKubernetesDirPath;
    string outResult;
    log("Creating dir:  "+kubernetesDirCmd, LOG_INFO);
    rc = execCmd(kubernetesDirCmd, outResult);
    if (rc != 0) {
        log("Command failed:  " + kubernetesDirCmd+" Error code: "
             +to_string(rc), LOG_ERR);
        return rc;
    }

    // Get the SW_Version from build.info
    string softwareVersion = getSoftwareVersion();
    if (softwareVersion.empty()) {
        log("Could not get software version from /etc/build.info", LOG_ERR);
        return 1;
    }
    // Verify if encryption-provider.yaml file exists.
    // If exists, then move to luks volume.
    string platformConfigPath = "/opt/platform/config/" +softwareVersion+
                                "/kubernetes/encryption-provider.yaml";
    if (access(platformConfigPath.c_str(), F_OK) == 0) {
        log("File: "+platformConfigPath+" exists.", LOG_INFO);

        // Copy the encryption-provider.yaml file to kubernetesFilePath
        string moveEncryptionFileCmd = "/usr/bin/mv " +
                           platformConfigPath + " " + luksKubernetesDirPath;
        log("Move File:  "+moveEncryptionFileCmd, LOG_INFO);
        rc = execCmd(moveEncryptionFileCmd, outResult);
        if (rc != 0) {
            log("Command failed:  " + moveEncryptionFileCmd +
                " Error code: " + to_string(rc), LOG_ERR);
            return rc;
        }
    }

    // Verify if /etc/kubernetes/encryption-provider.yaml file exists.
    // Note: access() does not detect symlink file.
    string encryptionFilePath = "/etc/kubernetes/encryption-provider.yaml";
    if (access(encryptionFilePath.c_str(), F_OK) == 0) {
        // If encrption-provider.yaml exists in luks volume, then
        // its already copied to luks volume from the
        // /opt/platform/config/${sftw_ver}/kubernetes
        if (access(sourceFilePath.c_str(), F_OK) != 0) {
            string moveEncryptFileCmd = "/usr/bin/mv " +
                   encryptionFilePath + " " + luksKubernetesDirPath;
            log("Move File:  "+moveEncryptFileCmd, LOG_INFO);
            rc = execCmd(moveEncryptFileCmd, outResult);
            if (rc != 0) {
                log("Command failed: " + moveEncryptFileCmd +
                    " Error code: " + to_string(rc), LOG_ERR);
                return rc;
            }
        } else {
            string delEncryptionFileCmd = "/usr/bin/rm -f " +
                   encryptionFilePath;
            log("Remove File:  "+delEncryptionFileCmd, LOG_INFO);
            rc = execCmd(delEncryptionFileCmd, outResult);
            if (rc != 0) {
                log("Command failed: " + delEncryptionFileCmd +
                    " Error code: " + to_string(rc), LOG_ERR);
                return rc;
            }
        }
     // Check if symlink exists at /etc/kubernetes/
     } else if (isSymlink(encryptionFilePath.c_str())) {
         log(encryptionFilePath + " already exists", LOG_INFO);
         return 0;
     }

     // Create symlink for encryption-provider.yaml file
     string symLinkCmd = "/usr/bin/ln -s " + sourceFilePath + " " +
                          encryptionFilePath;
     log("Creating symlink:  "+symLinkCmd, LOG_INFO);
     rc = execCmd(symLinkCmd, outResult);
     if (rc != 0) {
         log("Command failed: " + symLinkCmd + " Error code: "
              + to_string(rc), LOG_ERR);
         return rc;
     }
     return rc;
}
/* ***********************************************************************
 *
 * Name       : handleResize
 *
 * Description: This function resizes the existing LUKS volume if there is
 *              change in volume size in the default configuration file.
 *
 * ************************************************************************/
int handleResize(string &passphrase, string &volName) {
    int rc = 0;
    int defaultsize = 0;
    int createdsize = 0;
    int status;
    string statusCommand, log_message, sizeStr;
    // create a JSON object to store the used attributes.
    json_object *jsonConfig;
    CreatedLuksConfig createdLuksConfig;
    LuksConfig luksConfig;
    json_object *usedAttributes = json_object_new_object();
    json_object *luksvolumesArray = json_object_new_array();
    json_object *attributesObj = json_object_new_object();
    // Parse default configuration and extract volume attributes
    if (!parseJSONConfig(configFile, luksConfig, &jsonConfig)) {
        rc = 1;
        goto cleanup;
    }
    // Parse the createdConfigfile and extract volume attributes
    if (!parseJSONConfig(createdConfigFile, createdLuksConfig,
                                              &jsonConfig)) {
        rc = 1;
        goto cleanup;
    } else {
        log("created_luks.json exists", LOG_INFO);
    }
    // Logging the successfully parsed attributes of created_luks.json
    log_message = "Vault File: " +
                                       string(createdLuksConfig.vaultFile) +
                         ", Vault Size: " +
                                       string(createdLuksConfig.vaultSize) +
                         ", Volume Name: " +
                                         string(createdLuksConfig.volName) +
                         ", Mount Path: " +
                                       string(createdLuksConfig.mountPath) +
                         ", Passphrase Type: " +
                                   string(createdLuksConfig.passphraseType);
    log(log_message, LOG_INFO);
    // Resizing logic begin here
    statusCommand = "cryptsetup status " +
                        string(createdLuksConfig.volName) + " 2>/dev/null";
    status = system(statusCommand.c_str());
    // Cryptsetup returns 0 on success and a non-zero value on error.
    // Return codes on failure:
    // 1 wrong parameters, 2 no permission (badpassphrase),
    // 3 out of memory, 4 wrong device specified,
    // 5 device already exists or device is busy.
    if (status == 0) {
        log("LUKS device is already open", LOG_INFO);
    } else {
        log("LUKS device is not open. Try opening", LOG_INFO);
        if (!openLUKSVolume(createdLuksConfig.vaultFile,
                            createdLuksConfig.volName,
                            passphrase.c_str())) {
            rc = 1;
            goto cleanup;
        }
        log("LUKS device is successfully opened", LOG_INFO);
    }
    defaultsize = checkVaultSize(luksConfig.vaultSize);
    createdsize = checkVaultSize(createdLuksConfig.vaultSize);
    volName = string(createdLuksConfig.volName);
    if (defaultsize > createdsize) {
        log("Resizing the vault file.", LOG_INFO);
        if (resizeVault(createdLuksConfig.vaultFile,
                        defaultsize,
                        createdLuksConfig.volName,
                        createdLuksConfig.mountPath,
                        passphrase.c_str())) {
            // Assigning values to attributes used to write
            // created_luks.json
            sizeStr = to_string(defaultsize);
            luksConfig.vaultSize = (sizeStr + "M").c_str();
            json_object_object_add(attributesObj, "PASSPHRASE_TYPE",
                json_object_new_string(createdLuksConfig.passphraseType));
            json_object_object_add(attributesObj, "VAULT_FILE",
                     json_object_new_string(createdLuksConfig.vaultFile));
            json_object_object_add(attributesObj, "VAULT_SIZE",
                     json_object_new_string(luksConfig.vaultSize));
            json_object_object_add(attributesObj, "VOL_NAME",
                        json_object_new_string(createdLuksConfig.volName));
            json_object_object_add(attributesObj, "MOUNT_PATH",
                      json_object_new_string(createdLuksConfig.mountPath));
            json_object_array_add(luksvolumesArray, attributesObj);
            json_object_object_add(usedAttributes, "luksvolumes",
                                                         luksvolumesArray);
            if (!writeJSONToFile(createdConfigFile, usedAttributes)) {
                log("Error writing JSON file.", LOG_ERR);
                rc = 1;
                goto cleanup;
            }
        } else {
            rc = 1;
            goto cleanup;
          }
    } else {
        log("No resizing required", LOG_INFO);
        // No Reszing to handle, start the service normally
        // Check if the mount path exists
        if (access(luksConfig.mountPath, F_OK) == 0) {
            string mount_command = "/usr/bin/mountpoint -q " +
                                 string(luksConfig.mountPath);
            int mountpoint_status = system(mount_command.c_str());
            // mountpoint has the following exit status values:
            // 0: success; the directory is a mountpoint,
            // or device is block device
            // 1: failure; incorrect invocation, permissions or system error
            // 32: failure; the directory is not a mountpoint,
            // or device is not a block device
            if (mountpoint_status != 0) {
                // Mount path directory is not mount point,
                // proceed to mount it
                if (!mountFilesystem(luksConfig.volName,
                                     luksConfig.mountPath,
                                     defaultDirectoryPath)) {
                    rc = 1;
                    goto cleanup;
                }
                log("Encrypted vault is mounted.", LOG_INFO);
            } else {
                log("Encrypted vault is already mounted.", LOG_INFO);
            }
        } else {
            statusCommand = "cryptsetup status " +
                 string(createdLuksConfig.volName) + " 2>/dev/null";
            status = system(statusCommand.c_str());
            if (status == 0) {
                log("LUKS device is already open and in use", LOG_INFO);
                if (!mountFilesystem(luksConfig.volName, luksConfig.mountPath,
                                 defaultDirectoryPath)) {
                    rc = 1;
                    goto cleanup;
                }
            } else {
                log("LUKS device is not open. Try opening", LOG_INFO);
                if (openLUKSVolume(createdLuksConfig.vaultFile,
                             createdLuksConfig.volName,
                             passphrase.c_str())) {
                    if (!mountFilesystem(luksConfig.volName,
                                 luksConfig.mountPath,
                                 defaultDirectoryPath)) {
                        rc = 1;
                        goto cleanup;
                     }
                 } else {
                     log("Unable to open LUKS device.", LOG_ERR);
                     rc = 1;
                     goto cleanup;
                 }
            }
            log("Encrypted vault is mounted.", LOG_INFO);
        }
    }
    cleanup:
        json_object_put(jsonConfig);
        json_object_put(usedAttributes);
        return (rc);
}
/* ***********************************************************************
 *
 * Name       : initialVolCreate
 *
 * Description: This function reads the default configuration file and
 *              creates the vault file, setups the LUKS encryption,
 *              unseals the LUKS volume, create file system and mount
 *              the file system.
 *              Once the LUKS voume is created, it writes the configuration
 *              in new file.
 *
 * ************************************************************************/
int initialVolCreate(string &passphrase, string &volName) {
    int rc = 0;
    int size, status;
    size_t lastSlashPos;
    string log_message, sizeStr, ppType;
    string modifiedVaultFile, mountPath, statusCommand;
    // create a JSON object to store the used attributes.
    json_object *jsonConfig;
    LuksConfig luksConfig;
    CreatedLuksConfig createdLuksConfig;
    json_object *usedAttributes = json_object_new_object();
    json_object *luksvolumesArray = json_object_new_array();
    json_object *attributesObj = json_object_new_object();
    // Parse default configuration and extract volume attributes
    if (!parseJSONConfig(configFile, luksConfig, &jsonConfig)) {
        rc = 1;
        goto cleanup;
    }
    // Execute the below code when service start during first boot
    // Create default directory for the service to create FS and mount
    if (!createDefaultDirectory(defaultDirectoryPath)) {
        rc = 1;
        goto cleanup;
    }
    log_message = "Vault File: " + string(luksConfig.vaultFile) +
                     ", Vault Size: " + string(luksConfig.vaultSize) +
                     ", Volume Name: " + string(luksConfig.volName) +
                     ", Mount Path: " + string(luksConfig.mountPath);
    log(log_message, LOG_INFO);
    // Create a new string to hold the created values
    modifiedVaultFile = luksConfig.vaultFile;
    mountPath = luksConfig.mountPath;
    volName = luksConfig.volName;
    // Check if directory path is provided in vaultFile
    lastSlashPos = modifiedVaultFile.rfind('/');
    if (lastSlashPos == string::npos) {
        // No directory path provided, use default directory
        modifiedVaultFile = "/var/luks/stx/" + modifiedVaultFile;
    }
    // Check if the vault file exists
    if ((access(luksConfig.vaultFile, F_OK) == 0) ||
           (access(modifiedVaultFile.c_str(), F_OK) == 0)) {
        // The vault file exists, proceed to unseal
        statusCommand = "cryptsetup status " +
            string(luksConfig.volName) + " 2>/dev/null";
        status = system(statusCommand.c_str());
        // Cryptsetup returns 0 on success and a non-zero value on error.
        // Return codes on failure:
        // 1 wrong parameters, 2 no permission (badpassphrase),
        // 3 out of memory, 4 wrong device specified,
        // 5 device already exists or device is busy.
        if (status == 0) {
            log("LUKS device is already open", LOG_INFO);
        } else {
            log("LUKS device is not open. Try opening", LOG_INFO);
            if (!openLUKSVolume(modifiedVaultFile.c_str(),
                                luksConfig.volName, passphrase.c_str())) {
                rc = 1;
                goto cleanup;
            }
            log("LUKS device is successfully opened", LOG_INFO);
         }
        // Check if the mount path exists
        if (access(luksConfig.mountPath, F_OK) == 0) {
            string mount_command = "/usr/bin/mountpoint -q " +
                                 string(luksConfig.mountPath);
            int mountpoint_status = system(mount_command.c_str());
            // mountpoint has the following exit status values:
            // 0: success; the directory is a mountpoint,
            // or device is block device
            // 1: failure; incorrect invocation, permissions or system error
            // 32: failure; the directory is not a mountpoint,
            // or device is not a block device on
            if (mountpoint_status != 0) {
                // Mount path directory is not mount point,
                // proceed to mount it
                if (!mountFilesystem(luksConfig.volName,
                              luksConfig.mountPath, defaultDirectoryPath)) {
                    rc = 1;
                    goto cleanup;
                }
                log("Encrypted vault is mounted.", LOG_INFO);
            } else {
                log("Encrypted vault is already mounted.", LOG_INFO);
              }
        } else {
            // Mount path does not exist, create filesystem and then mount
            if (!createFilesystem(luksConfig.volName)) {
                log("Error creating filesystem", LOG_ERR);
                rc = 1;
                goto cleanup;
            }
            if (!mountFilesystem(luksConfig.volName, luksConfig.mountPath,
                                defaultDirectoryPath)) {
                rc = 1;
                goto cleanup;
            }
            log("Encrypted vault is mounted.", LOG_INFO);
        }
    } else {
        // The vault file does not exist, create it
        // Create the necessary directories if they don't exist
        log("The vault image file does not exist, creating one", LOG_INFO);
        size = checkVaultSize(luksConfig.vaultSize);
        if (!createVaultFile(modifiedVaultFile.c_str(), size)) {
            log("Error creating LUKS vault image file", LOG_ERR);
            rc = 1;
            goto cleanup;
        }
        // Set up LUKS encryption
        if (!setupLUKSEncryption(modifiedVaultFile.c_str(),
                             passphrase.c_str())) {
            log("Error setting up LUKS encryption", LOG_ERR);
            rc = 1;
            goto cleanup;
        }
        // Open LUKS Volume
        if (!openLUKSVolume(modifiedVaultFile.c_str(), luksConfig.volName,
                        passphrase.c_str())) {
            log("Error opening LUKS volume", LOG_ERR);
            rc = 1;
            goto cleanup;
        }
        // Create filesystem
        if (!createFilesystem(luksConfig.volName)) {
            log("Error creating filesystem", LOG_ERR);
            rc = 1;
            goto cleanup;
        }
        // Mount filesystem
        if (!mountFilesystem(luksConfig.volName, luksConfig.mountPath,
                         defaultDirectoryPath)) {
            rc = 1;
            goto cleanup;
        }
        log("Encrypted vault is set up and mounted.", LOG_INFO);
    }
    if (!isMountPathValid(luksConfig.mountPath, defaultDirectoryPath)) {
        log("Mount path is not valid, using default mount path.", LOG_INFO);
        mountPath = defaultMountPath;  // Use default mount path
    }
    // Assigning values to attributes used to write created_luks.json
    size = checkVaultSize(luksConfig.vaultSize);
    sizeStr = to_string(size);
    ppType = getPassPhraseType();
    createdLuksConfig.vaultSize = (sizeStr + "M").c_str();
    createdLuksConfig.vaultFile = modifiedVaultFile.c_str();
    createdLuksConfig.volName = luksConfig.volName;
    createdLuksConfig.mountPath = mountPath.c_str();
    createdLuksConfig.passphraseType = ppType.c_str();
    json_object_object_add(attributesObj, "PASSPHRASE_TYPE",
                json_object_new_string(createdLuksConfig.passphraseType));
    json_object_object_add(attributesObj, "VAULT_FILE",
                     json_object_new_string(createdLuksConfig.vaultFile));
    json_object_object_add(attributesObj, "VAULT_SIZE",
                     json_object_new_string(createdLuksConfig.vaultSize));
    json_object_object_add(attributesObj, "VOL_NAME",
                        json_object_new_string(createdLuksConfig.volName));
    json_object_object_add(attributesObj, "MOUNT_PATH",
                      json_object_new_string(createdLuksConfig.mountPath));
    json_object_array_add(luksvolumesArray, attributesObj);
    json_object_object_add(usedAttributes, "luksvolumes", luksvolumesArray);
    if (!writeJSONToFile(createdConfigFile, usedAttributes)) {
        log("Error writing JSON file.", LOG_ERR);
        rc = 1;
        goto cleanup;
    }
    cleanup:
        json_object_put(jsonConfig);
        json_object_put(usedAttributes);
        return (rc);
}
/* ***********************************************************************
 *
 * Name       : monitorLUKSVolume
 *
 * Description: This function monitors the LUKS volume status and runs
 *              in loop until there's any issue with the LUKS volume.
 *
 * ************************************************************************/
void monitorLUKSVolume(bool isController, const string& volumeName) {
    log("Monitoring LUKS volume: " + volumeName, LOG_INFO);
    string softwareVersion = getSoftwareVersion();
    if (softwareVersion.empty()) {
        log("Could not get software version from /etc/build.info", LOG_ERR);
        return;
    }
    string platformConfigPath = "/opt/platform/config/"
                 +softwareVersion+"/kubernetes/encryption-provider.yaml";
    while (!exitFlag.load()) {
        string statusCommand = "cryptsetup status " + volumeName +
                                                           " 2>/dev/null";
        int status = system(statusCommand.c_str());
        if (status != 0) {
            string errorMessage = "LUKS volume is not in use. "
                                  "Error code: " + to_string(status);
            log(errorMessage, LOG_ERR);
            break;
        }
        if (isController == true) {
            // encyption-provider.yaml should only be present in luks volume,
            // incase if it is present in
            // /opt/platform/config/${sftw_ver}/kubernetes, then delete it
            if (access(platformConfigPath.c_str(), F_OK) == 0) {
                string outResult;
                string delEncryptionFileCmd = "/usr/bin/rm -f " +
                                      platformConfigPath;
                log("Delete File:  "+delEncryptionFileCmd, LOG_INFO);
                int rc = execCmd(delEncryptionFileCmd, outResult);
                if (rc != 0) {
                    // Continue in the error case, so that it can
                    // be tried to delete the file again.
                    log("Command failed:  " + delEncryptionFileCmd +
                        " Error code: " + to_string(rc), LOG_ERR);
                }
            }
            int rc = syncLuksVolumeChange(luksControllerDataPath);
            if (rc != 0) {
                log("Sync failed. Error code: " + to_string(rc), LOG_ERR);
                break;
            }
        }
    }
}
/* ***********************************************************************
 *
 * Name       : checkPersonality
 *
 * Description: This function checks the personality of the host
 *              where service is running and sets the output controller
 *              flag accordingly.
 *
 * ************************************************************************/
int checkPersonality(bool &isController) {
    string output = "";
    string logMsg = "";
    isController = false;
    log("Checking host personality", LOG_INFO);
    string facterPersonalityCmd = "FACTERLIB=/usr/share/puppet/modules/"
                       "platform/lib/facter/ facter | egrep \"personality\"";
    // Check if host is a controller
    int rc = execCmd(facterPersonalityCmd, output);
    if (rc != 0) {
        logMsg = "Command " + facterPersonalityCmd +
                 " failed: Unable to fetch FACTER personality. "
                 " Error code: "+to_string(rc);
        log(logMsg, LOG_ERR);
    } else {
        // Process the output
        size_t pos = output.find("controller");
        if (pos != string::npos) {
            log("Host personality is controller.", LOG_INFO);
            isController = true;
        } else {
            log("Host personality is not controller.", LOG_INFO);
        }
    }
    return rc;
}
int main() {
    int rc = 0;
    bool isController = false;
    int ret = daemon(0, 0);
    if (ret != 0) {
        string errorMessage = "Failed to run luks-fs-mgr as daemon service. "
                              "Error code: " + to_string(ret);
        log(errorMessage, LOG_ERR);
        return ret;
    }
    // Create PID file
    ret = daemonCreatePidfile();
    if (ret != 0) {
        string errorMessage = "Failed to create pid file for luks-fs-mgr. "
                              "Error code: " + to_string(ret);
        log(errorMessage, LOG_ERR);
        return ret;
    }
    // Check personality of host
    ret = checkPersonality(isController);
    if (ret != 0) {
        string errorMessage = "Failed to get the personality. "
                              "Error code: " + to_string(ret);
        log(errorMessage, LOG_ERR);
        return ret;
    }
    // Install signal handler for termination signals
    signal(SIGTERM, luksMgrSignalHandler);

    string passphrase;
    string volName;
    // Getting Passphrase from passphraseGenerator
    PassphraseMechanism selectedMechanism = passPhraseType();
    auto passphraseGenerator =
      PassphraseGeneratorFactory::createPassphraseGenerator(selectedMechanism);
    bool passStatus = passphraseGenerator->generatePassphrase(passphrase);
    // Validating if passphrase is empty
    if (passphrase.empty() || passStatus == false) {
        log("Passphrase generation failed or"
                            " returned an empty passphrase.", LOG_ERR);
        return 1;
    }
    if (access(createdConfigFile, F_OK) == 0) {
        // Volume exists, check resize required or not and handle
        rc = handleResize(passphrase, volName);
        if (rc != 0) {
            log("Volume resize failed. Error code: " + to_string(rc), LOG_ERR);
            return rc;
        }
    } else {
        rc = initialVolCreate(passphrase, volName);
        if (rc != 0) {
            log("Initial volume creation failed. Error code: " +
                 to_string(rc), LOG_ERR);
            return rc;
        }
    }
    rc = copyKubeProviderFile(isController);
    if (rc != 0) {
        log("copyKubeProviderFile() failed. Error code: "
            +to_string(rc), LOG_ERR);
        return rc;
    }
    monitorLUKSVolume(isController, volName);
    return rc;
}
