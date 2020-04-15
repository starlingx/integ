// Copyright 2017 Intel Corporation. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

//
//  Copyright (c) 2019 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//

package main

import (
	"isolcpu_plugin/intel/intel-device-plugins-for-kubernetes/pkg/debug"
	dpapi "isolcpu_plugin/intel/intel-device-plugins-for-kubernetes/pkg/deviceplugin"
	pluginapi "isolcpu_plugin/kubernetes/pkg/kubelet/apis/deviceplugin/v1beta1"
	"isolcpu_plugin/kubernetes/pkg/kubelet/cm/cpuset"
	"github.com/pkg/errors"
        "io/ioutil"
	"strconv"
	"strings"
        "time"
        "flag"
        "fmt"
        "path"
	"regexp"
)

const (
	namespace  = "windriver.com"
	deviceType = "isolcpus"
	nodeRE	= `^node[0-9]+$`
)

type devicePlugin struct {
	nodeReg     *regexp.Regexp
}

func newDevicePlugin() *devicePlugin {
	return &devicePlugin{
		nodeReg: regexp.MustCompile(nodeRE),
	}
}

func (dp *devicePlugin) Scan(notifier dpapi.Notifier) error {
	for {
		devTree, err := dp.scan()
		if err != nil {
			return err
		}

		notifier.Notify(devTree)

		// This is only a precaution, we don't live-offline CPUs.
		time.Sleep(300 * time.Second)
	}
}

// GetCPUNode returns the NUMA node of a CPU.
func (dp *devicePlugin) getCPUNode(cpu int) (int, error) {
	cpustr := strconv.Itoa(cpu)
	cpuPath := "/sys/devices/system/cpu/cpu" + cpustr
	files, err := ioutil.ReadDir(cpuPath)
	if err != nil {
		return -1, errors.Wrap(err, "Can't read sysfs CPU subdir")
	}

	// there should be only one file of the form "node<num>"
	for _, f := range files {
		if dp.nodeReg.MatchString(f.Name()) {
			nodeStr := strings.TrimPrefix(f.Name(), "node")
			node, err := strconv.Atoi(nodeStr)
			if err != nil {
				return -1, errors.Wrap(err, "Can't convert node to int")
			}
			return node, nil
		}
	}

	return -1, errors.Wrap(err, "No node file found")
}

func (dp *devicePlugin) scan() (dpapi.DeviceTree, error) {
	dat, err := ioutil.ReadFile("/sys/devices/system/cpu/isolated")
	if err != nil {
		return nil, errors.Wrap(err, "Can't read sysfs isolcpus subdir")
	}

	// The isolated cpus string ends in a newline
	cpustring := strings.TrimSuffix(string(dat), "\n")
	cset, err := cpuset.Parse(cpustring)
	if err != nil {
		return nil, errors.Wrap(err, "Can't convert isolcpus string to cpuset")
	}
	isolcpus := cset.ToSlice()

	devTree := dpapi.NewDeviceTree()

	if len(isolcpus) > 0 {
		for _, cpu := range isolcpus {
                        cpustr := strconv.Itoa(cpu)
			numaNode, _ := dp.getCPUNode(cpu)
			devPath := path.Join("/dev/cpu", cpustr, "cpuid")
			debug.Printf("Adding %s to isolcpus", devPath)
		        var nodes []pluginapi.DeviceSpec
			nodes = append(nodes, pluginapi.DeviceSpec{
				HostPath:      devPath,
				ContainerPath: devPath,
				Permissions:   "r",
			})
		        devTree.AddDevice(deviceType, cpustr, dpapi.DeviceInfo{
			    State: pluginapi.Healthy, Nodes: nodes, NumaNode: numaNode,
		        })
                }
	}
        return devTree, nil
}

func main() {
	var debugEnabled bool
	flag.BoolVar(&debugEnabled, "debug", false, "enable debug output")
	flag.Parse()
	if debugEnabled {
		debug.Activate()
	}

	fmt.Println("isolcpus device plugin started")
	plugin := newDevicePlugin()
	manager := dpapi.NewManager(namespace, plugin)
	manager.Run()
}
