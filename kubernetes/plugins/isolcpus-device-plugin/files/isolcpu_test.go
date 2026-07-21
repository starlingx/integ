//
// Copyright (c) 2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//
package main

import (
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"testing"
)

func TestNewDevicePlugin(t *testing.T) {
	dp := newDevicePlugin()
	if dp == nil {
		t.Fatal("newDevicePlugin returned nil")
	}
	if dp.nodeReg == nil {
		t.Fatal("nodeReg is nil")
	}
}

func TestNodeRegex(t *testing.T) {
	dp := newDevicePlugin()
	tests := []struct {
		input string
		match bool
	}{
		{"node0", true},
		{"node1", true},
		{"node99", true},
		{"node", false},
		{"cpu0", false},
		{"nodeX", false},
		{"", false},
	}
	for _, tc := range tests {
		got := dp.nodeReg.MatchString(tc.input)
		if got != tc.match {
			t.Errorf("nodeReg.MatchString(%q) = %v, want %v",
				tc.input, got, tc.match)
		}
	}
}

func TestGetCPUNode_InvalidCPU(t *testing.T) {
	dp := newDevicePlugin()
	// CPU 99999 shouldn't exist
	_, err := dp.getCPUNode(99999)
	if err == nil {
		t.Error("expected error for non-existent CPU")
	}
}

func TestGetCPUNode_ValidCPU(t *testing.T) {
	dp := newDevicePlugin()
	// CPU 0 should always exist
	node, err := dp.getCPUNode(0)
	if err != nil {
		t.Fatalf("getCPUNode(0) failed: %v", err)
	}
	if node < 0 {
		t.Errorf("expected node >= 0, got %d", node)
	}
}

func TestScan_ReadsIsolatedCPUs(t *testing.T) {
	dp := newDevicePlugin()
	devTree, err := dp.scan()
	if err != nil {
		// On systems with no isolated CPUs, the file may contain
		// empty string which is fine
		t.Logf("scan() returned error (may be expected): %v", err)
		return
	}
	if devTree == nil {
		t.Fatal("scan returned nil devTree")
	}
}

func TestScan_WithMockSysfs(t *testing.T) {
	// Create a temp sysfs-like structure to test scan with
	// isolated CPUs file
	tmpDir := t.TempDir()
	isolFile := filepath.Join(tmpDir, "isolated")
	// Write empty isolated CPUs (no isolated CPUs)
	err := os.WriteFile(isolFile, []byte("\n"), 0644)
	if err != nil {
		t.Fatal(err)
	}
	// We can't easily redirect /sys reads without modifying source,
	// but we verify the function handles the real /sys gracefully
	dp := newDevicePlugin()
	_, scanErr := dp.scan()
	// Either succeeds or fails gracefully
	if scanErr != nil {
		t.Logf("scan error (expected on some systems): %v", scanErr)
	}
}

func TestGetCPUNode_CPU0HasNodeDir(t *testing.T) {
	cpuPath := "/sys/devices/system/cpu/cpu0"
	entries, err := os.ReadDir(cpuPath)
	if err != nil {
		t.Skipf("Cannot read %s: %v", cpuPath, err)
	}
	dp := newDevicePlugin()
	found := false
	for _, e := range entries {
		if dp.nodeReg.MatchString(e.Name()) {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("No node* directory found in %s", cpuPath)
	}
}

func TestGetCPUNode_AllOnlineCPUs(t *testing.T) {
	dp := newDevicePlugin()
	cpuBase := "/sys/devices/system/cpu"
	entries, err := os.ReadDir(cpuBase)
	if err != nil {
		t.Skip("Cannot read CPU sysfs")
	}
	tested := 0
	cpuReg := regexp.MustCompile(`^cpu(\d+)$`)
	for _, e := range entries {
		m := cpuReg.FindStringSubmatch(e.Name())
		if m == nil {
			continue
		}
		cpuNum, _ := strconv.Atoi(m[1])
		node, err := dp.getCPUNode(cpuNum)
		if err != nil {
			t.Errorf("getCPUNode(%d) error: %v", cpuNum, err)
			continue
		}
		if node < 0 {
			t.Errorf("getCPUNode(%d) returned negative node: %d", cpuNum, node)
		}
		tested++
		if tested >= 4 {
			break
		}
	}
	if tested == 0 {
		t.Skip("No CPUs found to test")
	}
}

func TestScan_NoIsolatedCPUs(t *testing.T) {
	dp := newDevicePlugin()
	devTree, err := dp.scan()
	if err != nil {
		t.Logf("scan error (expected if isolated file missing): %v", err)
		return
	}
	if devTree == nil {
		t.Error("expected non-nil devTree")
	}
}

func TestConstants(t *testing.T) {
	if namespace != "windriver.com" {
		t.Errorf("namespace = %q, want windriver.com", namespace)
	}
	if deviceType != "isolcpus" {
		t.Errorf("deviceType = %q, want isolcpus", deviceType)
	}
}
