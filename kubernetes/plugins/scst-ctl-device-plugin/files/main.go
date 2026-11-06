//
// Copyright (c) 2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//

// scst-ctl-device-plugin advertises the SCST iSCSI control device to kubelet so
// that a non-privileged gateway container can be granted it. Kubernetes has no
// other way to add a character device to a pod's device cgroup.
package main

import (
	"context"
	"flag"
	"log"
	"net"
	"os"
	"path/filepath"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	pluginapi "k8s.io/kubelet/pkg/apis/deviceplugin/v1beta1"
)

var (
	resource = flag.String("resource", "starlingx.io/scst-iscsi-ctl", "extended resource name")
	devPath  = flag.String("device", "/dev/iscsi-scst-ctl", "device node to grant")
	count    = flag.Int("count", 1, "how many pods may hold the device at once")
	sockName = "scst-iscsi-ctl.sock"
)

type plugin struct {
	pluginapi.UnimplementedDevicePluginServer
	devs []*pluginapi.Device
}

func (p *plugin) GetDevicePluginOptions(context.Context, *pluginapi.Empty) (*pluginapi.DevicePluginOptions, error) {
	return &pluginapi.DevicePluginOptions{}, nil
}

// ListAndWatch reports the device healthy only while the node exists, i.e.
// while the iscsi_scst module is loaded and the scst-ctl-dev unit has created
// /dev/iscsi-scst-ctl on the host.
func (p *plugin) ListAndWatch(_ *pluginapi.Empty, s pluginapi.DevicePlugin_ListAndWatchServer) error {
	last := ""
	for {
		health := pluginapi.Unhealthy
		if _, err := os.Stat(*devPath); err == nil {
			health = pluginapi.Healthy
		}
		if health != last {
			for _, d := range p.devs {
				d.Health = health
			}
			if err := s.Send(&pluginapi.ListAndWatchResponse{Devices: p.devs}); err != nil {
				return err
			}
			log.Printf("%s is %s", *devPath, health)
			last = health
		}
		// Exit when the kubelet closes the stream (e.g. a kubelet restart),
		// otherwise this goroutine leaks - it would keep polling the device
		// and sleeping forever, since s.Send is only reached on a health
		// change. main() re-registers on restart, so a stale watcher must stop.
		select {
		case <-s.Context().Done():
			return s.Context().Err()
		case <-time.After(10 * time.Second):
		}
	}
}

func (p *plugin) Allocate(_ context.Context, req *pluginapi.AllocateRequest) (*pluginapi.AllocateResponse, error) {
	resp := &pluginapi.AllocateResponse{}
	for range req.ContainerRequests {
		resp.ContainerResponses = append(resp.ContainerResponses, &pluginapi.ContainerAllocateResponse{
			Devices: []*pluginapi.DeviceSpec{{ContainerPath: *devPath, HostPath: *devPath, Permissions: "rw"}},
		})
	}
	return resp, nil
}

func (p *plugin) GetPreferredAllocation(context.Context, *pluginapi.PreferredAllocationRequest) (*pluginapi.PreferredAllocationResponse, error) {
	return &pluginapi.PreferredAllocationResponse{}, nil
}

func (p *plugin) PreStartContainer(context.Context, *pluginapi.PreStartContainerRequest) (*pluginapi.PreStartContainerResponse, error) {
	return &pluginapi.PreStartContainerResponse{}, nil
}

func serveAndRegister(p *plugin) (*grpc.Server, error) {
	sock := filepath.Join(pluginapi.DevicePluginPath, sockName)
	_ = os.Remove(sock)
	l, err := net.Listen("unix", sock)
	if err != nil {
		return nil, err
	}
	srv := grpc.NewServer()
	pluginapi.RegisterDevicePluginServer(srv, p)
	go srv.Serve(l)

	conn, err := grpc.NewClient("unix://"+pluginapi.KubeletSocket, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		srv.Stop()
		return nil, err
	}
	defer conn.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_, err = pluginapi.NewRegistrationClient(conn).Register(ctx, &pluginapi.RegisterRequest{
		Version: pluginapi.Version, Endpoint: sockName, ResourceName: *resource,
	})
	if err != nil {
		srv.Stop()
		return nil, err
	}
	log.Printf("registered %s with kubelet (%d slots)", *resource, *count)
	return srv, nil
}

func main() {
	flag.Parse()
	p := &plugin{}
	for i := 0; i < *count; i++ {
		p.devs = append(p.devs, &pluginapi.Device{ID: filepath.Base(*devPath) + "-" + string(rune('a'+i)), Health: pluginapi.Healthy})
	}
	// Re-register whenever kubelet restarts: it recreates its socket and
	// forgets every plugin.
	for {
		srv, err := serveAndRegister(p)
		if err != nil {
			log.Printf("register: %v; retrying", err)
			time.Sleep(5 * time.Second)
			continue
		}
		st, _ := os.Stat(pluginapi.KubeletSocket)
		for {
			time.Sleep(5 * time.Second)
			now, err := os.Stat(pluginapi.KubeletSocket)
			if err != nil || !os.SameFile(st, now) {
				log.Printf("kubelet restarted; re-registering")
				break
			}
		}
		srv.Stop()
	}
}
