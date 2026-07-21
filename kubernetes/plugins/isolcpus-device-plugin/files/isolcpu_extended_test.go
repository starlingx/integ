//
// Copyright (c) 2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//

//
// Copyright (c) 2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//

package main

import (
	"os"
	"testing"
)

// TestScan_DeviceTreeStructure verifies scan returns valid DeviceTree
func TestScan_DeviceTreeStructure(t *testing.T) {
	dp := newDevicePlugin()
	devTree, err := dp.scan()
	if err != nil {
		t.Skipf("scan() error (no isolated CPUs): %v", err)
	}
	if devTree == nil {
		t.Fatal("scan returned nil devTree")
	}
	count := devTree.DeviceTypeCount(deviceType)
	t.Logf("Found %d isolated CPUs of type %q", count, deviceType)
}

// TestGetCPUNode_AllCPUs tests getCPUNode for every available CPU
func TestGetCPUNode_AllCPUs(t *testing.T) {
	dp := newDevicePlugin()
	entries, err := os.ReadDir("/sys/devices/system/cpu")
	if err != nil {
		t.Skip("Cannot read CPU sysfs")
	}
	tested := 0
	for _, e := range entries {
		name := e.Name()
		if len(name) <= 3 || name[:3] != "cpu" {
			continue
		}
		numStr := name[3:]
		cpuNum := 0
		valid := true
		for _, c := range numStr {
			if c < '0' || c > '9' {
				valid = false
				break
			}
			cpuNum = cpuNum*10 + int(c-'0')
		}
		if !valid || len(numStr) == 0 {
			continue
		}
		node, err := dp.getCPUNode(cpuNum)
		if err != nil {
			t.Errorf("getCPUNode(%d) error: %v", cpuNum, err)
			continue
		}
		if node < 0 {
			t.Errorf("getCPUNode(%d) = %d, want >= 0", cpuNum, node)
		}
		tested++
	}
	if tested == 0 {
		t.Skip("No CPUs found")
	}
	t.Logf("Tested %d CPUs", tested)
}

// TestGetCPUNode_NonExistentCPU tests error when CPU doesn't exist
func TestGetCPUNode_NonExistentCPU(t *testing.T) {
	dp := newDevicePlugin()
	_, err := dp.getCPUNode(999999)
	if err == nil {
		t.Error("expected error for CPU 999999")
	}
}

// TestGetCPUNode_CPU0 verifies CPU 0 always has a NUMA node
func TestGetCPUNode_CPU0(t *testing.T) {
	dp := newDevicePlugin()
	node, err := dp.getCPUNode(0)
	if err != nil {
		t.Fatalf("getCPUNode(0) error: %v", err)
	}
	if node < 0 {
		t.Errorf("node = %d, want >= 0", node)
	}
}

// TestGetCPUNode_CPU1 verifies CPU 1 if present
func TestGetCPUNode_CPU1(t *testing.T) {
	if _, err := os.Stat("/sys/devices/system/cpu/cpu1"); os.IsNotExist(err) {
		t.Skip("CPU 1 does not exist")
	}
	dp := newDevicePlugin()
	node, err := dp.getCPUNode(1)
	if err != nil {
		t.Fatalf("getCPUNode(1) error: %v", err)
	}
	if node < 0 {
		t.Errorf("node = %d, want >= 0", node)
	}
}

// TestScan_IsolatedFileContent reads and logs the isolated CPUs file
func TestScan_IsolatedFileContent(t *testing.T) {
	dat, err := os.ReadFile("/sys/devices/system/cpu/isolated")
	if err != nil {
		t.Skipf("Cannot read isolated CPUs: %v", err)
	}
	t.Logf("Isolated CPUs: %q", string(dat))
}

// TestNewDevicePlugin_Fields verifies struct initialization
func TestNewDevicePlugin_Fields(t *testing.T) {
	dp := newDevicePlugin()
	if dp == nil {
		t.Fatal("nil")
	}
	if dp.nodeReg == nil {
		t.Fatal("nodeReg nil")
	}
}

// TestConstants_All verifies all constants
func TestConstants_All(t *testing.T) {
	tests := []struct {
		name, got, want string
	}{
		{"namespace", namespace, "windriver.com"},
		{"deviceType", deviceType, "isolcpus"},
		{"nodeRE", nodeRE, `^node[0-9]+$`},
	}
	for _, tc := range tests {
		if tc.got != tc.want {
			t.Errorf("%s = %q, want %q", tc.name, tc.got, tc.want)
		}
	}
}

// TestNodeRegex_EdgeCases tests regex matching
func TestNodeRegex_EdgeCases(t *testing.T) {
	dp := newDevicePlugin()
	cases := []struct {
		in   string
		want bool
	}{
		{"node0", true}, {"node1", true}, {"node10", true},
		{"node100", true}, {"node", false}, {"Node0", false},
		{"node0x", false}, {"xnode0", false}, {"", false},
		{"0", false}, {"node-1", false},
	}
	for _, tc := range cases {
		if got := dp.nodeReg.MatchString(tc.in); got != tc.want {
			t.Errorf("Match(%q) = %v, want %v", tc.in, got, tc.want)
		}
	}
}
