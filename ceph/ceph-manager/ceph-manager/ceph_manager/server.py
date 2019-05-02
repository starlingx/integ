# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2016-2018 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# https://chrigl.de/posts/2014/08/27/oslo-messaging-example.html
# http://docs.openstack.org/developer/oslo.messaging/server.html

import sys

# noinspection PyUnresolvedReferences
import eventlet
# noinspection PyUnresolvedReferences
import oslo_messaging as messaging
# noinspection PyUnresolvedReferences
from fm_api import fm_api
# noinspection PyUnresolvedReferences
from oslo_config import cfg
# noinspection PyUnresolvedReferences
from oslo_log import log as logging
# noinspection PyUnresolvedReferences
from oslo_service import service
# noinspection PyUnresolvedReferences
from oslo_service.periodic_task import PeriodicTasks

# noinspection PyUnresolvedReferences
from cephclient import wrapper

from ceph_manager.monitor import Monitor
from ceph_manager import constants

from ceph_manager.i18n import _LI
from ceph_manager.i18n import _LW
from retrying import retry

eventlet.monkey_patch(all=True)

CONF = cfg.CONF
CONF.register_opts([
    cfg.StrOpt('sysinv_api_bind_ip',
               default='0.0.0.0',
               help='IP for the Ceph Manager server to bind to')])
CONF.logging_default_format_string = (
    '%(asctime)s.%(msecs)03d %(process)d '
    '%(levelname)s %(name)s [-] %(message)s')
logging.register_options(CONF)
logging.setup(CONF, __name__)
LOG = logging.getLogger(__name__)
CONF.rpc_backend = 'rabbit'


class RpcEndpoint(PeriodicTasks):

    def __init__(self, service=None):
        self.service = service

    def get_primary_tier_size(self, _):
        """Get the ceph size for the primary tier.

        returns: an int for the size (in GB) of the tier
        """

        tiers_size = self.service.monitor.tiers_size
        primary_tier_size = tiers_size.get(
            self.service.monitor.primary_tier_name, 0)
        LOG.debug(_LI("Ceph cluster primary tier size: %s GB") %
                  str(primary_tier_size))
        return primary_tier_size

    def get_tiers_size(self, _):
        """Get the ceph cluster tier sizes.

        returns: a dict of sizes (in GB) by tier name
        """

        tiers_size = self.service.monitor.tiers_size
        LOG.debug(_LI("Ceph cluster tiers (size in GB): %s") %
                  str(tiers_size))
        return tiers_size

    def is_cluster_up(self, _):
        """Report if the last health check was successful.

        This is an independent view of the cluster accessibility that can be
        used by the sysinv conductor to gate ceph API calls which would timeout
        and potentially block other operations.

        This view is only updated at the rate the monitor checks for a cluster
        uuid or a health check (CEPH_HEALTH_CHECK_INTERVAL)

        returns: boolean True if last health check was successful else False
        """
        return self.service.monitor.cluster_is_up


class SysinvConductorUpgradeApi(object):
    def __init__(self):
        self.sysinv_conductor = None
        super(SysinvConductorUpgradeApi, self).__init__()

    def get_software_upgrade_status(self):
        LOG.info(_LI("Getting software upgrade status from sysinv"))
        cctxt = self.sysinv_conductor.prepare(timeout=2)
        upgrade = cctxt.call({}, 'get_software_upgrade_status')
        LOG.info(_LI("Software upgrade status: %s") % str(upgrade))
        return upgrade

    @retry(wait_fixed=1000,
           retry_on_exception=lambda e:
               LOG.warn(_LW(
                   "Getting software upgrade status failed "
                   "with: %s. Retrying... ") % str(e)) or True)
    def retry_get_software_upgrade_status(self):
        return self.get_software_upgrade_status()


class Service(SysinvConductorUpgradeApi, service.Service):

    def __init__(self, conf):
        super(Service, self).__init__()
        self.conf = conf
        self.rpc_server = None
        self.sysinv_conductor = None
        self.ceph_api = None
        self.entity_instance_id = ''
        self.fm_api = fm_api.FaultAPIs()
        self.monitor = Monitor(self)
        self.config = None
        self.config_desired = None
        self.config_applied = None

    def start(self):
        super(Service, self).start()
        transport = messaging.get_transport(self.conf)
        self.sysinv_conductor = messaging.RPCClient(
            transport,
            messaging.Target(
                topic=constants.SYSINV_CONDUCTOR_TOPIC))

        self.ceph_api = wrapper.CephWrapper(
            endpoint='https://localhost:5001')

        # Get initial config from sysinv and send it to
        # services that need it before starting them
        self.rpc_server = messaging.get_rpc_server(
            transport,
            messaging.Target(topic=constants.CEPH_MANAGER_TOPIC,
                             server=self.conf.sysinv_api_bind_ip),
            [RpcEndpoint(self)],
            executor='eventlet')
        self.rpc_server.start()
        eventlet.spawn_n(self.monitor.run)

    def stop(self):
        try:
            self.rpc_server.stop()
            self.rpc_server.wait()
        except Exception:
            pass
        super(Service, self).stop()


def run_service():
    CONF(sys.argv[1:])
    logging.setup(CONF, "ceph-manager")
    launcher = service.launch(CONF, Service(CONF), workers=1)
    launcher.wait()


if __name__ == "__main__":
    run_service()
