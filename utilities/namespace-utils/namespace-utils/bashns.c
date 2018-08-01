/*
 * Copyright (c) 2015 Wind River Systems, Inc.
*
* SPDX-License-Identifier: Apache-2.0
*
 */

#define _GNU_SOURCE
#include <sched.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>

void usage(char *name)
{
     printf("usage: %s <pid>\n", name);

}

int main(int argc, char **argv) {
     if (argc < 2) {
         printf("usage: %s <pid>\n", argv[0]);
         return -1;
     }

     int pid = atoi(argv[1]);
     printf("trying to open filesystem namespace of pid %d\n", pid);

     char buf[100];
     sprintf(buf, "/proc/%d/ns/mnt", pid);

     printf("trying to open %s\n", buf);

     int fd = open(buf, O_RDWR);
     if (fd < 1) {
         perror("unable to open file");
         return -1;
     }

     printf("got fd, trying to set namespace\n");

     int rc = setns(fd, 0);
     if (rc < 0) {
         perror("unable to set namespace");
         return -1;
     }

     printf("entered namespace successfully, trying to exec bash\n");

     rc = execvp("bash", 0);
     if (rc < 0) {
         perror("unable to exec bash");
         return -1;
     }
}

