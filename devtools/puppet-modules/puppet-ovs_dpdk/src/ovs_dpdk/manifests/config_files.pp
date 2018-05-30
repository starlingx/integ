class ovs_dpdk::config_files {
    file { '/etc/neutron/openvswitch_agent.ini':
        ensure => file,
        mode =>"0640",
        owner => 'root',
        group => 'neutron',
        source => 'puppet:///modules/ovs_dpdk/openvswitch_agent.ini',
    }

    file { '/usr/bin/update_openvswitch_agent_ini':
        ensure => file,
        mode =>"0755",
        owner => 'root',
        group => 'root',
        source => 'puppet:///modules/ovs_dpdk/update_openvswitch_agent_ini'
    }

    file { '/usr/bin/update_service_config':
        ensure => file,
        mode =>"0755",
        owner => 'root',
        group => 'root',
        source => 'puppet:///modules/ovs_dpdk/update_service_config'
    }

    file { '/usr/bin/ovs_dpdk_config_pre':
        ensure => file,
        mode =>"0755",
        owner => 'root',
        group => 'root',
        source => 'puppet:///modules/ovs_dpdk/ovs_dpdk_config_pre',
    }

    file { '/usr/bin/ovs_dpdk_config_post':
        ensure => file,
        mode =>"0755",
        owner => 'root',
        group => 'root',
        source => 'puppet:///modules/ovs_dpdk/ovs_dpdk_config_post',
    }
}
