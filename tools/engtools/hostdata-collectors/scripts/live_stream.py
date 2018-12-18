#!/usr/bin/python

"""
Copyright (c) 2017 Wind River Systems, Inc.

SPDX-License-Identifier: Apache-2.0
"""

import os
import sys
import time
import datetime
import psutil
import fcntl
import logging
from six.moves import configparser
import itertools
import six
from multiprocessing import Process
from multiprocessing import cpu_count
from subprocess import Popen
from subprocess import PIPE
from collections import OrderedDict
from six.moves import input


# generates the required string for the areas where fields are not static
def generateString(meas, tag_n, tag_v, field_n, field_v):
    base = "{},".format(meas)
    try:
        for i in range(len(tag_n)):
            if i == len(tag_n) - 1:
                # have space between tags and fields
                base += "'{}'='{}' ".format(tag_n[i], str(tag_v[i]))
            else:
                # separate with commas
                base += "'{}'='{}',".format(tag_n[i], str(tag_v[i]))
        for i in range(len(field_v)):
            if str(field_v[i]).replace(".", "").isdigit():
                if i == len(field_v) - 1:
                    base += "'{}'='{}'".format(field_n[i], str(field_v[i]))
                else:
                    base += "'{}'='{}',".format(field_n[i], str(field_v[i]))
        return base
    except IndexError:
        return None


# collects system memory information
def collectMemtop(influx_info, node, ci):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("memtop data starting collection with a collection interval of {}s".format(ci["memtop"]))
    measurement = "memtop"
    tags = {"node": node}
    MiB = 1024.0
    while True:
        try:
            fields = OrderedDict([("total", 0), ("used", 0), ("free", 0), ("cached", 0), ("buf", 0), ("slab", 0), ("cas", 0), ("clim", 0), ("dirty", 0), ("wback", 0), ("anon", 0), ("avail", 0)])
            with open("/proc/meminfo", "r") as f:
                hps = 0
                # for each line in /proc/meminfo, match with element in fields
                for line in f:
                    line = line.strip("\n").split()
                    if line[0].strip(":").startswith("MemTotal"):
                        # convert to from kibibytes to mibibytes
                        fields["total"] = float(line[1]) / MiB
                    elif line[0].strip(":").startswith("MemFree"):
                        fields["free"] = int(line[1]) / MiB
                    elif line[0].strip(":").startswith("MemAvailable"):
                        fields["avail"] = float(line[1]) / MiB
                    elif line[0].strip(":").startswith("Buffers"):
                        fields["buf"] = float(line[1]) / MiB
                    elif line[0].strip(":").startswith("Cached"):
                        fields["cached"] = float(line[1]) / MiB
                    elif line[0].strip(":").startswith("Slab"):
                        fields["slab"] = float(line[1]) / MiB
                    elif line[0].strip(":").startswith("CommitLimit"):
                        fields["clim"] = float(line[1]) / MiB
                    elif line[0].strip(":").startswith("Committed_AS"):
                        fields["cas"] = float(line[1]) / MiB
                    elif line[0].strip(":").startswith("Dirty"):
                        fields["dirty"] = float(line[1]) / MiB
                    elif line[0].strip(":").startswith("Writeback"):
                        fields["wback"] = float(line[1]) / MiB
                    elif line[0].strip(":").endswith("(anon)"):
                        fields["anon"] += float(line[1]) / MiB
                    elif line[0].strip(":").endswith("Hugepagesize"):
                        hps = float(line[1]) / MiB
                fields["used"] = fields["total"] - fields["avail"]
                f.close()
            # get platform specific memory info
            fields["platform_avail"] = 0
            fields["platform_hfree"] = 0
            for file in os.listdir("/sys/devices/system/node"):
                if file.startswith("node"):
                    node_num = file.replace("node", "").strip("\n")
                    avail = hfree = 0
                    with open("/sys/devices/system/node/{}/meminfo".format(file)) as f1:
                        for line in f1:
                            line = line.strip("\n").split()
                            if line[2].strip(":").startswith("MemFree") or line[2].strip(":").startswith("FilePages") or line[2].strip(":").startswith("SReclaimable"):
                                avail += float(line[3])
                            elif line[2].strip(":").startswith("HugePages_Free"):
                                hfree = float(line[3]) * hps
                        fields["{}:avail".format(node_num)] = avail / MiB
                        fields["{}:hfree".format(node_num)] = hfree
                        # get platform sum
                        fields["platform_avail"] += avail / MiB
                        fields["platform_hfree"] += hfree
                        f1.close()
            s = generateString(measurement, list(tags.keys()), list(tags.values()), list(fields.keys()), list(fields.values()))
            if s is None:
                good_string = False
            else:
                good_string = True
            if good_string:
                # send data to InfluxDB
                p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], s), shell=True)
                p.communicate()
            time.sleep(ci["memtop"])
        except KeyboardInterrupt:
            break
        except Exception:
            logging.error("memtop collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects rss and vsz information
def collectMemstats(influx_info, node, ci, services, syseng_services, openstack_services, exclude_list, skip_list, collect_all):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("memstats data starting collection with a collection interval of {}s".format(ci["memstats"]))
    measurement = "memstats"
    tags = {"node": node}
    ps_output = None
    influx_string = ""
    while True:
        try:
            fields = {}
            ps_output = Popen("exec ps -e -o rss,vsz,cmd", shell=True, stdout=PIPE)
            # create dictionary of dictionaries
            if collect_all is False:
                for svc in services:
                    fields[svc] = {"rss": 0, "vsz": 0}
                fields["static_syseng"] = {"rss": 0, "vsz": 0}
                fields["live_syseng"] = {"rss": 0, "vsz": 0}
            fields["total"] = {"rss": 0, "vsz": 0}
            ps_output.stdout.readline()
            while True:
                # for each line in ps output, get rss and vsz info
                line = ps_output.stdout.readline().strip("\n").split()
                # if at end of output, send data
                if not line:
                    break
                else:
                    rss = float(line[0])
                    vsz = float(line[1])
                    # go through all command outputs
                    for i in range(2, len(line)):
                        # remove unwanted characters and borders from cmd name. Ex: /usr/bin/example.py -> example.py
                        svc = line[i].replace("(", "").replace(")", "").strip(":").split("/")[-1].strip("\n")
                        if svc == "gunicorn":
                            gsvc = line[-1].replace("[", "").replace("]", "").strip("\n")
                            if gsvc == "public:application":
                                gsvc = "keystone-public"
                            elif gsvc == "admin:application":
                                gsvc = "keystone-admin"
                            gsvc = "gunicorn_{}".format(gsvc)
                            if gsvc not in fields:
                                fields[gsvc] = {"rss": rss, "vsz": vsz}
                            else:
                                fields[gsvc]["rss"] += rss
                                fields[gsvc]["vsz"] += vsz

                        elif svc == "postgres":
                            if (len(line) <= i+2):
                                # Command line could be "sudo su postgres", skip it
                                break

                            if line[i + 1].startswith("-") is False and line[i + 1].startswith("_") is False and line[i + 1] != "psql":
                                psvc = ""
                                if line[i + 2] in openstack_services:
                                    psvc = line[i + 2].strip("\n")
                                else:
                                    for j in range(i + 1, len(line)):
                                        psvc += "{}_".format(line[j].strip("\n"))
                                psvc = "postgres_{}".format(psvc).strip("_")
                                if psvc not in fields:
                                    fields[psvc] = {"rss": rss, "vsz": vsz}
                                else:
                                    fields[psvc]["rss"] += rss
                                    fields[psvc]["vsz"] += vsz

                        if collect_all is False:
                            if svc in services:
                                fields[svc]["rss"] += rss
                                fields[svc]["vsz"] += vsz
                                fields["total"]["rss"] += rss
                                fields["total"]["vsz"] += vsz
                                break
                            elif svc in syseng_services:
                                if svc == "live_stream.py":
                                    fields["live_syseng"]["rss"] += rss
                                    fields["live_syseng"]["vsz"] += vsz
                                else:
                                    fields["static_syseng"]["rss"] += rss
                                    fields["static_syseng"]["vsz"] += vsz
                                fields["total"]["rss"] += rss
                                fields["total"]["vsz"] += vsz
                                break
                        # Collect all services
                        else:
                            if svc in exclude_list or svc.startswith("-") or svc[0].isdigit() or svc.startswith("[") or svc.endswith("]"):
                                continue
                            elif svc in skip_list or svc.startswith("IPaddr"):
                                break
                            else:
                                if svc not in fields:
                                    fields[svc] = {"rss": rss, "vsz": vsz}
                                else:
                                    fields[svc]["rss"] += rss
                                    fields[svc]["vsz"] += vsz
                                fields["total"]["rss"] += rss
                                fields["total"]["vsz"] += vsz
                                break
            # send data to InfluxDB
            for key in fields:
                influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "service", key, "rss", fields[key]["rss"], "vsz", fields[key]["vsz"]) + "\n"
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
            p.communicate()
            influx_string = ""
            ps_output.kill()
            time.sleep(ci["memstats"])
        except KeyboardInterrupt:
            if ps_output is not None:
                ps_output.kill()
            break
        except Exception:
            logging.error("memstats collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects task cpu information
def collectSchedtop(influx_info, node, ci, services, syseng_services, openstack_services, exclude_list, skip_list, collect_all):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("schedtop data starting collection with a collection interval of {}s".format(ci["schedtop"]))
    measurement = "schedtop"
    tags = {"node": node}
    influx_string = ""
    top_output = Popen("exec top -b -c -w 512 -d{}".format(ci["schedtop"]), shell=True, stdout=PIPE)
    while True:
        try:
            fields = {}
            pro = psutil.Process(top_output.pid)
            # if process dies, restart it
            if pro.status() == "zombie":
                top_output.kill()
                top_output = Popen("exec top -b -c -w 512 -d{}".format(ci["schedtop"]), shell=True, stdout=PIPE)
            if collect_all is False:
                for svc in services:
                    fields[svc] = 0
                fields["static_syseng"] = 0
                fields["live_syseng"] = 0
            fields["total"] = 0
            # check first line
            line = top_output.stdout.readline()
            if not line:
                pass
            else:
                # skip header completely
                for _ in range(6):
                    top_output.stdout.readline()
                while True:
                    line = top_output.stdout.readline().strip("\n").split()
                    # if end of top output, leave this while loop
                    if not line:
                        break
                    else:
                        occ = float(line[8])
                        # for each command listed, check if it matches one from the list
                        for i in range(11, len(line)):
                            # remove unwanted characters and borders from cmd name. Ex: /usr/bin/example.py -> example.py
                            svc = line[i].replace("(", "").replace(")", "").strip(":").split("/")[-1]
                            if svc == "gunicorn":
                                gsvc = line[-1].replace("[", "").replace("]", "").strip("\n")
                                if gsvc == "public:application":
                                    gsvc = "keystone-public"
                                elif gsvc == "admin:application":
                                    gsvc = "keystone-admin"
                                gsvc = "gunicorn_{}".format(gsvc)
                                if gsvc not in fields:
                                    fields[gsvc] = occ
                                else:
                                    fields[gsvc] += occ

                            elif svc == "postgres":
                                if (len(line) <= i+2):
                                    # Command line could be "sudo su postgres", skip it
                                    break

                                if line[i + 1].startswith("-") is False and line[i + 1].startswith("_") is False and line[i + 1] != "psql":
                                    psvc = ""
                                    if line[i + 2] in openstack_services:
                                        psvc = line[i + 2].strip("\n")
                                    else:
                                        for j in range(i + 1, len(line)):
                                            psvc += "{}_".format(line[j].strip("\n"))
                                    psvc = "postgres_{}".format(psvc).strip("_")
                                    if psvc not in fields:
                                        fields[psvc] = occ
                                    else:
                                        fields[psvc] += occ

                            if collect_all is False:
                                if svc in services:
                                    fields[svc] += occ
                                    fields["total"] += occ
                                    break
                                elif svc in syseng_services:
                                    if svc == "live_stream.py":
                                        fields["live_syseng"] += occ
                                    else:
                                        fields["static_syseng"] += occ
                                    fields["total"] += occ
                                    break
                            # Collect all services
                            else:
                                if svc in exclude_list or svc.startswith("-") or svc[0].isdigit() or svc.startswith("[") or svc.endswith("]"):
                                    continue
                                elif svc in skip_list or svc.startswith("IPaddr"):
                                    break
                                else:
                                    if svc not in fields:
                                        fields[svc] = occ
                                    else:
                                        fields[svc] += occ
                                    fields["total"] += occ
                                    break
                for key in fields:
                    influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}'".format(measurement, "node", tags["node"], "service", key, "occ", fields[key]) + "\n"
                # send data to InfluxDB
                p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
                p.communicate()
                influx_string = ""
                time.sleep(ci["schedtop"])
        except KeyboardInterrupt:
            if top_output is not None:
                top_output.kill()
            break
        except Exception:
            logging.error("schedtop collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects disk utilization information
def collectDiskstats(influx_info, node, ci):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("diskstats data starting collection with a collection interval of {}s".format(ci["diskstats"]))
    measurement = "diskstats"
    tags = {"node": node, "file_system": None, "type": None, "mount": None}
    fields = {"size": 0, "used": 0, "avail": 0, "usage": 0}
    influx_string = ""
    while True:
        try:
            parts = psutil.disk_partitions()
            for i in parts:
                # gather all partitions
                tags["mount"] = str(i[1]).split("/")[-1]
                # if mount == '', call it root
                if tags["mount"] == "":
                    tags["mount"] = "root"
                # skip boot
                elif tags["mount"] == "boot":
                    continue
                tags["file_system"] = str(i[0]).split("/")[-1]
                tags["type"] = i[2]
                u = psutil.disk_usage(i[1])
                fields["size"] = u[0]
                fields["used"] = u[1]
                fields["avail"] = u[2]
                fields["usage"] = u[3]
                influx_string += "{},'{}'='{}','{}'='{}','{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "file_system", tags["file_system"], "type", tags["type"], "mount", tags["mount"], "size", fields["size"], "used", fields["used"], "avail", fields["avail"], "usage", fields["usage"]) + "\n"
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
            p.communicate()
            influx_string = ""
            time.sleep(ci["diskstats"])
        except KeyboardInterrupt:
            break
        except Exception:
            logging.error("diskstats collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collect device I/O information
def collectIostat(influx_info, node, ci):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("iostat data starting collection with a collection interval of {}s".format(ci["iostat"]))
    measurement = "iostat"
    tags = {"node": node}
    sector_size = 512.0
    influx_string = ""
    while True:
        try:
            fields = {}
            tmp = {}
            tmp1 = {}
            start = time.time()
            # get initial values
            for dev in os.listdir("/sys/block/"):
                if dev.startswith("sr"):
                    continue
                else:
                    fields[dev] = {"r/s": 0, "w/s": 0, "io/s": 0, "rkB/s": 0, "wkB/s": 0, "rrqms/s": 0, "wrqms/s": 0, "util": 0}
                    tmp[dev] = {"init_reads": 0, "init_reads_merged": 0, "init_read_sectors": 0, "init_read_wait": 0, "init_writes": 0, "init_writes_merged": 0, "init_write_sectors": 0, "init_write_wait": 0, "init_io_progress": 0, "init_io_time": 0, "init_wait_time": 0}
                    with open("/sys/block/{}/stat".format(dev), "r") as f:
                        # get initial readings
                        line = f.readline().strip("\n").split()
                        tmp[dev]["init_reads"] = int(line[0])
                        tmp[dev]["init_reads_merged"] = int(line[1])
                        tmp[dev]["init_read_sectors"] = int(line[2])
                        tmp[dev]["init_read_wait"] = int(line[3])
                        tmp[dev]["init_writes"] = int(line[4])
                        tmp[dev]["init_writes_merged"] = int(line[5])
                        tmp[dev]["init_write_sectors"] = int(line[6])
                        tmp[dev]["init_write_wait"] = int(line[7])
                        tmp[dev]["init_io_progress"] = int(line[8])
                        tmp[dev]["init_io_time"] = int(line[9])
                        tmp[dev]["init_wait_time"] = int(line[10])
            time.sleep(ci["iostat"])
            dt = time.time() - start
            # get values again
            for dev in os.listdir("/sys/block/"):
                if dev.startswith("sr"):
                    continue
                else:
                    # during a swact, some devices may not have been read in the initial reading. If found now, add them to dict
                    if dev not in fields:
                        fields[dev] = {"r/s": 0, "w/s": 0, "io/s": 0, "rkB/s": 0, "wkB/s": 0, "rrqms/s": 0, "wrqms/s": 0, "util": 0}
                    tmp1[dev] = {"reads": 0, "reads_merged": 0, "read_sectors": 0, "read_wait": 0, "writes": 0, "writes_merged": 0, "write_sectors": 0, "write_wait": 0, "io_progress": 0, "io_time": 0, "wait_time": 0}
                    with open("/sys/block/{}/stat".format(dev), "r") as f:
                        line = f.readline().strip("\n").split()
                        tmp1[dev]["reads"] = int(line[0])
                        tmp1[dev]["reads_merged"] = int(line[1])
                        tmp1[dev]["read_sectors"] = int(line[2])
                        tmp1[dev]["read_wait"] = int(line[3])
                        tmp1[dev]["writes"] = int(line[4])
                        tmp1[dev]["writes_merged"] = int(line[5])
                        tmp1[dev]["write_sectors"] = int(line[6])
                        tmp1[dev]["write_wait"] = int(line[7])
                        tmp1[dev]["io_progress"] = int(line[8])
                        tmp1[dev]["io_time"] = int(line[9])
                        tmp1[dev]["wait_time"] = int(line[10])
            # take difference and divide by delta t
            for key in fields:
                # if device was found in initial and second reading, do calculation
                if key in tmp and key in tmp1:
                    fields[key]["r/s"] = abs(tmp1[key]["reads"] - tmp[key]["init_reads"]) / dt
                    fields[key]["w/s"] = abs(tmp1[key]["writes"] - tmp[key]["init_writes"]) / dt
                    fields[key]["rkB/s"] = abs(tmp1[key]["read_sectors"] - tmp[key]["init_read_sectors"]) * sector_size / dt / 1000
                    fields[key]["wkB/s"] = abs(tmp1[key]["write_sectors"] - tmp[key]["init_write_sectors"]) * sector_size / dt / 1000
                    fields[key]["rrqms/s"] = abs(tmp1[key]["reads_merged"] - tmp[key]["init_reads_merged"]) / dt
                    fields[key]["wrqms/s"] = abs(tmp1[key]["writes_merged"] - tmp[key]["init_writes_merged"]) / dt
                    fields[key]["io/s"] = fields[key]["r/s"] + fields[key]["w/s"] + fields[key]["rrqms/s"] + fields[key]["wrqms/s"]
                    fields[key]["util"] = abs(tmp1[key]["io_time"] - tmp[key]["init_io_time"]) / dt / 10
                    influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "device", key, "r/s", fields[key]["r/s"], "w/s", fields[key]["w/s"], "rkB/s", fields[key]["rkB/s"], "wkB/s", fields[key]["wkB/s"], "rrqms/s", fields[key]["rrqms/s"], "wrqms/s", fields[key]["wrqms/s"], "io/s", fields[key]["io/s"], "util", fields[key]["util"]) + "\n"
            # send data to InfluxDB
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
            p.communicate()
            influx_string = ""
        except KeyboardInterrupt:
            break
        except Exception:
            logging.error("iostat collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects cpu load average information
def collectLoadavg(influx_info, node, ci):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("load_avg data starting collection with a collection interval of {}s".format(ci["load_avg"]))
    measurement = "load_avg"
    tags = {"node": node}
    fields = {"load_avg": 0}
    while True:
        try:
            fields["load_avg"] = os.getloadavg()[0]
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{},'{}'='{}' '{}'='{}''".format(influx_info[0], influx_info[1], influx_info[2], measurement, "node", tags["node"], "load_avg", fields["load_avg"]), shell=True)
            p.communicate()
            time.sleep(ci["load_avg"])
        except KeyboardInterrupt:
            break
        except Exception:
            logging.error("load_avg collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects cpu utilization information
def collectOcctop(influx_info, node, ci, pc):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("occtop data starting collection with a collection interval of {}s".format(ci["occtop"]))
    measurement = "occtop"
    tags = {"node": node}
    platform_cores = pc
    influx_string = ""
    while True:
        try:
            cpu = psutil.cpu_percent(percpu=True)
            cpu_times = psutil.cpu_times_percent(percpu=True)
            fields = {}
            # sum all cpu percents
            total = float(sum(cpu))
            sys_total = 0
            fields["platform_total"] = {"usage": 0, "system": 0}
            cores = 0
            # for each core, get values and assign a tag
            for el in cpu:
                fields["usage"] = float(el)
                fields["system"] = float(cpu_times[cores][2])
                sys_total += float(cpu_times[cores][2])
                tags["core"] = "core_{}".format(cores)
                influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "core", tags["core"], "usage", fields["usage"], "system", fields["system"]) + "\n"
                if len(platform_cores) > 0:
                    if cores in platform_cores:
                        fields["platform_total"]["usage"] += float(el)
                        fields["platform_total"]["system"] += float(cpu_times[cores][2])
                cores += 1
            # add usage and system total to influx string
            if len(platform_cores) > 0:
                influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "core", "platform_total", "usage", fields["platform_total"]["usage"], "system", fields["platform_total"]["system"]) + "\n"
            influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "core", "total", "usage", total, "system", sys_total) + "\n"
            # send data to Influx
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
            p.communicate()
            influx_string = ""
            time.sleep(ci["occtop"])
        except KeyboardInterrupt:
            break
        except Exception:
            logging.error("occtop collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects network interface information
def collectNetstats(influx_info, node, ci):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("netstats data starting collection with a collection interval of {}s".format(ci["netstats"]))
    measurement = "netstats"
    tags = {"node": node}
    fields = {}
    prev_fields = {}
    Mbps = float(1000000 / 8)
    influx_string = ""
    while True:
        try:
            net = psutil.net_io_counters(pernic=True)
            # get initial data for difference calculation
            for key in net:
                prev_fields[key] = {"tx_B": net[key][0], "rx_B": net[key][1], "tx_p": net[key][2], "rx_p": net[key][3]}
            start = time.time()
            time.sleep(ci["netstats"])
            net = psutil.net_io_counters(pernic=True)
            # get new data for difference calculation
            dt = time.time() - start
            for key in net:
                tx_B = (float(net[key][0]) - float(prev_fields[key]["tx_B"]))
                tx_Mbps = tx_B / Mbps / dt
                rx_B = (float(net[key][1]) - float(prev_fields[key]["rx_B"]))
                rx_Mbps = rx_B / Mbps / dt
                tx_pps = (float(net[key][2]) - float(prev_fields[key]["tx_p"])) / dt
                rx_pps = (float(net[key][3]) - float(prev_fields[key]["rx_p"])) / dt
                # ensure no division by zero
                if rx_B > 0 and rx_pps > 0:
                    rx_packet_size = rx_B / rx_pps
                else:
                    rx_packet_size = 0
                if tx_B > 0 and tx_pps > 0:
                    tx_packet_size = tx_B / tx_pps
                else:
                    tx_packet_size = 0
                fields[key] = {"tx_mbps": tx_Mbps, "rx_mbps": rx_Mbps, "tx_pps": tx_pps, "rx_pps": rx_pps, "tx_packet_size": tx_packet_size, "rx_packet_size": rx_packet_size}
            for key in fields:
                influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "interface", key, "rx_mbps", fields[key]["rx_mbps"], "tx_mbps", fields[key]["tx_mbps"], "rx_pps", fields[key]["rx_pps"], "tx_pps", fields[key]["tx_pps"], "rx_packet_size", fields[key]["rx_packet_size"], "tx_packet_size", fields[key]["tx_packet_size"]) + "\n"
            # send data to InfluxDB
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
            p.communicate()
            influx_string = ""
        except KeyboardInterrupt:
            break
        except Exception:
            logging.error("netstats collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects postgres db size and postgres service size information
def collectPostgres(influx_info, node, ci):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("postgres data starting collection with a collection interval of {}s".format(ci["postgres"]))
    measurement = "postgres_db_size"
    measurement1 = "postgres_svc_stats"
    tags = {"node": node, "service": None, "table_schema": 0, "table": None}
    fields = {"db_size": 0, "connections": 0}
    fields1 = {"table_size": 0, "total_size": 0, "index_size": 0, "live_tuples": 0, "dead_tuples": 0}
    postgres_output = postgres_output1 = None
    influx_string = influx_string1 = ""
    good_string = False
    dbcount = 0
    BATCH_SIZE = 10

    while True:
        try:
            # make sure this is active controller, otherwise postgres queries wont work
            if isActiveController():
                while True:
                    postgres_output = Popen("sudo -u postgres psql --pset pager=off -q -t -c'SELECT datname, pg_database_size(datname) FROM pg_database WHERE datistemplate = false;'", shell=True, stdout=PIPE)
                    db_lines = postgres_output.stdout.read().replace(" ", "").strip().split("\n")
                    if db_lines == "" or db_lines is None:
                        postgres_output.kill()
                        break
                    else:
                        # for each database from the previous output
                        for line in db_lines:
                            if not line:
                                break
                            line = line.replace(" ", "").split("|")
                            tags["service"] = line[0]
                            fields["db_size"] = line[1]
                            # send DB size to InfluxDB
                            influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}'".format(measurement, "node", tags["node"], "service", tags["service"], "db_size", fields["db_size"]) + "\n"
                            # get tables for each database
                            sql = "SELECT table_schema,table_name,pg_size_pretty(table_size) AS table_size,pg_size_pretty(indexes_size) AS indexes_size,pg_size_pretty(total_size) AS total_size,live_tuples,dead_tuples FROM (SELECT table_schema,table_name,pg_table_size(table_name) AS table_size,pg_indexes_size(table_name) AS indexes_size,pg_total_relation_size(table_name) AS total_size,pg_stat_get_live_tuples(table_name::regclass) AS live_tuples,pg_stat_get_dead_tuples(table_name::regclass) AS dead_tuples FROM (SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE') AS all_tables ORDER BY total_size DESC) AS pretty_sizes;"
                            postgres_output1 = Popen('sudo -u postgres psql --pset pager=off -q -t -d{} -c"{}"'.format(line[0], sql), shell=True, stdout=PIPE)
                            tbl_lines = postgres_output1.stdout.read().replace(" ", "").strip().split("\n")
                            for line in tbl_lines:
                                if line == "":
                                    continue
                                else:
                                    line = line.replace(" ", "").split("|")
                                    elements = list()
                                    # ensures all data is present
                                    if len(line) != 7:
                                        good_string = False
                                        break
                                    else:
                                        # do some conversions
                                        for el in line:
                                            if el.endswith("bytes"):
                                                el = int(el.replace("bytes", ""))
                                            elif el.endswith("kB"):
                                                el = el.replace("kB", "")
                                                el = int(el) * 1000
                                            elif el.endswith("MB"):
                                                el = el.replace("MB", "")
                                                el = int(el) * 1000000
                                            elif el.endswith("GB"):
                                                el = el.replace("GB", "")
                                                el = int(el) * 1000000000
                                            elements.append(el)
                                        tags["table_schema"] = elements[0]
                                        tags["table"] = elements[1]
                                        fields1["table_size"] = int(elements[2])
                                        fields1["index_size"] = int(elements[3])
                                        fields1["total_size"] = int(elements[4])
                                        fields1["live_tuples"] = int(elements[5])
                                        fields1["dead_tuples"] = int(elements[6])
                                        influx_string1 += "{},'{}'='{}','{}'='{}','{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}'".format(measurement1, "node", tags["node"], "service", tags["service"], "table_schema", tags["table_schema"], "table", tags["table"], "table_size", fields1["table_size"], "index_size", fields1["index_size"], "total_size", fields1["total_size"], "live_tuples", fields1["live_tuples"], "dead_tuples", fields1["dead_tuples"]) + "\n"
                                        good_string = True
			    dbcount += 1
			    if dbcount == BATCH_SIZE and good_string:
				# Curl will barf if the batch is too large
				p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string1), shell=True)
				p.communicate()
			       	influx_string1 = ""
				dbcount = 0
                        if good_string:
                            # send table data to InfluxDB
                            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
                            p.communicate()
                            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string1), shell=True)
                            p.communicate()
                            influx_string = influx_string1 = ""
                            dbcount = 0
                            time.sleep(ci["postgres"])
                        postgres_output1.kill()
                        postgres_output.kill()
            else:
                time.sleep(20)
        except KeyboardInterrupt:
            if postgres_output is not None:
                postgres_output.kill()
            if postgres_output1 is not None:
                postgres_output1.kill()
            break
        except Exception:
            logging.error("postgres collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collect postgres connections information
def collectPostgresConnections(influx_info, node, ci, fast):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    if fast:
        logging.info("postgres_connections data starting collection with a constant collection interval")
    else:
        logging.info("postgres_connections data starting collection with a collection interval of {}s".format(ci["postgres"]))
    measurement = "postgres_connections"
    tags = {"node": node, "service": None, "state": None}
    connections_output = None
    influx_string = ""
    while True:
        try:
            # make sure this is active controller, otherwise postgres queries wont work
            if isActiveController():
                while True:
                    fields = {}
                    # outputs a list of postgres dbs and their connections
                    connections_output = Popen("sudo -u postgres psql --pset pager=off -q -c 'SELECT datname,state,count(*) from pg_stat_activity group by datname,state;'", shell=True, stdout=PIPE)
                    line = connections_output.stdout.readline()
                    if line == "" or line is None:
                        break
                    # skip header
                    connections_output.stdout.readline()
                    while True:
                        line = connections_output.stdout.readline().strip("\n")
                        if not line:
                            break
                        else:
                            line = line.replace(" ", "").split("|")
                            if len(line) != 3:
                                continue
                            else:
                                svc = line[0]
                                connections = int(line[2])
                                tags["service"] = svc
                                if svc not in fields:
                                    fields[svc] = {"active": 0, "idle": 0, "other": 0}
                                if line[1] == "active":
                                    fields[svc]["active"] = connections
                                elif line[1] == "idle":
                                    fields[svc]["idle"] = connections
                                else:
                                    fields[svc]["other"] = connections
                                influx_string += "{},'{}'='{}','{}'='{}','{}'='{}' '{}'='{}'".format(measurement, "node", tags["node"], "service", tags["service"], "state", "active", "connections", fields[svc]["active"]) + "\n"
                                influx_string += "{},'{}'='{}','{}'='{}','{}'='{}' '{}'='{}'".format(measurement, "node", tags["node"], "service", tags["service"], "state", "idle", "connections", fields[svc]["idle"]) + "\n"
                                influx_string += "{},'{}'='{}','{}'='{}','{}'='{}' '{}'='{}'".format(measurement, "node", tags["node"], "service", tags["service"], "state", "other", "connections", fields[svc]["other"]) + "\n"

                    # send data to InfluxDB
                    p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
                    p.communicate()
                    influx_string = ""
                    connections_output.kill()
                    if fast:
                        pass
                    else:
                        time.sleep(ci["postgres"])
            else:
                time.sleep(20)
        except KeyboardInterrupt:
            if connections_output is not None:
                connections_output.kill()
            break
        except Exception:
            logging.error("postgres_connections collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects rabbitmq information
def collectRabbitMq(influx_info, node, ci):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("rabbitmq data starting collection with a collection interval of {}s".format(ci["rabbitmq"]))
    measurement = "rabbitmq"
    tags = OrderedDict([("node", node)])
    rabbitmq_output = None
    while True:
        try:
            # make sure this is active controller, otherwise rabbit queries wont work
            if isActiveController():
                while True:
                    fields = OrderedDict([])
                    rabbitmq_output = Popen("sudo rabbitmqctl -n rabbit@localhost status", shell=True, stdout=PIPE)
                    # needed data starts where output = '{memory,['
                    line = rabbitmq_output.stdout.readline()
                    # if no data is returned, exit
                    if line == "" or line is None:
                        rabbitmq_output.kill()
                        break
                    else:
                        line = rabbitmq_output.stdout.read().strip("\n").split("{memory,[")
                        if len(line) != 2:
                            rabbitmq_output.kill()
                            break
                        else:
                            # remove brackets from data
                            info = line[1].replace(" ", "").replace("{", "").replace("}", "").replace("\n", "").replace("[", "").replace("]", "").split(",")
                            for i in range(len(info) - 3):
                                if info[i].endswith("total"):
                                    info[i] = info[i].replace("total", "memory_total")
                                # some data needs string manipulation
                                if info[i].startswith("clustering") or info[i].startswith("amqp"):
                                    info[i] = "listeners_" + info[i]
                                if info[i].startswith("total_"):
                                    info[i] = "descriptors_" + info[i]
                                if info[i].startswith("limit") or info[i].startswith("used"):
                                    info[i] = "processes_" + info[i]
                                if info[i].replace("_", "").isalpha() and info[i + 1].isdigit():
                                    fields[info[i]] = info[i + 1]
                            s = generateString(measurement, list(tags.keys()), list(tags.values()), list(fields.keys()), list(fields.values()))
                            if s is None:
                                rabbitmq_output.kill()
                            else:
                                # send data to InfluxDB
                                p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], s), shell=True)
                                p.communicate()
                                time.sleep(ci["rabbitmq"])
                                rabbitmq_output.kill()
            else:
                time.sleep(20)
        except KeyboardInterrupt:
            if rabbitmq_output is not None:
                rabbitmq_output.kill()
            break
        except Exception:
            logging.error("rabbitmq collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects rabbitmq messaging information
def collectRabbitMqSvc(influx_info, node, ci, services):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("rabbitmq_svc data starting collection with a collection interval of {}s".format(ci["rabbitmq"]))
    measurement = "rabbitmq_svc"
    tags = {"node": node, "service": None}
    fields = {"messages": 0, "messages_ready": 0, "messages_unacknowledged": 0, "memory": 0, "consumers": 0}
    rabbitmq_svc_output = None
    good_string = False
    influx_string = ""
    while True:
        try:
            # make sure this is active controller, otherwise rabbit queries wont work
            if isActiveController():
                while True:
                    rabbitmq_svc_output = Popen("sudo rabbitmqctl -n rabbit@localhost list_queues name messages messages_ready messages_unacknowledged memory consumers", shell=True, stdout=PIPE)
                    # # if no data is returned, exit
                    if rabbitmq_svc_output.stdout.readline() == "" or rabbitmq_svc_output.stdout.readline() is None:
                        rabbitmq_svc_output.kill()
                        break
                    else:
                        for line in rabbitmq_svc_output.stdout:
                            line = line.split()
                            if not line:
                                break
                            else:
                                if len(line) != 6:
                                    good_string = False
                                    break
                                else:
                                    # read line and fill fields
                                    if line[0] in services:
                                        tags["service"] = line[0]
                                        fields["messages"] = line[1]
                                        fields["messages_ready"] = line[2]
                                        fields["messages_unacknowledged"] = line[3]
                                        fields["memory"] = line[4]
                                        fields["consumers"] = line[5]
                                        influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "service", tags["service"], "messages", fields["messages"], "messages_ready", fields["messages_ready"], "messages_unacknowledged", fields["messages_unacknowledged"], "memory", fields["memory"], "consumers", fields["consumers"]) + "\n"
                                        good_string = True
                        if good_string:
                            # send data to InfluxDB
                            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
                            p.communicate()
                            influx_string = ""
                            time.sleep(ci["rabbitmq"])
                        rabbitmq_svc_output.kill()
            else:
                time.sleep(20)
        except KeyboardInterrupt:
            if rabbitmq_svc_output is not None:
                rabbitmq_svc_output.kill()
            break
        except Exception:
            logging.error("rabbitmq_svc collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects open file information
def collectFilestats(influx_info, node, ci, services, syseng_services, exclude_list, skip_list, collect_all):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("filestats data starting collection with a collection interval of {}s".format(ci["filestats"]))
    measurement = "filestats"
    tags = {"node": node}
    influx_string = ""
    while True:
        try:
            fields = {}
            # fill dict with services from engtools.conf
            if collect_all is False:
                for svc in services:
                    fields[svc] = {"read/write": 0, "write": 0, "read": 0}
                fields["static_syseng"] = {"read/write": 0, "write": 0, "read": 0}
                fields["live_syseng"] = {"read/write": 0, "write": 0, "read": 0}
            fields["total"] = {"read/write": 0, "write": 0, "read": 0}
            for process in os.listdir("/proc/"):
                if process.isdigit():
                    # sometimes the process dies before reading its info
                    try:
                        svc = psutil.Process(int(process)).name()
                        svc = svc.split()[0].replace("(", "").replace(")", "").strip(":").split("/")[-1]
                    except Exception:
                        continue
                    if collect_all is False:
                        if svc in services:
                            try:
                                p = Popen("ls -l /proc/{}/fd".format(process), shell=True, stdout=PIPE)
                                p.stdout.readline()
                                while True:
                                    line = p.stdout.readline().strip("\n").split()
                                    if not line:
                                        break
                                    else:
                                        priv = line[0]
                                        if priv[1] == "r" and priv[2] == "w":
                                            fields[svc]["read/write"] += 1
                                            fields["total"]["read/write"] += 1
                                        elif priv[1] == "r" and priv[2] != "w":
                                            fields[svc]["read"] += 1
                                            fields["total"]["read"] += 1
                                        elif priv[1] != "r" and priv[2] == "w":
                                            fields[svc]["write"] += 1
                                            fields["total"]["write"] += 1
                            except Exception:
                                p.kill()
                                continue
                            p.kill()

                        elif svc in syseng_services:
                            try:
                                p = Popen("ls -l /proc/{}/fd".format(process), shell=True, stdout=PIPE)
                                p.stdout.readline()
                                while True:
                                    line = p.stdout.readline().strip("\n").split()
                                    if not line:
                                        break
                                    else:
                                        priv = line[0]
                                        if svc == "live_stream.py":
                                            if priv[1] == "r" and priv[2] == "w":
                                                fields["live_syseng"]["read/write"] += 1
                                                fields["total"]["read/write"] += 1
                                            elif priv[1] == "r" and priv[2] != "w":
                                                fields["live_syseng"]["read"] += 1
                                                fields["total"]["read"] += 1
                                            elif priv[1] != "r" and priv[2] == "w":
                                                fields["live_syseng"]["write"] += 1
                                                fields["total"]["write"] += 1
                                        else:
                                            if priv[1] == "r" and priv[2] == "w":
                                                fields["static_syseng"]["read/write"] += 1
                                                fields["total"]["read/write"] += 1
                                            elif priv[1] == "r" and priv[2] != "w":
                                                fields["static_syseng"]["read"] += 1
                                                fields["total"]["read"] += 1
                                            elif priv[1] != "r" and priv[2] == "w":
                                                fields["static_syseng"]["write"] += 1
                                                fields["total"]["write"] += 1
                            except Exception:
                                p.kill()
                                continue
                            p.kill()

                    else:
                        # remove garbage processes
                        if svc in exclude_list or svc in skip_list or svc.startswith("-") or svc.endswith("-") or svc[0].isdigit() or svc[-1].isdigit() or svc[0].isupper():
                            continue
                        elif svc not in fields:
                            fields[svc] = {"read/write": 0, "write": 0, "read": 0}
                        try:
                            p = Popen("ls -l /proc/{}/fd".format(process), shell=True, stdout=PIPE)
                            p.stdout.readline()
                            while True:
                                line = p.stdout.readline().strip("\n").split()
                                if not line:
                                    break
                                else:
                                    priv = line[0]
                                    if priv[1] == "r" and priv[2] == "w":
                                        fields[svc]["read/write"] += 1
                                        fields["total"]["read/write"] += 1
                                    elif priv[1] == "r" and priv[2] != "w":
                                        fields[svc]["read"] += 1
                                        fields["total"]["read"] += 1
                                    elif priv[1] != "r" and priv[2] == "w":
                                        fields[svc]["write"] += 1
                                        fields["total"]["write"] += 1
                            if fields[svc]["read/write"] == 0 and fields[svc]["read"] == 0 and fields[svc]["write"] == 0:
                                del fields[svc]
                        except Exception:
                            p.kill()
                            continue
                        p.kill()
            for key in fields:
                influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "service", key, "read/write", fields[key]["read/write"], "write", fields[key]["write"], "read", fields[key]["read"]) + "\n"
                # send data to InfluxDB
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
            p.communicate()
            influx_string = ""
            time.sleep(ci["filestats"])
        except KeyboardInterrupt:
            break
        except Exception:
            logging.error("filestats collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects vshell information
def collectVswitch(influx_info, node, ci):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("vswitch data starting collection with a collection interval of {}s".format(ci["vswitch"]))
    measurement = "vswitch"
    tags = OrderedDict([("node", node), ("engine", 0)])
    tags1 = OrderedDict([("node", node), ("port", 0)])
    tags2 = OrderedDict([("node", node), ("interface", 0)])
    fields = OrderedDict([("cpuid", 0), ("rx_packets", 0), ("tx_packets", 0), ("rx_discard", 0), ("tx_discard", 0), ("tx_disabled", 0), ("tx_overflow", 0), ("tx_timeout", 0), ("usage", 0)])
    fields1 = OrderedDict([("rx_packets", 0), ("tx_packets", 0), ("rx_bytes", 0), ("tx_bytes", 0), ("tx_errors", 0), ("rx_errors", 0), ("rx_nombuf", 0)])
    fields2 = OrderedDict([("rx_packets", 0), ("tx_packets", 0), ("rx_bytes", 0), ("tx_bytes", 0), ("tx_errors", 0), ("rx_errors", 0), ("tx_discards", 0), ("rx_discards", 0), ("rx_floods", 0), ("rx_no_vlan", 0)])
    vshell_engine_stats_output = vshell_port_stats_output = vshell_interface_stats_output = None
    influx_string = ""
    while True:
        try:
            vshell_engine_stats_output = Popen("vshell engine-stats-list", shell=True, stdout=PIPE)
            # skip first few lines
            vshell_engine_stats_output.stdout.readline()
            vshell_engine_stats_output.stdout.readline()
            vshell_engine_stats_output.stdout.readline()
            while True:
                line = vshell_engine_stats_output.stdout.readline().replace("|", "").split()
                if not line:
                    break
                # skip lines like +++++++++++++++++++++++++++++
                elif line[0].startswith("+"):
                    continue
                else:
                    # get info from output
                    i = 2
                    tags["engine"] = line[1]
                    for key in fields:
                        fields[key] = line[i].strip("%")
                        i += 1
                    influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}'".format(measurement, list(tags.keys())[0], list(tags.values())[0], list(tags.keys())[1], list(tags.values())[1], list(fields.keys())[0], list(fields.values())[0], list(fields.keys())[1], list(fields.values())[1], list(fields.keys())[2], list(fields.values())[2], list(fields.keys())[3], list(fields.values())[3], list(fields.keys())[4], list(fields.values())[4], list(fields.keys())[5], list(fields.values())[5], list(fields.keys())[6], list(fields.values())[6], list(fields.keys())[7], list(fields.values())[7], list(fields.keys())[8], list(fields.values())[8]) + "\n"
            vshell_engine_stats_output.kill()
            vshell_port_stats_output = Popen("vshell port-stats-list", shell=True, stdout=PIPE)
            vshell_port_stats_output.stdout.readline()
            vshell_port_stats_output.stdout.readline()
            vshell_port_stats_output.stdout.readline()
            while True:
                line = vshell_port_stats_output.stdout.readline().replace("|", "").split()
                if not line:
                    break
                elif line[0].startswith("+"):
                    continue
                else:
                    i = 3
                    tags1["port"] = line[1]
                    for key in fields1:
                        fields1[key] = line[i].strip("%")
                        i += 1
                    influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}'".format(measurement, list(tags1.keys())[0], list(tags1.values())[0], list(tags1.keys())[1], list(tags1.values())[1], list(fields1.keys())[0], list(fields1.values())[0], list(fields1.keys())[1], list(fields1.values())[1], list(fields1.keys())[2], list(fields1.values())[2], list(fields1.keys())[3], list(fields1.values())[3], list(fields1.keys())[4], list(fields1.values())[4], list(fields1.keys())[5], list(fields1.values())[5], list(fields1.keys())[6], list(fields1.values())[6]) + "\n"
            vshell_port_stats_output.kill()
            vshell_interface_stats_output = Popen("vshell interface-stats-list", shell=True, stdout=PIPE)
            vshell_interface_stats_output.stdout.readline()
            vshell_interface_stats_output.stdout.readline()
            vshell_interface_stats_output.stdout.readline()
            while True:
                line = vshell_interface_stats_output.stdout.readline().replace("|", "").split()
                if not line:
                    break
                elif line[0].startswith("+"):
                    continue
                else:
                    if line[2] == "ethernet" and line[3].startswith("eth"):
                        i = 4
                        tags2["interface"] = line[3]
                        for key in fields2:
                            fields2[key] = line[i].strip("%")
                            i += 1
                        influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}','{}'='{}'".format(measurement, list(tags2.keys())[0], list(tags2.values())[0], list(tags2.keys())[1], list(tags2.values())[1], list(fields2.keys())[0], list(fields2.values())[0], list(fields2.keys())[1], list(fields2.values())[1], list(fields2.keys())[2], list(fields2.values())[2], list(fields2.keys())[3], list(fields2.values())[3], list(fields2.keys())[4], list(fields2.values())[4], list(fields2.keys())[5], list(fields2.values())[5], list(fields2.keys())[6], list(fields2.values())[6], list(fields2.keys())[7], list(fields2.values())[7], list(fields2.keys())[8], list(fields2.values())[8], list(fields2.keys())[9], list(fields2.values())[9]) + "\n"
                    else:
                        continue
            vshell_interface_stats_output.kill()
            # send data to InfluxDB
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
            p.communicate()
            influx_string = ""
            time.sleep(ci["vswitch"])
        except KeyboardInterrupt:
            if vshell_engine_stats_output is not None:
                vshell_engine_stats_output.kill()
            if vshell_port_stats_output is not None:
                vshell_port_stats_output.kill()
            if vshell_interface_stats_output is not None:
                vshell_interface_stats_output.kill()
            break
        except Exception:
            logging.error("vswitch collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)


# collects the number of cores
def collectCpuCount(influx_info, node, ci):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("cpu_count data starting collection with a collection interval of {}s".format(ci["cpu_count"]))
    measurement = "cpu_count"
    tags = {"node": node}
    while True:
        try:
            fields = {"cpu_count": cpu_count()}
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{},'{}'='{}' '{}'='{}''".format(influx_info[0], influx_info[1], influx_info[2], measurement, "node", tags["node"], "cpu_count", fields["cpu_count"]), shell=True)
            p.communicate()
            time.sleep(ci["cpu_count"])
        except KeyboardInterrupt:
            break
        except Exception:
            logging.error("cpu_count collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))

def collectApiStats(influx_info, node, ci, services, db_port, rabbit_port):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.info("api_request data starting collection with a collection interval of {}s".format(ci["cpu_count"]))
    measurement = "api_requests"
    tags = {"node": node}
    influx_string = ""
    lsof_args = ['lsof', '-Pn', '-i', 'tcp']
    while True:
        try:
            fields = {}
            lsof_result = Popen(lsof_args, shell=False, stdout=PIPE)
            lsof_lines = list()
            while True:
                line = lsof_result.stdout.readline().strip("\n")
                if not line:
                    break
                lsof_lines.append(line)
            lsof_result.kill()
            for name, service in services.items():
                pid_list = list()
                check_pid = False
                if name == "keystone-public":
                    check_pid = True
                    ps_result = Popen("pgrep -f --delimiter=' ' keystone-public", shell=True, stdout=PIPE)
                    pid_list = ps_result.stdout.readline().strip().split(' ')
                    ps_result.kill()
                elif name == "gnocchi-api":
                    check_pid = True
                    ps_result = Popen("pgrep -f --delimiter=' ' gnocchi-api", shell=True, stdout=PIPE)
                    pid_list = ps_result.stdout.readline().strip().split(' ')
                    ps_result.kill()
                api_count = 0
                db_count = 0
                rabbit_count = 0
                for line in lsof_lines:
                    if service['name'] is not None and service['name'] in line and (not check_pid or any(pid in line for pid in pid_list)):
                        if service['api-port'] is not None and service['api-port'] in line:
                            api_count += 1
                        elif db_port is not None and db_port in line:
                            db_count += 1
                        elif rabbit_port is not None and rabbit_port in line:
                            rabbit_count += 1
                fields[name] = {"api": api_count, "db": db_count, "rabbit": rabbit_count}
                influx_string += "{},'{}'='{}','{}'='{}' '{}'='{}','{}'='{}','{}'='{}'".format(measurement, "node", tags["node"], "service", name, "api", fields[name]["api"], "db", fields[name]["db"], "rabbit", fields[name]["rabbit"]) + "\n"
            p = Popen("curl -s -o /dev/null 'http://'{}':'{}'/write?db='{}'' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string), shell=True)
            p.communicate()
            influx_string = ""
        except KeyboardInterrupt:
            break
        except Exception:
            logging.error("api_request collection stopped unexpectedly with error: {}. Restarting process...".format(sys.exc_info()))
            time.sleep(3)

# returns the cores dedicated to platform use
def getPlatformCores(node, cpe):
    if cpe is True or node.startswith("compute"):
        logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
        core_list = list()
        try:
            with open("/etc/platform/worker_reserved.conf", "r") as f:
                for line in f:
                    if line.startswith("PLATFORM_CPU_LIST"):
                        core_list = line.split("=")[1].replace("\"", "").strip("\n").split(",")
                        core_list = [int(x) for x in core_list]
                        return core_list
        except Exception:
            logging.warning("skipping platform specific collection for {} due to error: {}".format(node, sys.exc_info()))
            return core_list
    else:
        return []


# determine if controller is active/standby
def isActiveController():
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    try:
        o = Popen("sm-dump", shell=True, stdout=PIPE)
        o.stdout.readline()
        o.stdout.readline()
        # read line for active/standby
        l = o.stdout.readline().strip("\n").split()
        per = l[1]
        o.kill()
        if per == "active":
            return True
        else:
            return False
    except Exception:
        if o is not None:
            o.kill()
        logging.error("sm-dump command could not be called properly. This is usually caused by a swact. Trying again on next call: {}".format(sys.exc_info()))
        return False


# checks whether the duration param has been set. If set, sleep; then kill processes upon waking up
def checkDuration(duration):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    if duration is None:
        return None
    else:
        time.sleep(duration)
        print("Duration interval has ended. Killing processes now")
        logging.warning("Duration interval has ended. Killing processes now")
        raise KeyboardInterrupt


# kill all processes and log each death
def killProcesses(tasks):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    for t in tasks:
        try:
            logging.info("{} data stopped collection".format(str(t.name)))
            t.terminate()
        except Exception:
            continue


# create database in InfluxDB and add it to Grafana
def createDB(influx_info, grafana_port, grafana_api_key):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    p = None
    try:
        logging.info("Adding database to InfluxDB and Grafana")
        # create database in InfluxDB if not already created. Will NOT overwrite previous db
        p = Popen("curl -s -XPOST 'http://'{}':'{}'/query' --data-urlencode 'q=CREATE DATABASE {}'".format(influx_info[0], influx_info[1], influx_info[2]), shell=True, stdout=PIPE)
        response = p.stdout.read().strip("\n")
        if response == "":
            raise Exception("An error occurred while creating the database: Please make sure the Grafana and InfluxDB services are running")
        else:
            logging.info("InfluxDB response: {}".format(response))
        p.kill()

        # add database to Grafana
        grafana_db = '{"name":"%s", "type":"influxdb", "url":"http://%s:%s", "access":"proxy", "isDefault":false, "database":"%s"}' % (influx_info[2], influx_info[0], influx_info[1], influx_info[2])
        p = Popen("curl -s 'http://{}:{}/api/datasources' -H 'Accept: application/json' -H 'Content-Type: application/json' -H 'Authorization: Bearer {}' --data-binary '{}'".format(influx_info[0], grafana_port, grafana_api_key, grafana_db), shell=True, stdout=PIPE)
        response = p.stdout.read().strip("\n")
        if response == "":
            raise Exception("An error occurred while creating the database: Please make sure the Grafana and InfluxDB services are running")
        else:
            logging.info("Grafana response: {}".format(response))
        p.kill()
    except KeyboardInterrupt:
        if p is not None:
            p.kill()
    except Exception as e:
        print(e.message)
        sys.exit(0)


# delete database from InfluxDB and remove it from Grafana
def deleteDB(influx_info, grafana_port, grafana_api_key):
    logging.basicConfig(filename="/tmp/livestream.log", filemode="a", format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    p = None
    try:
        answer = str(input("\nAre you sure you would like to delete {}? (Y/N): ".format(influx_info[2]))).lower()
    except Exception:
        answer = None
    if answer is None or answer == "" or answer == "y" or answer == "yes":
        try:
            logging.info("Removing database from InfluxDB and Grafana")
            print("Removing database from InfluxDB and Grafana. Please wait...")
            # delete database from InfluxDB
            p = Popen("curl -s -XPOST 'http://'{}':'{}'/query' --data-urlencode 'q=DROP DATABASE {}'".format(influx_info[0], influx_info[1], influx_info[2]), shell=True, stdout=PIPE)
            response = p.stdout.read().strip("\n")
            if response == "":
                raise Exception("An error occurred while removing the database: Please make sure the Grafana and InfluxDB services are running")
            else:
                logging.info("InfluxDB response: {}".format(response))
            p.kill()

            # get database ID for db removal
            p = Popen("curl -s -G 'http://{}:{}/api/datasources/id/{}' -H 'Accept: application/json' -H 'Content-Type: application/json' -H 'Authorization: Bearer {}'".format(influx_info[0], grafana_port, influx_info[2], grafana_api_key), shell=True, stdout=PIPE)
            id = p.stdout.read().split(":")[1].strip("}")
            if id == "":
                raise Exception("An error occurred while removing the database: Could not determine the database ID")
            p.kill()

            # remove database from Grafana
            p = Popen("curl -s -XDELETE 'http://{}:{}/api/datasources/{}' -H 'Accept: application/json' -H 'Content-Type: application/json' -H 'Authorization: Bearer {}'".format(influx_info[0], grafana_port, id, grafana_api_key), shell=True, stdout=PIPE)
            response = p.stdout.read().strip("\n")
            if response == "":
                raise Exception("An error occurred while removing the database: Please make sure the Grafana and InfluxDB services are running")
            else:
                logging.info("Grafana response: {}".format(response))
            p.kill()
        except KeyboardInterrupt:
            if p is not None:
                p.kill()
        except Exception as e:
            print(e.message)
        sys.exit(0)


# used for output log
def appendToFile(file, content):
    with open(file, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(content + '\n')
        fcntl.flock(f, fcntl.LOCK_UN)


# main program
if __name__ == "__main__":
    # make sure user is root
    if os.geteuid() != 0:
        print("Must be run as root!\n")
        sys.exit(0)

    # initialize variables
    cpe_lab = False
    influx_ip = influx_port = influx_db = ""
    external_if = ""
    influx_info = list()
    grafana_port = ""
    grafana_api_key = ""
    controller_services = list()
    compute_services = list()
    storage_services = list()
    rabbit_services = list()
    common_services = list()
    services = {}
    live_svc = ("live_stream.py",)
    collection_intervals = {"memtop": None, "memstats": None, "occtop": None, "schedtop": None, "load_avg": None, "cpu_count": None, "diskstats": None, "iostat": None, "filestats": None, "netstats": None, "postgres": None, "rabbitmq": None, "vswitch": None}
    duration = None
    unconverted_duration = ""
    collect_api_requests = False
    api_requests = ""
    auto_delete_db = False
    delete_db = ""
    collect_all_services = False
    all_services = ""
    fast_postgres_connections = False
    fast_postgres = ""
    config = configparser.ConfigParser()

    node = os.popen("hostname").read().strip("\n")

    # get info from engtools.conf
    try:
        conf_file = ""
        if "engtools.conf" in tuple(os.listdir(os.getcwd())):
            conf_file = os.getcwd() + "/engtools.conf"
        elif "engtools.conf" in tuple(os.listdir("/etc/engtools/")):
            conf_file = "/etc/engtools/engtools.conf"
        config.read(conf_file)
        if config.get("LabConfiguration", "CPE_LAB").lower() == "y" or config.get("LabConfiguration", "CPE_LAB").lower() == "yes":
            cpe_lab = True
        if node.startswith("controller"):
            external_if = config.get("CollectInternal", "{}_EXTERNAL_INTERFACE".format(node.upper().replace("-", "")))
        influx_ip = config.get("RemoteServer", "INFLUX_IP")
        influx_port = config.get("RemoteServer", "INFLUX_PORT")
        influx_db = config.get("RemoteServer", "INFLUX_DB")
        grafana_port = config.get("RemoteServer", "GRAFANA_PORT")
        grafana_api_key = config.get("RemoteServer", "GRAFANA_API_KEY")
        duration = config.get("LiveStream", "DURATION")
        unconverted_duration = config.get("LiveStream", "DURATION")
        api_requests = config.get("AdditionalOptions", "API_REQUESTS")
        delete_db = config.get("AdditionalOptions", "AUTO_DELETE_DB")
        all_services = config.get("AdditionalOptions", "ALL_SERVICES")
        fast_postgres = config.get("AdditionalOptions", "FAST_POSTGRES_CONNECTIONS")
        # additional options
        if api_requests.lower() == "y" or api_requests.lower() == "yes":
            collect_api_requests = True
        if delete_db.lower() == "y" or delete_db.lower() == "yes":
            auto_delete_db = True
        if all_services.lower() == "y" or all_services.lower() == "yes":
            collect_all_services = True
        if fast_postgres.lower() == "y" or fast_postgres.lower() == "yes":
            fast_postgres_connections = True
        # convert duration into seconds
        if duration == "":
            duration = None
        elif duration.endswith("s") or duration.endswith("S"):
            duration = duration.strip("s")
            duration = duration.strip("S")
            duration = int(duration)
        elif duration.endswith("m") or duration.endswith("M"):
            duration = duration.strip("m")
            duration = duration.strip("M")
            duration = int(duration) * 60
        elif duration.endswith("h") or duration.endswith("H"):
            duration = duration.strip("h")
            duration = duration.strip("H")
            duration = int(duration) * 3600
        elif duration.endswith("d") or duration.endswith("D"):
            duration = duration.strip("d")
            duration = duration.strip("D")
            duration = int(duration) * 3600 * 24
        controller_services = tuple(config.get("ControllerServices", "CONTROLLER_SERVICE_LIST").split())
        compute_services = tuple(config.get("ComputeServices", "COMPUTE_SERVICE_LIST").split())
        storage_services = tuple(config.get("StorageServices", "STORAGE_SERVICE_LIST").split())
        rabbit_services = tuple(config.get("RabbitmqServices", "RABBITMQ_QUEUE_LIST").split())
        common_services = tuple(config.get("CommonServices", "COMMON_SERVICE_LIST").split())
        static_svcs = tuple(config.get("StaticServices", "STATIC_SERVICE_LIST").split())
        openstack_services = tuple(config.get("OpenStackServices", "OPEN_STACK_SERVICE_LIST").split())
        skip_list = tuple(config.get("SkipList", "SKIP_LIST").split())
        exclude_list = tuple(config.get("ExcludeList", "EXCLUDE_LIST").split())
        # get collection intervals
        for i in config.options("Intervals"):
            if config.get("Intervals", i) == "" or config.get("Intervals", i) is None:
                collection_intervals[i] = None
            else:
                collection_intervals[i] = int(config.get("Intervals", i))
        # get api-stats services
        DB_PORT_NUMBER = config.get("ApiStatsConstantPorts", "DB_PORT_NUMBER")
        RABBIT_PORT_NUMBER = config.get("ApiStatsConstantPorts", "RABBIT_PORT_NUMBER")
        SERVICES = OrderedDict()
        SERVICES_INFO = tuple(config.get("ApiStatsServices", "API_STATS_STRUCTURE").split('|'))
        for service_string in SERVICES_INFO:
            service_tuple = tuple(service_string.split(';'))
            if service_tuple[2] != "" and service_tuple[2] != None:
                SERVICES[service_tuple[0]] = {'name': service_tuple[1], 'api-port': service_tuple[2]}
            else:
                SERVICES[service_tuple[0]] = {'name': service_tuple[1], 'api-port': None}
    except Exception:
        print("An error has occurred when parsing the engtools.conf configuration file: {}".format(sys.exc_info()))
        sys.exit(0)

    syseng_services = live_svc + static_svcs
    if cpe_lab is True:
        services["controller_services"] = controller_services + compute_services + storage_services + common_services
    else:
        controller_services += common_services
        compute_services += common_services
        storage_services += common_services
        services["controller_services"] = controller_services
        services["compute_services"] = compute_services
        services["storage_services"] = storage_services
        services["common_services"] = common_services
    services["syseng_services"] = syseng_services
    services["rabbit_services"] = rabbit_services

    influx_info.append(influx_ip)
    influx_info.append(influx_port)
    influx_info.append(influx_db)

    # add config options to log
    with open("/tmp/livestream.log", "w") as e:
        e.write("Configuration for {}:\n".format(node))
        e.write("-InfluxDB address: {}:{}\n".format(influx_ip, influx_port))
        e.write("-InfluxDB name: {}\n".format(influx_db))
        e.write("-CPE lab: {}\n".format(str(cpe_lab)))
        e.write(("-Collect API requests: {}\n".format(str(collect_api_requests))))
        e.write(("-Collect all services: {}\n".format(str(collect_all_services))))
        e.write(("-Fast postgres connections: {}\n".format(str(fast_postgres_connections))))
        e.write(("-Automatic database removal: {}\n".format(str(auto_delete_db))))
        if duration is not None:
            e.write("-Live stream duration: {}\n".format(unconverted_duration))
        e.close()

    # add POSTROUTING entry to NAT table
    if cpe_lab is False:
        # check controller-0 for NAT entry. If not there, add it
        if node.startswith("controller"):
            # use first interface if not specified in engtools.conf
            if external_if == "" or external_if is None:
                p = Popen("ifconfig", shell=True, stdout=PIPE)
                external_if = p.stdout.readline().split(":")[0]
                p.kill()
            appendToFile("/tmp/livestream.log", "-External interface for {}: {}".format(node, external_if))
            # enable IP forwarding
            p = Popen("sysctl -w net.ipv4.ip_forward=1 > /dev/null", shell=True)
            p.communicate()
            p = Popen("iptables -t nat -L --line-numbers", shell=True, stdout=PIPE)
            tmp = []
            # entries need to be removed in reverse order
            for line in p.stdout:
                tmp.append(line.strip("\n"))
            for line in reversed(tmp):
                l = " ".join(line.strip("\n").split()[1:])
                # if an entry already exists, remove it
                if l.startswith("MASQUERADE tcp -- anywhere"):
                    line_number = line.strip("\n").split()[0]
                    p1 = Popen("iptables -t nat -D POSTROUTING {}".format(line_number), shell=True)
                    p1.communicate()
            p.kill()
            appendToFile("/tmp/livestream.log", "-Adding NAT information to allow compute/storage nodes to communicate with remote server\n")
            # add new entry for both InfluxDB and Grafana
            p = Popen("iptables -t nat -A POSTROUTING -p tcp -o {} -d {} --dport {} -j MASQUERADE".format(external_if, influx_ip, influx_port), shell=True)
            p.communicate()
            p = Popen("iptables -t nat -A POSTROUTING -p tcp -o {} -d {} --dport {} -j MASQUERADE".format(external_if, influx_ip, grafana_port), shell=True)
            p.communicate()

    appendToFile("/tmp/livestream.log", "\nStarting collection at {}\n".format(datetime.datetime.utcnow()))
    tasks = []

    createDB(influx_info, grafana_port, grafana_api_key)

    try:
        node_type = str(node.split("-")[0])
        # if not a standard node, run the common functions with collect_all enabled
        if node_type != "controller" and node_type != "compute" and node_type != "storage":
            node_type = "common"
            collect_all_services = True

        if collection_intervals["memstats"] is not None:
            p = Process(target=collectMemstats, args=(influx_info, node, collection_intervals, services["{}_services".format(node_type)], services["syseng_services"], openstack_services, exclude_list, skip_list, collect_all_services), name="memstats")
            tasks.append(p)
            p.start()
        if collection_intervals["schedtop"] is not None:
            p = Process(target=collectSchedtop, args=(influx_info, node, collection_intervals, services["{}_services".format(node_type)], services["syseng_services"], openstack_services, exclude_list, skip_list, collect_all_services), name="schedtop")
            tasks.append(p)
            p.start()
        if collection_intervals["filestats"] is not None:
            p = Process(target=collectFilestats, args=(influx_info, node, collection_intervals, services["{}_services".format(node_type)], services["syseng_services"], exclude_list, skip_list, collect_all_services), name="filestats")
            tasks.append(p)
            p.start()
        if collection_intervals["occtop"] is not None:
            p = Process(target=collectOcctop, args=(influx_info, node, collection_intervals, getPlatformCores(node, cpe_lab)), name="occtop")
            tasks.append(p)
            p.start()
        if collection_intervals["load_avg"] is not None:
            p = Process(target=collectLoadavg, args=(influx_info, node, collection_intervals), name="load_avg")
            tasks.append(p)
            p.start()
        if collection_intervals["cpu_count"] is not None:
            p = Process(target=collectCpuCount, args=(influx_info, node, collection_intervals), name="cpu_count")
            tasks.append(p)
            p.start()
        if collection_intervals["memtop"] is not None:
            p = Process(target=collectMemtop, args=(influx_info, node, collection_intervals), name="memtop")
            tasks.append(p)
            p.start()
        if collection_intervals["diskstats"] is not None:
            p = Process(target=collectDiskstats, args=(influx_info, node, collection_intervals), name="diskstats")
            tasks.append(p)
            p.start()
        if collection_intervals["iostat"] is not None:
            p = Process(target=collectIostat, args=(influx_info, node, collection_intervals), name="iostat")
            tasks.append(p)
            p.start()
        if collection_intervals["netstats"] is not None:
            p = Process(target=collectNetstats, args=(influx_info, node, collection_intervals), name="netstats")
            tasks.append(p)
            p.start()
        if collect_api_requests is True and node_type == "controller":
            p = Process(target=collectApiStats, args=(influx_info, node, collection_intervals, SERVICES, DB_PORT_NUMBER, RABBIT_PORT_NUMBER), name="api_requests")
            tasks.append(p)
            p.start()

        if node_type == "controller":
            if collection_intervals["postgres"] is not None:
                p = Process(target=collectPostgres, args=(influx_info, node, collection_intervals), name="postgres")
                tasks.append(p)
                p.start()
                p = Process(target=collectPostgresConnections, args=(influx_info, node, collection_intervals, fast_postgres_connections), name="postgres_connections")
                tasks.append(p)
                p.start()
            if collection_intervals["rabbitmq"] is not None:
                p = Process(target=collectRabbitMq, args=(influx_info, node, collection_intervals), name="rabbitmq")
                tasks.append(p)
                p.start()
                p = Process(target=collectRabbitMqSvc, args=(influx_info, node, collection_intervals, services["rabbit_services"]), name="rabbitmq_svc")
                tasks.append(p)
                p.start()

        if node_type == "compute" or cpe_lab is True:
            if collection_intervals["vswitch"] is not None:
                p = Process(target=collectVswitch, args=(influx_info, node, collection_intervals), name="vswitch")
                tasks.append(p)
                p.start()

        print("Sending data to InfluxDB. Please tail /tmp/livestream.log")

        checkDuration(duration)
        # give a small delay to ensure services have started
        time.sleep(3)
        for t in tasks:
            os.wait()
    except KeyboardInterrupt:
        pass
    finally:
        # end here once duration param has ended or ctrl-c is pressed
        appendToFile("/tmp/livestream.log", "\nEnding collection at {}\n".format(datetime.datetime.utcnow()))
        if tasks is not None and len(tasks) > 0:
            killProcesses(tasks)
        if auto_delete_db is True:
            deleteDB(influx_info, grafana_port, grafana_api_key)
        sys.exit(0)
