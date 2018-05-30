# Class ovs_dpdk
#
#  ovs_dpdk configuration
#
# == parameters
#

class ovs_dpdk {
    class { ovs_dpdk::config_files: } ~>
    class { ovs_dpdk::config: }
}
