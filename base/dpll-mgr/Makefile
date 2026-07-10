# Makefile for Timing Manager Application
# SPDX-License-Identifier: BSD 3-Clause License
# Copyright (c) 2026, Intel Corporation

CC = gcc
CFLAGS = -g -O2 -Wall -Wextra -Werror -std=gnu11 -D_GNU_SOURCE -Iinclude
CFLAGS += -D_FORTIFY_SOURCE=3 -fstack-protector-strong -fstack-clash-protection
CFLAGS += -fPIE -fcf-protection=full
CFLAGS += -Wformat-security -Werror=format-security
CFLAGS += -DSTATIC_PARAMS_FROM_CONFIG
CFLAGS += -DENABLE_PTP_SUBSCRIPTION
# Use PARK as the idle gear on failover (default). To use NEUTRAL instead,
# pass EXTRA_CFLAGS=-UUSE_GEAR_PARK to make, e.g.:
#   make EXTRA_CFLAGS=-UUSE_GEAR_PARK
CFLAGS += -DUSE_GEAR_PARK
# ---------------------------------------------------------------------------
# Build mode: poll (default) or event
#   make                    -> poll-based  (periodic DPLL state polling)
#   make BUILD_MODE=event   -> event-based (DPLL netlink notifications)
# ---------------------------------------------------------------------------
BUILD_MODE ?= event
ifeq ($(BUILD_MODE),poll)
LOOP_SRC    = $(SRC_DIR)/apts_manager_poll.c
LOOP_OBJ    = $(OBJ_DIR)/apts_manager_poll.o
else ifeq ($(BUILD_MODE),event)
LOOP_SRC    = $(SRC_DIR)/apts_manager_event.c
LOOP_OBJ    = $(OBJ_DIR)/apts_manager_event.o
else
$(error Unknown BUILD_MODE '$(BUILD_MODE)'. Use 'poll' (default) or 'event')
endif
CFLAGS += $(EXTRA_CFLAGS)
APTS_VERSION := $(shell cat VERSION 2>/dev/null | tr -d '[:space:]')
ifeq ($(strip $(APTS_VERSION)),)
APTS_VERSION := unknown
endif
CFLAGS += -DAPTS_MGR_VERSION=\"$(APTS_VERSION)\"

# Kernel DPLL API compatibility probes.
# Older kernels may lack dpll_lock_status_error / dpll_feature_state.
# Probe by trying to compile a snippet that references the guard macros;
# if the probe succeeds the kernel header already defines the types.
DPLL_PROBE_FLAGS := -Iinclude -include linux/dpll.h -fsyntax-only
HAVE_DPLL_LOCK_STATUS_ERROR := $(shell echo 'int x = DPLL_A_LOCK_STATUS_ERROR;' | \
	$(CC) $(DPLL_PROBE_FLAGS) -x c - 2>/dev/null && echo 1)
HAVE_DPLL_FEATURE_STATE := $(shell echo 'int x = DPLL_A_PHASE_OFFSET_MONITOR;' | \
	$(CC) $(DPLL_PROBE_FLAGS) -x c - 2>/dev/null && echo 1)
ifeq ($(HAVE_DPLL_LOCK_STATUS_ERROR),1)
CFLAGS += -DHAVE_DPLL_LOCK_STATUS_ERROR
endif
ifeq ($(HAVE_DPLL_FEATURE_STATE),1)
CFLAGS += -DHAVE_DPLL_FEATURE_STATE
endif
#LDFLAGS = -pie -Wl,-z,relro,-z,now,-z,noexecstack -lgps -lcjson -lynl
LDFLAGS = -pie -Wl,-z,relro,-z,now,-z,noexecstack \
          -lgps -lcjson

# Bundled YNL (kernel netlink library)
YNL_DIR = ynl
YNL_CFLAGS = -std=gnu11 -O2 -Wall -Wno-unused-parameter -Wno-sign-compare
YNL_OBJS = $(OBJ_DIR)/ynl.o $(OBJ_DIR)/dpll-user.o

# Directories
SRC_DIR = src
HDR_DIR = hdr
OBJ_DIR = obj
BIN_DIR = .

# Source and object files
SOURCES = $(SRC_DIR)/apts_manager.c $(SRC_DIR)/ptp_protocol.c $(SRC_DIR)/gnss_utils.c \
	$(SRC_DIR)/dpll_utils.c $(SRC_DIR)/config_parser.c $(SRC_DIR)/phc_utils.c \
	$(SRC_DIR)/dpll_phase_adjust.c $(SRC_DIR)/gearshift.c $(SRC_DIR)/status_writer.c $(LOOP_SRC)
HEADERS = $(HDR_DIR)/apts_manager.h $(HDR_DIR)/ptp_protocol.h $(HDR_DIR)/config_parser.h \
	$(HDR_DIR)/phc_utils.h $(HDR_DIR)/dpll_phase_adjust.h $(HDR_DIR)/gearshift.h \
	$(HDR_DIR)/status_writer.h
OBJECTS = $(OBJ_DIR)/apts_manager.o $(OBJ_DIR)/ptp_protocol.o $(OBJ_DIR)/gnss_utils.o \
	$(OBJ_DIR)/dpll.o $(OBJ_DIR)/config_parser.o $(OBJ_DIR)/phc_utils.o \
	$(OBJ_DIR)/dpll_phase_adjust.o $(OBJ_DIR)/gearshift.o $(OBJ_DIR)/status_writer.o $(LOOP_OBJ)
TARGET = $(BIN_DIR)/apts_mgr # Default target
all: $(TARGET)

# Create object directory
$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

# Build timing manager
$(TARGET): $(OBJECTS) $(YNL_OBJS) | $(BIN_DIR)
	$(CC) -o $@ $(OBJECTS) $(YNL_OBJS) $(LDFLAGS)
	@echo "Built timing_manager successfully"

# Compile apts_manager
$(OBJ_DIR)/apts_manager.o: $(SRC_DIR)/apts_manager.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile ptp_protocol
$(OBJ_DIR)/ptp_protocol.o: $(SRC_DIR)/ptp_protocol.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile gnss_utils
$(OBJ_DIR)/gnss_utils.o: $(SRC_DIR)/gnss_utils.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile dpll
$(OBJ_DIR)/dpll.o: $(SRC_DIR)/dpll_utils.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile config_parser
$(OBJ_DIR)/config_parser.o: $(SRC_DIR)/config_parser.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile phc_utils
$(OBJ_DIR)/phc_utils.o: $(SRC_DIR)/phc_utils.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile dpll_phase_adjust
$(OBJ_DIR)/dpll_phase_adjust.o: $(SRC_DIR)/dpll_phase_adjust.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile gearshift
$(OBJ_DIR)/gearshift.o: $(SRC_DIR)/gearshift.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile status_writer
$(OBJ_DIR)/status_writer.o: $(SRC_DIR)/status_writer.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile poll-based loop (BUILD_MODE=poll)
$(OBJ_DIR)/apts_manager_poll.o: $(SRC_DIR)/apts_manager_poll.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Compile event-based loop (BUILD_MODE=event)
$(OBJ_DIR)/apts_manager_event.o: $(SRC_DIR)/apts_manager_event.c $(HEADERS) | $(OBJ_DIR)
	$(CC) $(CFLAGS) -I. -c $< -o $@

# Bundled YNL objects (compiled with relaxed warnings)
$(OBJ_DIR)/ynl.o: $(YNL_DIR)/ynl.c | $(OBJ_DIR)
	$(CC) $(YNL_CFLAGS) -Iinclude -I. -c $< -o $@

$(OBJ_DIR)/dpll-user.o: $(YNL_DIR)/dpll-user.c | $(OBJ_DIR)
	$(CC) $(YNL_CFLAGS) -Iinclude -I. -c $< -o $@

# Clean build artifacts
clean:
	rm -rf $(OBJ_DIR)
	rm -f $(TARGET)
	@echo "Cleaned build artifacts"

# Install target
install: $(TARGET)
	install -D -m 755 $(TARGET) /usr/local/bin/apts_mgr
	@echo "Installed timing_manager to /usr/local/bin/"

# Uninstall target
uninstall:
	rm -f /usr/local/bin/apts_mgr
	@echo "Uninstalled apts_mgr"

# Help target
help:
	@echo "Timing Manager Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all        - Build the timing_manager application (default)"
	@echo "  clean      - Remove build artifacts"
	@echo "  install    - Install timing_manager to /usr/local/bin"
	@echo "  uninstall  - Remove installed timing_manager"
	@echo "  help       - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make              # Build the application"
	@echo "  make clean        # Clean build files"
	@echo "  sudo make install # Install to system"

.PHONY: all clean install uninstall help
