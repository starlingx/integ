/*
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Copyright (c) 2026, Intel Corporation
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived from
 *    this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */


#define _DEFAULT_SOURCE

#include "../hdr/phc_utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <ctype.h>

int phc_get_device_from_interface(const char *iface, char *device_path, size_t path_size)
{
    FILE *fp;
    char cmd[256];
    char line[256];
    int phc_num = -1;
    
    if (!iface || !device_path || path_size < 16) {
        return -1;
    }
    
    /* Validate interface name to prevent command injection */
    if (strlen(iface) > 15) {  /* IFNAMSIZ - 1 */
        return -1;
    }
    for (const char *p = iface; *p; p++) {
        if (!isalnum((unsigned char)*p) && *p != '-' && *p != '_' && *p != '.' && *p != ':') {
            return -1;
        }
    }

    /* Build ethtool command */
    snprintf(cmd, sizeof(cmd), "ethtool -T %s 2>/dev/null", iface);
    
    /* Execute command and read output */
    fp = popen(cmd, "r");
    if (!fp) {
        return -1;
    }
    
    /* Parse output to find "PTP Hardware Clock: N" */
    while (fgets(line, sizeof(line), fp) != NULL) {
        if (strstr(line, "PTP Hardware Clock:") != NULL) {
            /* Extract the clock number */
            if (sscanf(line, "%*[^:]: %d", &phc_num) == 1) {
                break;
            }
        }
    }
    
    pclose(fp);
    
    /* Check if we found a valid PHC number */
    if (phc_num < 0) {
        return -1;
    }
    
    /* Build device path */
    snprintf(device_path, path_size, "/dev/ptp%d", phc_num);
    
    return 0;
}
