//
// Copyright (c) 2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//

package debug

import (
	"testing"
)

func TestActivate(t *testing.T) {
	isEnabled = false
	Activate()
	if !isEnabled {
		t.Error("Activate should set isEnabled to true")
	}
	isEnabled = false
}

func TestPrintWhenDisabled(t *testing.T) {
	isEnabled = false
	// Should not panic
	Print("test message")
}

func TestPrintWhenEnabled(t *testing.T) {
	isEnabled = true
	// Should not panic
	Print("test message")
	isEnabled = false
}

func TestPrintfWhenDisabled(t *testing.T) {
	isEnabled = false
	Printf("test %s", "message")
}

func TestPrintfWhenEnabled(t *testing.T) {
	isEnabled = true
	Printf("test %s", "message")
	isEnabled = false
}

func TestGetFileAndLine(t *testing.T) {
	result := getFileAndLine()
	if result == "" {
		t.Error("getFileAndLine returned empty")
	}
	if result == "???:0" {
		t.Error("getFileAndLine could not get caller")
	}
}
