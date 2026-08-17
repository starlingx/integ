//
// Copyright (c) 2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//

package deviceplugin

import (
	"context"
	pluginapi "k8s.io/kubelet/pkg/apis/deviceplugin/v1beta1"
	cdispec "tags.cncf.io/container-device-interface/specs-go"
	"testing"
)

func TestNewDeviceTree(t *testing.T) {
	tree := NewDeviceTree()
	if tree == nil {
		t.Fatal("NewDeviceTree returned nil")
	}
	if len(tree) != 0 {
		t.Errorf("new tree len = %d, want 0", len(tree))
	}
}

func TestAddDevice(t *testing.T) {
	tree := NewDeviceTree()
	info := DeviceInfo{state: pluginapi.Healthy}
	tree.AddDevice("gpu", "gpu-0", info)
	if tree.DeviceTypeCount("gpu") != 1 {
		t.Errorf("count = %d, want 1",
			tree.DeviceTypeCount("gpu"))
	}
}

func TestAddDeviceMultipleTypes(t *testing.T) {
	tree := NewDeviceTree()
	info := DeviceInfo{state: pluginapi.Healthy}
	tree.AddDevice("gpu", "gpu-0", info)
	tree.AddDevice("gpu", "gpu-1", info)
	tree.AddDevice("fpga", "fpga-0", info)
	if tree.DeviceTypeCount("gpu") != 2 {
		t.Errorf("gpu count = %d, want 2",
			tree.DeviceTypeCount("gpu"))
	}
	if tree.DeviceTypeCount("fpga") != 1 {
		t.Errorf("fpga count = %d, want 1",
			tree.DeviceTypeCount("fpga"))
	}
}

func TestDeviceTypeCountMissing(t *testing.T) {
	tree := NewDeviceTree()
	if tree.DeviceTypeCount("missing") != 0 {
		t.Error("missing type should return 0")
	}
}

func TestNewDeviceInfoWithTopologyHints(t *testing.T) {
	nodes := []pluginapi.DeviceSpec{{
		HostPath:      "/dev/cpu/0/cpuid",
		ContainerPath: "/dev/cpu/0/cpuid",
		Permissions:   "r",
	}}
	topo := &pluginapi.TopologyInfo{
		Nodes: []*pluginapi.NUMANode{{ID: 0}},
	}
	info := NewDeviceInfoWithTopologyHints(
		pluginapi.Healthy,
		nodes, nil, nil, nil, topo, nil,
	)
	if info.state != pluginapi.Healthy {
		t.Errorf("state = %q", info.state)
	}
	if info.topology == nil {
		t.Error("topology should not be nil")
	}
}

func TestUseDefaultMethodError(t *testing.T) {
	err := &UseDefaultMethodError{}
	if err.Error() != "use default method" {
		t.Errorf("Error() = %q", err.Error())
	}
}

// --- notifier tests ---

func TestNewNotifier(t *testing.T) {
	ch := make(chan updateInfo, 1)
	n := newNotifier(ch)
	if n == nil {
		t.Fatal("newNotifier returned nil")
	}
}

func TestNotifierNotifyAdded(t *testing.T) {
	ch := make(chan updateInfo, 1)
	n := newNotifier(ch)
	tree := NewDeviceTree()
	info := DeviceInfo{state: pluginapi.Healthy}
	tree.AddDevice("gpu", "gpu-0", info)
	n.Notify(tree)
	update := <-ch
	if len(update.Added) != 1 {
		t.Errorf("Added = %d, want 1", len(update.Added))
	}
}

func TestNotifierNotifyNoChange(t *testing.T) {
	ch := make(chan updateInfo, 1)
	n := newNotifier(ch)
	tree := NewDeviceTree()
	info := DeviceInfo{state: pluginapi.Healthy}
	tree.AddDevice("gpu", "gpu-0", info)
	n.Notify(tree)
	<-ch
	// Notify again with same tree — no update
	n.Notify(tree)
	select {
	case <-ch:
		t.Error("should not send update for no change")
	default:
	}
}

func TestNotifierNotifyRemoved(t *testing.T) {
	ch := make(chan updateInfo, 1)
	n := newNotifier(ch)
	tree := NewDeviceTree()
	info := DeviceInfo{state: pluginapi.Healthy}
	tree.AddDevice("gpu", "gpu-0", info)
	n.Notify(tree)
	<-ch
	// Notify with empty tree — removal
	n.Notify(NewDeviceTree())
	update := <-ch
	if len(update.Removed) != 1 {
		t.Errorf("Removed = %d, want 1", len(update.Removed))
	}
}

// --- NewManager tests ---

func TestNewManager(t *testing.T) {
	m := NewManager("test.com", nil)
	if m == nil {
		t.Fatal("NewManager returned nil")
	}
	if m.namespace != "test.com" {
		t.Errorf("namespace = %q", m.namespace)
	}
}

// --- server tests ---

func TestNewServer(t *testing.T) {
	srv := newServer("testdev", nil, nil, nil, nil)
	if srv == nil {
		t.Fatal("newServer returned nil")
	}
}

func TestServerGetDevicePluginOptions(t *testing.T) {
	srv := &server{
		preStartContainer:      nil,
		getPreferredAllocation: nil,
	}
	opts := srv.getDevicePluginOptions()
	if opts.PreStartRequired {
		t.Error("PreStartRequired should be false")
	}
	if opts.GetPreferredAllocationAvailable {
		t.Error("GetPreferredAllocation should be false")
	}
}

func TestServerGetDevicePluginOptionsEnabled(t *testing.T) {
	srv := &server{
		preStartContainer: func(
			r *pluginapi.PreStartContainerRequest,
		) error {
			return nil
		},
		getPreferredAllocation: func(
			r *pluginapi.PreferredAllocationRequest,
		) (*pluginapi.PreferredAllocationResponse, error) {
			return nil, nil
		},
	}
	opts := srv.getDevicePluginOptions()
	if !opts.PreStartRequired {
		t.Error("PreStartRequired should be true")
	}
	if !opts.GetPreferredAllocationAvailable {
		t.Error("GetPreferredAllocation should be true")
	}
}

func TestServerGetDevicePluginOptionsGRPC(t *testing.T) {
	srv := &server{}
	opts, err := srv.GetDevicePluginOptions(
		context.Background(), &pluginapi.Empty{},
	)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if opts == nil {
		t.Fatal("opts is nil")
	}
}

func TestServerSetGetState(t *testing.T) {
	srv := &server{state: uninitialized}
	if srv.getState() != uninitialized {
		t.Error("initial state wrong")
	}
	srv.setState(serving)
	if srv.getState() != serving {
		t.Error("state should be serving")
	}
	srv.setState(terminating)
	if srv.getState() != terminating {
		t.Error("state should be terminating")
	}
}

func TestServerStopWithoutServe(t *testing.T) {
	srv := &server{}
	err := srv.Stop()
	if err == nil {
		t.Error("Stop without Serve should error")
	}
}

func TestServerAllocateDefault(t *testing.T) {
	srv := &server{
		devices: map[string]DeviceInfo{
			"cpu-0": {
				state: pluginapi.Healthy,
				nodes: []pluginapi.DeviceSpec{{
					HostPath:      "/dev/cpu/0",
					ContainerPath: "/dev/cpu/0",
					Permissions:   "r",
				}},
			},
		},
	}
	rqt := &pluginapi.AllocateRequest{
		ContainerRequests: []*pluginapi.ContainerAllocateRequest{
			{DevicesIds: []string{"cpu-0"}},
		},
	}
	resp, err := srv.Allocate(context.Background(), rqt)
	if err != nil {
		t.Fatalf("Allocate error: %v", err)
	}
	if len(resp.ContainerResponses) != 1 {
		t.Errorf("responses = %d, want 1",
			len(resp.ContainerResponses))
	}
}

func TestServerAllocateNonExistent(t *testing.T) {
	srv := &server{
		devices: map[string]DeviceInfo{},
	}
	rqt := &pluginapi.AllocateRequest{
		ContainerRequests: []*pluginapi.ContainerAllocateRequest{
			{DevicesIds: []string{"missing"}},
		},
	}
	_, err := srv.Allocate(context.Background(), rqt)
	if err == nil {
		t.Error("should error for non-existent device")
	}
}

func TestServerAllocateUnhealthy(t *testing.T) {
	srv := &server{
		devices: map[string]DeviceInfo{
			"cpu-0": {state: pluginapi.Unhealthy},
		},
	}
	rqt := &pluginapi.AllocateRequest{
		ContainerRequests: []*pluginapi.ContainerAllocateRequest{
			{DevicesIds: []string{"cpu-0"}},
		},
	}
	_, err := srv.Allocate(context.Background(), rqt)
	if err == nil {
		t.Error("should error for unhealthy device")
	}
}

func TestServerPreStartContainerNil(t *testing.T) {
	srv := &server{}
	_, err := srv.PreStartContainer(
		context.Background(),
		&pluginapi.PreStartContainerRequest{},
	)
	if err == nil {
		t.Error("should error when not implemented")
	}
}

func TestServerGetPreferredAllocationNil(t *testing.T) {
	srv := &server{}
	_, err := srv.GetPreferredAllocation(
		context.Background(),
		&pluginapi.PreferredAllocationRequest{},
	)
	if err == nil {
		t.Error("should error when not implemented")
	}
}

func TestWriteCdiSpecNil(t *testing.T) {
	names, err := writeCdiSpecToFilesystem(nil, "/tmp")
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if len(names) != 0 {
		t.Errorf("names = %d, want 0", len(names))
	}
}

func TestServerConstants(t *testing.T) {
	if CDIVersion != "0.5.0" {
		t.Errorf("CDIVersion = %q", CDIVersion)
	}
	if CDIDir != "/var/run/cdi" {
		t.Errorf("CDIDir = %q", CDIDir)
	}
}

// --- Allocate with envs, mounts, annotations ---

func TestServerAllocateWithEnvsAndMounts(t *testing.T) {
	srv := &server{
		devices: map[string]DeviceInfo{
			"dev-0": {
				state: pluginapi.Healthy,
				nodes: []pluginapi.DeviceSpec{{
					HostPath:      "/dev/x",
					ContainerPath: "/dev/x",
					Permissions:   "rw",
				}},
				mounts: []pluginapi.Mount{{
					ContainerPath: "/mnt",
					HostPath:      "/host",
					ReadOnly:      true,
				}},
				envs:        map[string]string{"KEY": "VAL"},
				annotations: map[string]string{"a": "b"},
			},
		},
	}
	rqt := &pluginapi.AllocateRequest{
		ContainerRequests: []*pluginapi.ContainerAllocateRequest{
			{DevicesIds: []string{"dev-0"}},
		},
	}
	resp, err := srv.Allocate(context.Background(), rqt)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	cr := resp.ContainerResponses[0]
	if cr.Envs["KEY"] != "VAL" {
		t.Error("missing env")
	}
	if cr.Annotations["a"] != "b" {
		t.Error("missing annotation")
	}
	if len(cr.Mounts) != 1 {
		t.Error("missing mount")
	}
	if len(cr.Devices) != 1 {
		t.Error("missing device")
	}
}

func TestServerAllocateWithCustomAllocator(t *testing.T) {
	called := false
	srv := &server{
		allocate: func(
			r *pluginapi.AllocateRequest,
		) (*pluginapi.AllocateResponse, error) {
			called = true
			return &pluginapi.AllocateResponse{}, nil
		},
		devices: map[string]DeviceInfo{},
	}
	rqt := &pluginapi.AllocateRequest{
		ContainerRequests: []*pluginapi.ContainerAllocateRequest{
			{DevicesIds: []string{}},
		},
	}
	_, err := srv.Allocate(context.Background(), rqt)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if !called {
		t.Error("custom allocator not called")
	}
}

func TestServerAllocateUseDefault(t *testing.T) {
	srv := &server{
		allocate: func(
			r *pluginapi.AllocateRequest,
		) (*pluginapi.AllocateResponse, error) {
			return nil, &UseDefaultMethodError{}
		},
		devices: map[string]DeviceInfo{
			"d0": {state: pluginapi.Healthy},
		},
	}
	rqt := &pluginapi.AllocateRequest{
		ContainerRequests: []*pluginapi.ContainerAllocateRequest{
			{DevicesIds: []string{"d0"}},
		},
	}
	resp, err := srv.Allocate(context.Background(), rqt)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if len(resp.ContainerResponses) != 1 {
		t.Error("should fall through to default")
	}
}

func TestServerAllocateWithPostAllocate(t *testing.T) {
	called := false
	srv := &server{
		postAllocate: func(
			r *pluginapi.AllocateResponse,
		) error {
			called = true
			return nil
		},
		devices: map[string]DeviceInfo{
			"d0": {state: pluginapi.Healthy},
		},
	}
	rqt := &pluginapi.AllocateRequest{
		ContainerRequests: []*pluginapi.ContainerAllocateRequest{
			{DevicesIds: []string{"d0"}},
		},
	}
	_, err := srv.Allocate(context.Background(), rqt)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if !called {
		t.Error("postAllocate not called")
	}
}

// --- PreStartContainer with callback ---

func TestServerPreStartContainerWithCallback(t *testing.T) {
	called := false
	srv := &server{
		preStartContainer: func(
			r *pluginapi.PreStartContainerRequest,
		) error {
			called = true
			return nil
		},
	}
	_, err := srv.PreStartContainer(
		context.Background(),
		&pluginapi.PreStartContainerRequest{},
	)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if !called {
		t.Error("callback not called")
	}
}

// --- GetPreferredAllocation with callback ---

func TestServerGetPreferredAllocationWithCb(t *testing.T) {
	srv := &server{
		getPreferredAllocation: func(
			r *pluginapi.PreferredAllocationRequest,
		) (*pluginapi.PreferredAllocationResponse, error) {
			return &pluginapi.PreferredAllocationResponse{}, nil
		},
	}
	resp, err := srv.GetPreferredAllocation(
		context.Background(),
		&pluginapi.PreferredAllocationRequest{},
	)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if resp == nil {
		t.Error("response is nil")
	}
}

// --- Notifier updated path ---

func TestNotifierNotifyUpdated(t *testing.T) {
	ch := make(chan updateInfo, 2)
	n := newNotifier(ch)
	tree1 := NewDeviceTree()
	info1 := DeviceInfo{state: pluginapi.Healthy}
	tree1.AddDevice("gpu", "gpu-0", info1)
	n.Notify(tree1)
	<-ch
	// Change device state
	tree2 := NewDeviceTree()
	info2 := DeviceInfo{state: pluginapi.Unhealthy}
	tree2.AddDevice("gpu", "gpu-0", info2)
	n.Notify(tree2)
	update := <-ch
	if len(update.Updated) != 1 {
		t.Errorf("Updated = %d, want 1",
			len(update.Updated))
	}
}

// --- NewDeviceInfo (calls topology, will warn) ---

func TestNewDeviceInfo(t *testing.T) {
	nodes := []pluginapi.DeviceSpec{{
		HostPath:      "/dev/null",
		ContainerPath: "/dev/null",
		Permissions:   "r",
	}}
	info := NewDeviceInfo(
		pluginapi.Healthy,
		nodes, nil, nil, nil, nil,
	)
	if info.state != pluginapi.Healthy {
		t.Errorf("state = %q", info.state)
	}
}

// --- AddDevice CDI branches ---

func TestAddDeviceCdiNilSpec(t *testing.T) {
	tree := NewDeviceTree()
	info := DeviceInfo{
		state:   pluginapi.Healthy,
		cdiSpec: nil,
	}
	tree.AddDevice("t", "d0", info)
	if tree.DeviceTypeCount("t") != 1 {
		t.Error("should add device with nil cdi")
	}
}

// --- handleUpdate with mock server ---

type mockServer struct {
	served  bool
	stopped bool
	updated bool
	devices map[string]DeviceInfo
}

func (m *mockServer) Serve(ns string) error {
	m.served = true
	return nil
}
func (m *mockServer) Stop() error {
	m.stopped = true
	return nil
}
func (m *mockServer) Update(d map[string]DeviceInfo) {
	m.updated = true
	m.devices = d
}

func TestHandleUpdateAdded(t *testing.T) {
	ms := &mockServer{}
	mgr := &Manager{
		namespace: "test.com",
		servers:   make(map[string]devicePluginServer),
		createServer: func(
			dt string,
			pa postAllocateFunc,
			ps preStartContainerFunc,
			gpa getPreferredAllocationFunc,
			a allocateFunc,
		) devicePluginServer {
			return ms
		},
	}
	added := NewDeviceTree()
	info := DeviceInfo{state: pluginapi.Healthy}
	added.AddDevice("gpu", "gpu-0", info)
	mgr.handleUpdate(updateInfo{
		Added:   added,
		Updated: NewDeviceTree(),
		Removed: NewDeviceTree(),
	})
	// Give goroutine time to call Serve
	if !ms.updated {
		t.Error("Update not called")
	}
}

func TestHandleUpdateUpdated(t *testing.T) {
	ms := &mockServer{}
	mgr := &Manager{
		namespace: "test.com",
		servers: map[string]devicePluginServer{
			"gpu": ms,
		},
	}
	updated := NewDeviceTree()
	info := DeviceInfo{state: pluginapi.Healthy}
	updated.AddDevice("gpu", "gpu-0", info)
	mgr.handleUpdate(updateInfo{
		Added:   NewDeviceTree(),
		Updated: updated,
		Removed: NewDeviceTree(),
	})
	if !ms.updated {
		t.Error("Update not called")
	}
}

func TestHandleUpdateRemoved(t *testing.T) {
	ms := &mockServer{}
	mgr := &Manager{
		namespace: "test.com",
		servers: map[string]devicePluginServer{
			"gpu": ms,
		},
	}
	removed := NewDeviceTree()
	removed.AddDevice("gpu", "gpu-0", DeviceInfo{})
	mgr.handleUpdate(updateInfo{
		Added:   NewDeviceTree(),
		Updated: NewDeviceTree(),
		Removed: removed,
	})
	if !ms.stopped {
		t.Error("Stop not called")
	}
}

// --- writeCdiSpecToFilesystem edge cases ---

func TestWriteCdiSpecWrongDeviceCount(t *testing.T) {
	spec := &cdispec.Spec{
		Kind:    "test/dev",
		Devices: []cdispec.Device{},
	}
	_, err := writeCdiSpecToFilesystem(spec, "/tmp")
	if err == nil {
		t.Error("should error with 0 devices")
	}
}
