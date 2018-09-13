#!/bin/bash

username="wrsroot"
password="Li69nux*"
test_duration="30"
wait_duration="5"
udp_find_0_frameloss="1"
udp_max_iter="20"
udp_granularity="100000"
result_dir="/home/${username}/benchmark_results"
summary_file="${result_dir}/benchmark_summary.xls"
host=""
remote=""
controllers=()
computes=()
nodes=()
max_compute_node="10"
interfaces=("")
# udp header total length: Ethernet header ( 14 ) + CRC ( 4 ) + IPv4 header ( 20 ) + UDP header ( 8 )
udp_header_len="46"
# icmp header total length: ICMP header ( 8 ) + IPv4 header ( 20 )
icmp_header_len="28"
frame_sizes=(64 128 256 512 1024 1280 1518)
ssh_opt="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -q"
# ports used for different kind of traffics except hiprio. these are chosen randomly since they are not used
# 8000 - storage; 8001 - migration; 8002 - default; 8003 - drbd
controller_ports=(8000 8001 8002 8003)
compute_ports=(8000 8001 8002)
traffic_types=(storage migration default drbd)
flow_ids=(1:20 1:30 1:40 1:50)

function exec_cmd {
    node="$1"
    cmd="$2"

    if [[ "${node}" == *"${host}"* ]]; then
        echo "$(bash -c "${cmd}")"
    else
        echo "$(ssh ${ssh_opt} ${username}@${node} "${cmd}")"
    fi
}

function iperf3_server_start {
    local server="$1"
    local result="$2"
    local port="$3"
    local cmd="iperf3 -s"

    if [ "${port}" ]; then
        cmd="${cmd} -p ${port}"
    fi
    cmd="nohup ${cmd} > ${result} 2>&1 &"
    $(exec_cmd "${server}" "${cmd}")
}

function iperf3_client_tcp_start {
    local result="${result_dir}/throughput"
    local cmd=""
    local client="$1"
    local server="$2"
    local port="$3"

    cmd="iperf3 -t ${test_duration} -c $(get_ip_addr "${server}")"
    if [ "${port}" ]; then
        cmd="${cmd} -p ${port} -O ${wait_duration}"
        result="${result}_parallel_${port}"
    else
        result="${result}_tcp"
        if [[ "${server}" == *"infra"* ]]; then
            result="${result}_infra"
        fi
    fi
    $(exec_cmd "${client}" "${cmd} > ${result} 2>&1")
}

function iperf3_client_udp_start {
    local result="${result_dir}/throughput_udp"
    local cmd=""
    local client="$1"
    local server="$2"
    local frame_size="$3"
    local bw="0"

    if [ "${4}" ]; then
        bw="${4}"
    fi

    cmd="iperf3 -u -t ${test_duration} -c $(get_ip_addr ${server})"
    if [ ${frame_size} ]; then
        cmd="${cmd} -l ${frame_size}"
        result="${result}_$[${frame_size}+${udp_header_len}]"
    fi

    if [[ ${server} == *"infra"* ]]; then
        result="${result}_infra"
    fi

    $(exec_cmd "${client}" "${cmd} -b ${bw} >> ${result} 2>&1" )
}

function iperf3_stop {
    local node="$1"
    local cmd="pkill iperf3"
    $(exec_cmd "${node}" "${cmd}")
}

function get_ip_addr {
    arp -a | grep -oP "(?<=$1 \()[^)]*" | head -n 1
}

function throughput_tcp_test {
    for (( i = 0; i < ${#nodes[@]} ; i+=2 )); do
        for interface in "${interfaces[@]}"; do
            local interface_name="management"
            local interface_suffix=""
            local result_suffix=""
            if [ "${interface}" == "infra" ]; then
                interface_name="infrastructure"
                interface_suffix="-infra"
                result_suffix="_infra"
            fi
            local result_file="${result_dir}/throughput_tcp${result_suffix}"
            printf "Running TCP throughput test between ${nodes[${i}]} and ${nodes[$[${i}+1]]}'s ${interface_name} network..."
            iperf3_server_start ${nodes[$[${i}+1]]}${interface_suffix} ${result_file}
            iperf3_client_tcp_start ${nodes[${i}]}${interface_suffix} ${nodes[$[${i}+1]]}${interface_suffix}
            iperf3_stop ${nodes[$[${i}+1]]}${interface_suffix}
            result=$(exec_cmd "${nodes[${i}]}" "awk '/sender/ {print \$7 \" \" \$8}' ${result_file}")
            printf " Done (${result})\n"
        done
    done
}

function throughput_udp_test {
    for (( i = 0; i < ${#nodes[@]} ; i+=2 )); do
        for interface in "${interfaces[@]}"; do
            local interface_name="management"
            local interface_suffix=""
            local result_suffix=""
            if [ "${interface}" == "infra" ]; then
                interface_name="infrastructure"
                interface_suffix="-infra"
                result_suffix="_infra"
            fi
            echo "Running UDP throughput test between ${nodes[${i}]} and ${nodes[$[${i}+1]]}'s ${interface_name} network"
            for frame_size in "${frame_sizes[@]}"; do
                local max_bw="0"
                local min_bw="0"
                local cur_bw="0"
                local old_bw="0"
                local result=""
                local result_unit=""
                local frame_loss=""
                local max_result=""
                local max_result_unit=""
                local max_frame_loss=""
                local result_file="${result_dir}/throughput_udp_${frame_size}${result_suffix}"
                local iter="0"
                local diff=""
                printf "\tFrame size = ${frame_size}..."
                while true; do
                    iperf3_server_start ${nodes[$[${i}+1]]}${interface_suffix} ${result_file}
                    iperf3_client_udp_start ${nodes[${i}]}${interface_suffix} ${nodes[$[${i}+1]]}${interface_suffix} $[${frame_size}-${udp_header_len}] ${cur_bw}
                    iperf3_stop ${nodes[$[${i}+1]]}${interface_suffix}
                    result=$(exec_cmd "${nodes[${i}]}" "awk '/%/ {print \$7}' ${result_file} | tail -n1")
                    result_unit=$(exec_cmd "${nodes[${i}]}" "awk '/%/ {print \$8}' ${result_file} | tail -n1")
                    frame_loss=$(exec_cmd "${nodes[${i}]}" "awk '/%/ {print \$12}' ${result_file} | tail -n1 | tr -d '()%'")
                    if [ "${udp_find_0_frameloss}" == "1" ]; then
                        if [ "${iter}" -eq "0" ]; then
                            max_result="${result}"
                            max_result_unit="${result_unit}"
                            max_frame_loss="${frame_loss}"
                        fi
                        if [ $(echo ${frame_loss} | grep e) ]; then
                            frame_loss="$(echo ${frame_loss} | sed 's/e/*10^/g;s/ /*/' )"
                        fi
                        if [ "$(echo "${frame_loss} > 0" | bc -l)" -eq "1" ]; then
                            max_bw="${result}"
                            if [ "${result_unit}" == "Kbits/sec" ]; then
                                max_bw="$(echo "(${max_bw} * 1000) / 1" | bc)"
                            elif [ "${result_unit}" == "Mbits/sec" ]; then
                                max_bw="$(echo "(${max_bw} * 1000000) / 1" | bc)"
                            elif [ "${result_unit}" == "Gbits/sec" ]; then
                                max_bw="$(echo "(${max_bw} * 1000000000) / 1" | bc)"
                            fi
                        else
                            if [ "${iter}" -eq "0" ]; then
                                break
                            else
                                min_bw="${result}"
                                if [ "${result_unit}" == "Kbits/sec" ]; then
                                    min_bw="$(echo "(${min_bw} * 1000) / 1" | bc)"
                                elif [ "${result_unit}" == "Mbits/sec" ]; then
                                    min_bw="$(echo "(${min_bw} * 1000000) / 1" | bc)"
                                elif [ "${result_unit}" == "Gbits/sec" ]; then
                                    min_bw="$(echo "(${min_bw} * 1000000000) / 1" | bc)"
                                fi
                            fi
                        fi
                        old_bw="${cur_bw}"
                        cur_bw="$[(${max_bw} + ${min_bw}) / 2]"
                        diff="$(echo "$[${cur_bw} - ${old_bw}]" | tr -d '-')"
                        #break
                        ((iter++))
                        if [ "${diff}" -lt "${udp_granularity}" ]; then
                            break
                        fi
                        if [ "${udp_max_iter}" -ne "0" ] && [ "${iter}" -ge "${udp_max_iter}" ]; then
                            break
                        fi
                    else
                        break
                    fi
                done
                if [ "${udp_find_0_frameloss}" == "1" ]; then
                    printf " Done (%s %s @ %s%% & %s %s @ %s%%)\n" "${max_result}" "${max_result_unit}" "${max_frame_loss}" "${result}" "${result_unit}" "${frame_loss}"
                else
                    printf " Done (%s %s @ %s%%)\n" "${result}" "${result_unit}" "${frame_loss}"
                fi
            done
        done
    done
}

function throughput_parallel_test {
    local dev=""
    local ip_addr=""
    local interface_name=""
    local interface_suffix=""
    local result_file="${result_dir}/throughput_parallel"
    # get device name of the interface
    if [ "${#interfaces[@]}" -gt "1"  ]; then
        interface_name="infrastructure"
        interface_suffix="-infra"
        ip_addr=$(ping -c1 ${host}-infra | awk -F'[()]' '/PING/{print $2}')
    else
        interface_name="management"
        ip_addr=$(ping -c1 ${host} | awk -F'[()]' '/PING/{print $2}')
    fi
    dev=$(ifconfig | grep -B1 "inet ${ip_addr}" | awk '$1!="inet" && $1!="--" {print $1}')


    # set all the filters
    for node in ${nodes[@]}; do
        local ports=("${controller_ports[@]}")
        if [[ "${node}" == *"compute"* ]]; then
            ports=("${compute_ports[@]}")
        fi
        for i in $(seq 0 $[${#ports[@]} - 1]); do
            if [ ${traffic_types[i]} != "default" ]; then
                tc_dport="tc filter add dev ${dev} protocol ip parent 1:0 prio 1 u32 match ip protocol 6 0xff match ip dport ${ports[i]} 0xffff flowid ${flow_ids[i]}"
                tc_sport="tc filter add dev ${dev} protocol ip parent 1:0 prio 1 u32 match ip protocol 6 0xff match ip sport ${ports[i]} 0xffff flowid ${flow_ids[i]}"
                $(exec_cmd "${node}" "echo ${password} | sudo -S  bash -c '${tc_dport}; ${tc_sport}' > /dev/null 2>&1")
            fi
        done
    done

    # run the tests
    for (( i = 0; i < ${#nodes[@]} ; i+=2 )); do
        local ports=("${controller_ports[@]}")
        if [[ "${nodes[${i}]}" == *"compute"* ]]; then
            ports=("${compute_ports[@]}")
        fi
        printf "Running parallel throughput test between ${nodes[${i}]} and ${nodes[$[${i}+1]]}'s ${interface_name} network..."

        # start the servers
        for port in "${ports[@]}"; do
            iperf3_server_start "${nodes[$[${i}+1]]}${interface_suffix}" "${result_file}_${port}" "${port}"
        done
        #start the clients
        for port in "${controller_ports[@]}"; do
            iperf3_client_tcp_start ${nodes[${i}]}${interface_suffix} ${nodes[$[${i}+1]]}${interface_suffix} ${port} &
        done
        sleep $[${test_duration} + ${wait_duration} + 1]
        iperf3_stop ${nodes[$[${i}+1]]}${interface_suffix}
        printf " Done\n"

        # get results
        for j in $(seq 0 $[${#ports[@]} - 1]); do
            result=$(exec_cmd "${nodes[${i}]}" "awk '/sender/ {print \$7 \" \" \$8}' ${result_file}_${ports[${j}]}")
            printf "\t${traffic_types[$j]} = ${result}\n"
        done
    done

    # remove all the filters
    for node in ${nodes[@]}; do
        local handles=()
        local ports=("${controller_ports[@]}")
        if [[ "${node}" == *"compute"* ]]; then
            ports=("${compute_ports[@]}")
        fi
        handles=($(exec_cmd "${node}" "/usr/sbin/tc filter show dev ${dev} | awk '/filter/ {print \$10}' | tail -n $[(${#ports[@]} - 1) * 2 ]"))
        for handle in "${handles[@]}"; do
            $(exec_cmd "${node}" "echo ${password} | sudo -S /usr/sbin/tc filter delete dev ${dev} parent 1: handle ${handle} prio 1 u32 > /dev/null 2>&1")
        done
    done
}

function latency_test {
    for (( i = 0; i < ${#nodes[@]} ; i+=2 )); do
        for interface in "${interfaces[@]}"; do
            local interface_name="management"
            local interface_suffix=""
            local result_suffix=""
            if [ "${interface}" == "infra" ]; then
                interface_name="infrastructure"
                interface_suffix="-infra"
                result_suffix="_infra"
            fi
            echo "Running latency test between ${nodes[${i}]} and ${nodes[$[${i}+1]]}'s ${interface_name} network"
            for frame_size in "${frame_sizes[@]}"; do
                local result_file="${result_dir}/latency_${frame_size}${result_suffix}"
                printf "\tFrame size = ${frame_size}..."
                $(exec_cmd "${nodes[${i}]}" "ping -s $[${frame_size}-8] -w ${test_duration} -i 0.2 ${nodes[$[${i}+1]]}${interface_suffix} > ${result_file} 2>&1")
                result=$(exec_cmd "${nodes[${i}]}" "awk '/rtt/ {print \$2 \" = \" \$4 \" \" \$5}' ${result_file}")
                printf " Done (%s)\n" "${result}"
            done
        done
    done
}

function setup {
    for node in ${nodes[@]}; do
        iperf3_stop "${node}"
        $(exec_cmd "${node}" "rm -rf ${result_dir}; mkdir -p ${result_dir}")
    done
}

function get_remote_results {
    for node in ${nodes[@]}; do
        if [ "${node}" != "${host}" ]; then
            mkdir ${result_dir}/${node}
            scp ${ssh_opt} ${username}@${node}:${result_dir}/* ${result_dir}/${node} > /dev/null 2>&1
        fi
    done
}

function get_interface_info {
    local dev=""
    local ip_addr=""
    printf "Network interfaces info\n" >> ${summary_file}
    for interface in "${interfaces[@]}"; do
        local interface_suffix=""
        local interface_name="management"
        if [ "${interface}" == "infra" ]; then
            interface_name="infrastructure"
            interface_suffix="-infra"
        fi
        ip_addr=$(ping -c1 ${host}${interface_suffix} | awk -F'[()]' '/PING/{print $2}')
        dev=$(ifconfig | grep -B1 "inet ${ip_addr}" | awk '$1!="inet" && $1!="--" {print $1}')
        printf "%s network interface\n" "${interface_name}" >> ${summary_file}
        echo ${password} | sudo -S ethtool ${dev} >> ${summary_file}
    done
}

function generate_summary {
    local header=""
    local result=""
    local result_file=""

    printf "Summary\n\n" > ${summary_file}
    printf "Throughput TCP\n" >> ${summary_file}
    for (( i = 0; i < ${#nodes[@]} ; i+=2 )); do
        for interface in "${interfaces[@]}"; do
            local node_type="controller"
            local interface_type="mgmt"
            local result_suffix=""
            if [[ "${nodes[${i}]}" == *"compute"* ]]; then
                node_type="compute"
            fi
            if [ "${interface}" == "infra" ]; then
                interface_type="infra"
                result_suffix="_infra"
            fi
            header="${header},${node_type}'s ${interface_type}"
            result_file="${result_dir}"
            if [ ${node_type} == "compute" ]; then
                result_file="${result_file}/${nodes[${i}]}"
            fi
            result_file="${result_file}/throughput_tcp${result_suffix}"
            result="${result},$(awk '/sender/ {print $7 " " $8}' ${result_file})"
        done
    done
    printf "%s\n%s\n\n" "${header}" "${result}" >> ${summary_file}

    printf "Throughput UDP\n" >> ${summary_file}
    header=",frame,max throughput,max frameloss"
    if [ "${udp_find_0_frameloss}" == "1" ]; then
        header="${header},final throughput, final frameloss"
    fi
    for (( i = 0; i < ${#nodes[@]} ; i+=2 )); do
        for interface in "${interfaces[@]}"; do
            local node_type="controller"
            local interface_type="mgmt"
            local result_suffix=""
            if [[ "${nodes[${i}]}" == *"compute"* ]]; then
                node_type="compute"
            fi
            if [ "${interface}" == "infra" ]; then
                interface_type="infra"
                result_suffix="_infra"
            fi
            printf "%s's %s\n%s\n" "${node_type}" "${interface_type}" "${header}" >> ${summary_file}
            result_file=${result_dir}
            if [ ${node_type} == "compute" ]; then
                result_file="${result_file}/${nodes[${i}]}"
            fi
            for frame in ${frame_sizes[@]}; do
                result="${frame},$(awk '/%/ {print $7 " " $8}' ${result_file}/throughput_udp_${frame}${result_suffix} | head -n1),$(awk '/%/ {print $12}' ${result_file}/throughput_udp_${frame}${result_suffix} | head -n1 | tr -d '()')"
                if [ "${udp_find_0_frameloss}" == "1" ]; then
                    result="${result},$(awk '/%/ {print $7 " " $8}' ${result_file}/throughput_udp_${frame}${result_suffix} | tail -n1),$(awk '/%/ {print $12}' ${result_file}/throughput_udp_${frame}${result_suffix} | tail -n1 | tr -d '()')"
                fi
                printf ",%s\n" "${result}" >> ${summary_file}
            done
            printf "\n" >> ${summary_file}
        done
    done

    printf "Parallel throughput result\n" >> ${summary_file}
    header=",Node type"
    for traffic_type in "${traffic_types[@]}"; do
        header="${header},${traffic_type}"
    done
    printf "%s\n" "${header}" >> ${summary_file}
    for (( i = 0; i < ${#nodes[@]} ; i+=2 )); do
        local node_type="controller"
        local ports=("${controller_ports[@]}")
        if [[ "${nodes[${i}]}" == *"compute"* ]]; then
            node_type="compute"
        fi
        result_file=${result_dir}
        if [ ${node_type} == "compute" ]; then
            ports=("${compute_ports[@]}")
            result_file="${result_file}/${nodes[${i}]}"
        fi
        result=",${node_type}"
        for port in "${ports[@]}"; do
            result="${result},$(awk '/sender/ {print $7 " " $8}' ${result_file}/throughput_parallel_${port})"
        done
        printf "%s\n" "${result}" >> ${summary_file}
    done

    printf "\nLatency result in ms\n" >> ${summary_file}
    for (( i = 0; i < ${#nodes[@]} ; i+=2 )); do
        for interface in "${interfaces[@]}"; do
            local node_type="controller"
            local interface_type="mgmt"
            local result_suffix=""
            if [[ "${nodes[${i}]}" == *"compute"* ]]; then
                node_type="compute"
            fi
            if [ "${interface}" == "infra" ]; then
                interface_type="infra"
                result_suffix="_infra"
            fi
            printf "%s's %s network\n" "${node_type}" "${interface_type}" >> ${summary_file}
            result_file=${result_dir}
            if [ ${node_type} == "compute" ]; then
                result_file="${result_file}/${nodes[${i}]}"
            fi
            result_file="${result_file}/latency"
            printf ",frame size,%s\n" "$(awk '/rtt/ {print $2}' ${result_file}_${frame_sizes}${result_suffix} | tr '/' ',' )" >> ${summary_file}
            for frame_size in "${frame_sizes[@]}"; do
                printf ",%s,%s\n" "${frame_size}" "$(awk '/rtt/ {print $4}' ${result_file}_${frame_size}${result_suffix} | tr '/' ',' )" >> ${summary_file}
            done

            printf "latency distribution\n" >> ${summary_file}
            printf ",frame size" >> ${summary_file}
            for (( j = 1; j < "20" ; j+=1 )); do
                printf ",%s" "$(echo "scale=3;${j}/100" | bc | awk '{printf "%.3f", $0}')" >> ${summary_file}
            done
            printf "\n" >> ${summary_file}
            for frame_size in "${frame_sizes[@]}"; do
                printf ",%s" "${frame_size}" >> ${summary_file}
                for (( j = 1; j < "20" ; j+=1 )); do
                    printf ",%s" "$(grep -c "time=$(echo "scale=2;${j}/100" | bc | awk '{printf "%.2f", $0}')" ${result_file}_${frame_size}${result_suffix})" >> ${summary_file}
                done
                printf "\n" >> ${summary_file}
            done
            printf "\n" >> ${summary_file}
        done
    done

    get_interface_info
}

echo "Starting linux interface benchmark test. ($(date))"

# find the nodes to test
host=${HOSTNAME}
if [ "${host}" == "controller-1" ]; then
    remote="controller-0"
else
    remote="controller-1"
fi

# at least another controller needs to be reachable
ping -c1 ${remote} > /dev/null 2>&1
if [ $? -eq 0 ]; then
    controllers=(${host} ${remote})
    nodes+=("${controllers[@]}")
else
    echo "Stopping test as ${remote} is not reachable"
    exit 1
fi

# check if infrastructure interface is provisioned
ping -c1 "${remote}-infra" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Infrastructure network is provisioned"
    interfaces+=("infra")
fi

# check if there are any compute nodes
for i in $(seq 0 $[${max_compute_node} - 1]); do
    ping -c1 compute-${i} > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        computes+=("compute-${i}")
        if [ ${#computes[@]} -ge "2" ]; then
            nodes+=("${computes[@]}")
            break
        fi
    fi
done

setup
throughput_tcp_test
throughput_udp_test
throughput_parallel_test
latency_test
get_remote_results
generate_summary
echo "Linux interface benchmark test finished. ($(date))"

