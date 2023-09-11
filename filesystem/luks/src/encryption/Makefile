#
# Copyright (c) 2023 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

SHELL = /bin/bash

CFLAGS = -Wall -Wextra -g -Werror -std=c++11
LIBS = -lstdc++ -ljson-c
INCLUDES = -I.

CC=g++

SRC = PassphraseGenerator.cpp luks-fs-mgr.cpp
COMMON_OBJS = PassphraseGenerator.o
OBJS = $(SRCS:.cpp=.o)
EXECUTABLE = luks-fs-mgr

.PHONY: all clean

all: $(EXECUTABLE)

$(EXECUTABLE): $(SRC)
	$(CC) $(CFLAGS) $(INCLUDES) -o $@ $^ $(LIBS)

clean:
	rm -f $(EXECUTABLE) *.o
