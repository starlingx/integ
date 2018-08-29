#!/usr/bin/env python

"""
Copyright (c) 2017 Wind River Systems, Inc.

SPDX-License-Identifier: Apache-2.0

This script is for parsing post-data analysis. It takes the csv files generated from the parser scripts and imports
the data to an influx database. All influx information should be specified in the lab.conf file. Please see the wiki
for more details.
"""

import os
import sys
import time
import datetime
from optparse import OptionParser
from multiprocessing import Pool


# command line arguments
def init():
    parser = OptionParser()
    parser.add_option("-a", "--all", dest="parse_all", action="store_true", default=False, help="use this option to parse all csv files for all nodes specified within lab.conf")
    parser.add_option("-n", "--node", dest="node_list", action="append", type="string", help="the specific node(s) to be parsed, otherwise all nodes within lab.conf will be parsed")
    parser.add_option("-f", "--file", dest="file_list", action="append", type="string", help="the specific csv file(s) to be parsed. Must use with the -n option. Ex: -n controller-0 -f postgres-conns.csv")
    parser.add_option("-p", "--postgres_svc", dest="postgres_list", action="append", type="string", help="use this option to parse postgres CSV files given specific services. Ex:  -p nova")
    parser.add_option("-b", "--batch-size", dest="batch_size", action="store", type="int", default="100", help="Influx accepts data in batches. Use this option to change the batch size from the default value of 100. Note that Influx can timeout if the batch size is to large")
    (options, args) = parser.parse_args()
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        sys.exit(0)
    else:
        return options


# converts given UTC time into epoch time
def convertTime(file, node, start, lc, utcTime):
    try:
        # diskstats csv requires special work as no timestamp is provided
        if file.startswith("diskstats"):
            t = " ".join(start)
            pattern = '%Y-%m-%d %H%M'
            epoch = int(time.mktime(time.strptime(t, pattern)))
            # add 15 minutes to current timestamp
            epoch += 900 * lc
        else:
            if utcTime.endswith("AM"):
                pattern = '%m/%d/%Y %H:%M:%S'
                epoch = int(time.mktime(time.strptime(utcTime[:19], pattern)))
            elif utcTime.endswith("PM"):
                tmp = int(utcTime[11:13])
                if tmp < 12:
                    tmp += 12
                str1 = utcTime[:11]
                str2 = utcTime[13:19]
                utcTime = str1 + str(tmp) + str2
                pattern = '%m/%d/%Y %H:%M:%S'
                epoch = int(time.mktime(time.strptime(utcTime, pattern)))
            elif file.startswith("memstats") or file.startswith("filestats"):
                pattern = '%Y-%m-%d %H:%M:%S'
                epoch = int(time.mktime(time.strptime(utcTime[:19], pattern)))
            else:
                pattern = '%Y-%m-%d %H:%M:%S.%f'
                epoch = int(time.mktime(time.strptime(utcTime[:23], pattern)))
        return str(epoch)
    except Exception as e:
        appendToFile("/tmp/csv-to-influx.log", "Error: Issue converting time for {} for {}. Please check the csv and re-parse as some data may be incorrect\n-{}".format(file, node, e.message))
        return None


# go through each node folder to parse csv files
def processFiles(path, node, options, influx_info):
    prefixes = ["postgres-conns", "postgres", "memtop", "occtop", "iostat", "netstats", "rabbitmq", "schedtop", "vswitch", "filestats-summary", "memstats-summary", "diskstats"]
    if options.file_list is None:
        for file in os.listdir(path):
            if file.endswith(".csv"):
                if file.startswith(tuple(prefixes)):
                    if options.parse_all is True or options.node_list is not None:
                        parse(path, file, node, options, influx_info)
                    elif options.postgres_list is not None:
                        for svc in options.postgres_list:
                            if svc in list(file.split("_")):
                                parse(path, file, node, options, influx_info)
                            else:
                                continue
    # if -f option is used
    elif options.file_list is not None:
        for file in options.file_list:
            parse(path, file, node, options, influx_info)

    # let the log know when a thread has finished parsing a folder
    appendToFile("/tmp/csv-to-influx.log", "-Process for {} finished parsing at {}".format(node, datetime.datetime.utcnow()))


# parse the csv files and add data to influx
# needs to be cleaned up
def parse(path, file, node, options, influx_info):
    file_loc = os.path.join(path, file)
    # until able to access the file
    while True:
        if os.access(file_loc, os.R_OK):
            try:
                with open(file_loc, "r") as f:
                    file_name = file.replace("-", "_").replace(".csv", "").replace("_{}".format(node.replace("-", "_")),
                                                                                   "").strip("\n")
                    appendToFile("/tmp/csv-to-influx.log", "Parsing {} for {}".format(file_name, node))
                    header = f.readline().split(",")
                    # vswitch CSV files have no headers...
                    if file_name.startswith("vswitch"):
                        if file_name.replace("vswitch_", "").split("_")[0] == "engine":
                            header = "date/time,id,cpuid,rx-packets,tx-packets,tx-disabled,tx-overflow,rx-discard,tx-discard,usage".split(
                                ",")
                        elif file_name.replace("vswitch_", "").split("_")[0] == "interface":
                            header = "date/time,rx-packets,tx-packets,rx-bytes,tx-bytes,tx-errors,rx-errors,tx-discards,rx-discards,rx-floods,rx-no-vlan".split(
                                ",")
                        elif file_name.replace("vswitch_", "").split("_")[0] == "port":
                            header = "date/time,rx-packets,tx-packets,rx-bytes,tx-bytes,tx-errors,rx-errors,rx-nombuf".split(
                                ",")
                    elif file_name.startswith("memstats"):
                        if header[0] != "Date":
                            header = "date/time,rss,vrz"
                    influx_string = ""
                    measurement = ""
                    tag_names = ["node"]
                    init_tags = [node]
                    line_count = 0
                    batch = 0
                    start_time = ""  # used for diskstats
                    bad_string = False
                    # set tag information needed for influx. Each file needs different things
                    if file_name.startswith("postgres_conns"):
                        measurement = "postgres_connections"
                    elif file_name.startswith("postgres"):
                        if file_name.endswith("_size"):
                            measurement = "postgres_db_size"
                            service = file_name.replace("postgres_", "").replace("_size", "")
                            if service == "size":
                                service = "postgres"
                            tag_names = ["node", "service"]
                            init_tags = [node, service]
                        else:
                            measurement = "postgres_svc_stats"
                            service = file_name.replace("postgres_", "").split("_")[0]
                            tag_names = ["node", "service", "schema", "table"]
                            init_tags = [node, service]
                    elif file_name.startswith("memtop"):
                        if file_name == "memtop_detailed":
                            measurement = "memtop_detailed"
                        else:
                            measurement = "memtop"
                    elif file_name.startswith("occtop"):
                        if file_name == "occtop_detailed":
                            measurement = "occtop_detailed"
                        else:
                            measurement = "occtop"
                    elif file_name.startswith("iostat"):
                        measurement = "iostat"
                        tag_names = ["node", "device"]
                        init_tags = [node, header[1]]
                    elif file_name.startswith("netstats"):
                        measurement = "netstats"
                        interface = file.replace("{}-".format(measurement), "").replace("{}-".format(node), "").replace(
                            ".csv", "")
                        tag_names = ["node", "interface"]
                        init_tags = [node, interface]
                    elif file_name.startswith("rabbitmq"):
                        if file_name.endswith("info"):
                            measurement = "rabbitmq_svc"
                            service = file_name.replace("rabbitmq_", "")
                            tag_names = ["node", "service"]
                            init_tags = [node, service]
                        else:
                            measurement = "rabbitmq"
                    elif file_name.startswith("schedtop"):
                        measurement = "schedtop"
                        service = file_name.replace("schedtop_", "").replace("_", "-")
                        tag_names = ["node", "service"]
                        init_tags = [node, service]
                    elif file_name.startswith("vswitch"):
                        measurement = "vswitch"
                        identifier = file_name.replace("vswitch_", "").split("_")
                        tag_names = ["node", identifier[0]]
                        if identifier[0] == "engine":
                            init_tags = [node, "engine_id_{}".format(identifier[1])]
                        elif identifier[0] == "interface":
                            init_tags = [node, identifier[1]]
                        elif identifier[0] == "port":
                            init_tags = [node, "port_{}".format(identifier[1])]
                    elif file_name.startswith("filestats"):
                        measurement = "filestats"
                        service = file_name.replace("filestats_summary_", "").replace(".csv", "").replace("_", "-")
                        tag_names = ["node", "service"]
                        init_tags = [node, service]
                    elif file_name.startswith("memstats"):
                        measurement = "memstats"
                        service = file_name.replace("memstats_summary_", "").replace(".csv", "").replace("_", "-")
                        tag_names = ["node", "service"]
                        init_tags = [node, service]
                    elif file_name.startswith("diskstats"):
                        measurement = "diskstats"
                        mount = file_name.replace("diskstats_", "")
                        tag_names = ["node", "mount", "file_system", "type"]
                        init_tags = [node, mount]
                        # find the bz2 file with the earliest date
                        start = float('inf')
                        for t in os.listdir(path):
                            if t.startswith(node) and t.endswith("bz2"):
                                next = int(
                                    str(t.replace("{}_".format(node), "")[2:15]).replace("-", "").replace("_", ""))
                                if next < start:
                                    start = next
                                    start_time = t.split("_")[1:3]

                    # go through header, determine the fields, skip the tags
                    field_names = []
                    for i in header:
                        j = i.lower().replace(" ", "_").replace("-", "_").replace("used(%)", "usage").replace("(%)", "").replace("(s)", "").strip(" ").strip("\n")
                        if j in tag_names or i in init_tags or j == 'pid' or j == 'name':
                            continue
                        else:
                            # for occtop core info
                            if j.isdigit():
                                j = "core_{}".format(j)
                            field_names.append(j)

                    # go through each line
                    bad_count = 0
                    for lines in f:
                        line = lines.strip("\n").split(",")
                        timestamp = convertTime(file, node, start_time, line_count, line[0].strip("\n"))
                        if timestamp is None:
                            bad_count += 1
                            if bad_count == 3:
                                bad_string = True
                                break
                            else:
                                continue
                        tag_values = init_tags
                        field_values = []
                        line_count += 1
                        batch += 1

                        # go through data in each line and determine whether it belongs to a tag or a field
                        for word in line:
                            word = word.strip("\n")
                            # is non-number, interface, or device, add to tags, otherwise add to fields
                            if word.replace("_", "").replace("-", "").replace(" ", "").isalpha() or (word in init_tags) or word.endswith(".info") or word.startswith("ext"):
                                tag_values.append(word)
                            elif word.startswith("/dev"):
                                tag_values.append(word.split("/")[-1])
                            elif word.startswith("<rabbit"):
                                continue
                            else:
                                if word == "" or word == "\n":
                                    word = '0'
                                if word.endswith("%"):
                                    word = word.strip("%")
                                if file_name.startswith("diskstats"):
                                    if word.endswith("k"):
                                        word = word.strip("k")
                                        word = str(float(word) * 1000)
                                    if word.endswith("M"):
                                        word = word.strip("M")
                                        word = str(float(word) * 1000 * 1000)
                                    if word.endswith("G"):
                                        word = word.strip("G")
                                        word = str(float(word) * 1000 * 1000 * 1000)
                                    if word.endswith("T"):
                                        word = word.strip("T")
                                        word = str(float(word) * 1000 * 1000 * 1000 * 1000)
                                field_values.append(word.strip(" "))
                        # problem with the generated string? Print error and close file
                        generated_string = generateString(file, node, measurement, tag_names, tag_values, field_names, field_values, line_count, timestamp)
                        if generated_string is None:
                            bad_count += 1
                            if bad_count == 3:
                                bad_string = True
                                break
                            else:
                                continue
                        else:
                            bad_string = False
                            bad_count = 0
                            influx_string += generated_string
                        # send data to influx in batches
                        if bad_string is False:
                            if batch >= options.batch_size:
                                writing = True
                                influx_string = "curl -s -i -o /dev/null -XPOST 'http://'{}':'{}'/write?db='{}'&precision=s' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string.strip("\n"))
                                while writing:
                                    begin = time.time()
                                    os.system(influx_string + "\n")
                                    end = time.time()
                                    if end - begin >= 4.5:
                                        appendToFile("/tmp/csv-to-influx.log", "Timeout warning: {} for {}. Retrying now".format(file_name, node))
                                    else:
                                        batch = 0
                                        influx_string = ""
                                        writing = False
                    # leave while loop due to incorrectly formatted csv data
                    if bad_string:
                        f.close()
                        break
                    else:
                        # get remainder of data from csv
                        if batch < options.batch_size:
                            writing = True
                            influx_string = "curl -s -i -o /dev/null -XPOST 'http://'{}':'{}'/write?db='{}'&precision=s' --data-binary '{}'".format(influx_info[0], influx_info[1], influx_info[2], influx_string.strip("\n"))
                            while writing:
                                begin = time.time()
                                os.system(influx_string + "\n")
                                end = time.time()
                                if end - begin >= 4.5:
                                    appendToFile("/tmp/csv-to-influx.log", "Timeout warning: {} for {}. Retrying now".format(file_name, node))
                                else:
                                    writing = False
                f.close()
                appendToFile("/tmp/csv-to-influx.log",
                             "{} lines parsed in {} for {}".format(line_count, file_name, node))
                break
            except IOError as e:
                appendToFile("/tmp/csv-to-influx.log", "Error: Issue opening {}\n-{}".format(file_loc, e.message))
            except (KeyboardInterrupt, SystemExit):
                sys.exit(0)
        else:
            appendToFile("/tmp/csv-to-influx.log", "Error: Could not access {}".format(file_loc))


# generate http api string to send data to influx
def generateString(file, node, meas, tag_n, tag_v, field_n, field_v, lc, date):
    base = "{},".format(meas)
    try:
        if file.startswith("diskstats"):
            for i in range(len(tag_n)):
                if i == len(tag_n)-1:
                    base = base + "'{}'='{}' ".format(tag_n[i], str(tag_v[i]))
                else:
                    base = base + "'{}'='{}',".format(tag_n[i], str(tag_v[i]))
            for i in range(len(field_v)):
                if str(field_v[i]).replace(".", "").isdigit():
                    if i == len(field_v)-1:
                        base = base + "'{}'='{}' {}".format(field_n[i], str(field_v[i]), date)
                    else:
                        base = base + "'{}'='{}',".format(field_n[i], str(field_v[i]))
                else:
                    appendToFile("/tmp/csv-to-influx.log", "Error: Issue with line {} with {} for {}. Please check the csv and re-parse as some data may be incorrect".format(lc, file, node))
                    return None
        else:
            for i in range(len(tag_n)):
                if i == len(tag_n)-1:
                    base = base + "'{}'='{}' ".format(tag_n[i], str(tag_v[i]))
                else:
                    base = base + "'{}'='{}',".format(tag_n[i], str(tag_v[i]))
            for i in range(1, len(field_v)):
                if str(field_v[i]).replace(".", "").isdigit():
                    if i == len(field_v)-1:
                        base = base + "'{}'='{}' {}".format(field_n[i], str(field_v[i]), date)
                    else:
                        base = base + "'{}'='{}',".format(field_n[i], str(field_v[i]))
                else:
                    appendToFile("/tmp/csv-to-influx.log", "Error: Issue with line {} with {} for {}. Please check the csv and re-parse as some data may be incorrect".format(lc, file, node))
                    return None
        return base + '\n'
    except Exception as e:
        appendToFile("/tmp/csv-to-influx.log", "Error: Issue with http api string with {} for {}\n-{}".format(file, node, e.message))
        return None


# append to error log
def appendToFile(file, content):
    with open(file, "a") as f:
        f.write(content + '\n')


# main method
if __name__ == "__main__":
    # get command-line args
    options = init()
    controller_list = []
    compute_list = []
    storage_list = []
    influx_host = influx_port = influx_db = ""
    influx_info = []
    pool_size = 0

    # create the files
    file = open("/tmp/csv-to-influx.log", "w")
    file.close()
    file = open("output.txt", "w")
    file.close()
    appendToFile("/tmp/csv-to-influx.log", "Starting parsing at {}".format(datetime.datetime.utcnow()))
    appendToFile("/tmp/csv-to-influx.log", "----------------------------------------------")

    # get node and influx info from lab.conf
    with open("lab.conf", "r") as lc:
        for lines in lc:
            line = lines.strip("\n")
            if line.startswith("CONTROLLER_LIST"):
                controller_list = list(line.strip(" ").split("="))[1].strip("\"").split(" ")
            elif line.startswith("COMPUTE_LIST"):
                compute_list = list(line.strip(" ").split("="))[1].strip("\"").split(" ")
            elif line.startswith("STORAGE_LIST"):
                storage_list = list(line.strip(" ").split("="))[1].strip("\"").split(" ")
            elif line.startswith("INFLUX_HOST"):
                influx_host = list(line.strip(" ").split("="))[1].strip("\"").split(" ")[0]
            elif line.startswith("INFLUX_PORT"):
                influx_port = list(line.strip(" ").split("="))[1].strip("\"").split(" ")[0]
            elif line.startswith("INFLUX_DB"):
                influx_db = list(line.strip(" ").split("="))[1].strip("\"").split(" ")[0]
                break
    lc.close()

    influx_info.append(influx_host)
    influx_info.append(influx_port)
    influx_info.append(influx_db)

    # if -n option is used, remove unneeded nodes
    if options.node_list is not None:
        tmp_controller_list = []
        tmp_compute_list = []
        tmp_storage_list = []
        for n in controller_list:
            if n in options.node_list:
                tmp_controller_list.append(n)
        for n in compute_list:
            if n in options.node_list:
                tmp_compute_list.append(n)
        for n in storage_list:
            if n in options.node_list:
                tmp_storage_list.append(n)
        controller_list = tmp_controller_list
        compute_list = tmp_compute_list
        storage_list = tmp_storage_list

    pool_size = len(controller_list) + len(compute_list) + len(storage_list)

    if options.file_list is not None and options.parse_all is True:
        print("You cannot use the -a option with the -f option")
        sys.exit(0)
    if options.postgres_list is not None and options.file_list is not None:
        print("You cannot use the -p option with the -f option")
        sys.exit(0)
    if options.parse_all is True and options.node_list is not None:
        print("You cannot use the -a option with the -n option.  Ex: -n controller-0")
        sys.exit(0)
    if options.file_list is not None and options.node_list is None:
        print("You must specify a node and a file.  Ex: -n controller-0 -f postgres-conns.csv")
        sys.exit(0)

    working_dir = os.getcwd()
    pool = Pool(processes=pool_size)
    proc_list = []

    print("Sending data to InfluxDB. Please tail /tmp/csv-to-influx.log")

    # create a process per node
    if len(controller_list) > 0:
        for i in range(len(controller_list)):
            path = os.path.join(working_dir, controller_list[i])
            proc_list.append(pool.apply_async(processFiles, (path, controller_list[i], options, influx_info,)))

    if len(compute_list) > 0:
        for i in range(len(compute_list)):
            path = os.path.join(working_dir, compute_list[i])
            proc_list.append(pool.apply_async(processFiles, (path, compute_list[i], options, influx_info,)))

    if len(storage_list) > 0:
        for i in range(len(storage_list)):
            path = os.path.join(working_dir, storage_list[i])
            proc_list.append(pool.apply_async(processFiles, (path, storage_list[i], options, influx_info,)))

    pool.close()
    pool.join()
