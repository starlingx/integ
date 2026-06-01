# Makefile for dpll-mgr (Advanced PTP Timing Synchronization Manager)
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, Intel Corporation

CC = gcc
CFLAGS = -g -O2 -Wall -Wextra -Werror -std=gnu11 -D_GNU_SOURCE
CFLAGS += -D_FORTIFY_SOURCE=3 -fstack-protector-strong -fstack-clash-protection
CFLAGS += -fPIE -fcf-protection=full
CFLAGS += -Wformat-security -Werror=format-security
CFLAGS += -DSTATIC_PARAMS_FROM_CONFIG
CFLAGS += -DENABLE_PTP_SUBSCRIPTION
CFLAGS += -UUSE_GEAR_PARK
CFLAGS += $(EXTRA_CFLAGS)
DPLL_MGR_VERSION := $(shell cat VERSION 2>/dev/null | tr -d '[:space:]')
ifeq ($(strip $(DPLL_MGR_VERSION)),)
DPLL_MGR_VERSION := unknown
endif
CFLAGS += -DDPLL_MGR_VERSION=\"$(DPLL_MGR_VERSION)\"
LDFLAGS ?= -pie -Wl,-z,relro,-z,now,-z,noexecstack -lgps -lcjson

# Directories
SRC_DIR = src
HDR_DIR = hdr
OBJ_DIR = obj
YNL_DIR = ynl

# Include paths: -I. resolves <ynl/ynl.h> and <ynl/dpll-user.h>
#                -Iinclude resolves <linux/dpll.h> (bundled UAPI header)
INCLUDES = -Iinclude -I. -I$(HDR_DIR)

# YNL (bundled kernel netlink library)
YNL_CFLAGS = -std=gnu11 -O2 -Wall -Wno-unused-parameter
YNL_SRCS = $(YNL_DIR)/ynl.c $(YNL_DIR)/dpll-user.c
YNL_OBJS = $(OBJ_DIR)/ynl.o $(OBJ_DIR)/dpll-user.o

# Application source
SOURCES = $(SRC_DIR)/apts_manager.c $(SRC_DIR)/ptp_protocol.c \
	$(SRC_DIR)/gnss_utils.c $(SRC_DIR)/dpll_utils.c \
	$(SRC_DIR)/config_parser.c $(SRC_DIR)/phc_utils.c \
	$(SRC_DIR)/dpll_phase_adjust.c $(SRC_DIR)/gearshift.c
OBJECTS = $(OBJ_DIR)/apts_manager.o $(OBJ_DIR)/ptp_protocol.o \
	$(OBJ_DIR)/gnss_utils.o $(OBJ_DIR)/dpll_utils.o \
	$(OBJ_DIR)/config_parser.o $(OBJ_DIR)/phc_utils.o \
	$(OBJ_DIR)/dpll_phase_adjust.o $(OBJ_DIR)/gearshift.o

TARGET = dpll_mgr

all: $(TARGET)

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

# Build YNL objects
$(OBJ_DIR)/ynl.o: $(YNL_DIR)/ynl.c | $(OBJ_DIR)
	$(CC) $(YNL_CFLAGS) -Iinclude -I. -c $< -o $@

$(OBJ_DIR)/dpll-user.o: $(YNL_DIR)/dpll-user.c | $(OBJ_DIR)
	$(CC) $(YNL_CFLAGS) -Iinclude -I. -c $< -o $@

# Build application objects
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# Link
$(TARGET): $(OBJECTS) $(YNL_OBJS)
	$(CC) -o $@ $(OBJECTS) $(YNL_OBJS) $(LDFLAGS)

clean:
	rm -rf $(OBJ_DIR) $(TARGET)

install: $(TARGET)
	install -D -m 755 $(TARGET) $(DESTDIR)/usr/bin/dpll-mgr

.PHONY: all clean install
