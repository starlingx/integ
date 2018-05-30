class ovs_dpdk::config {
    exec { 'setup_ovsdpdk_1_1':
        path => [ '/usr/bin', '/usr/sbin', '/bin', '/sbin' ],
        command => 'update_openvswitch_agent_ini',
    } ~>
    exec { 'setup_ovsdpdk_1_2':
        path => [ '/usr/bin', '/usr/sbin', '/bin', '/sbin' ],
        command => 'update_service_config',
    } ~>
    exec { 'setup_ovsdpdk_1_3':
        path => [ '/usr/bin', '/usr/sbin', '/bin', '/sbin' ],
        command => 'systemctl enable neutron-openvswitch-agent',
    } ~>
    exec { 'setup_ovsdpdk_1_4':
        path => [ '/usr/bin', '/usr/sbin', '/bin', '/sbin' ],
        command => 'systemctl enable neutron-l3-agent',
    }
}
