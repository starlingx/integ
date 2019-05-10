#
# Copyright (c) 2019 StarlingX.
#
# SPDX-License-Identifier: Apache-2.0
#

# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#

""" Pci interrupt affinity agent daemon entry"""

import six
import json
import sys
import signal
import re
import eventlet
import threading
import time

from oslo_service import periodic_task
from oslo_service import service
import oslo_messaging

from config import CONF
from config import sysconfig
from nova_provider import novaClient
from affinity import pciIrqAffinity
from log import LOG

stay_on = True


class EventType:
    CREATE = 'compute.instance.create.end'
    DELETE = 'compute.instance.delete.end'
    RESIZE = 'compute.instance.resize.confirm.end'


def process_signal_handler(signum, frame):
    """Process Signal Handler"""
    global stay_on

    if signum in [signal.SIGTERM, signal.SIGINT, signal.SIGTSTP]:
        stay_on = False
    else:
        LOG.info("Ignoring signal" % signum)


def get_inst(instance_uuid, callback):
    # get instance info from nova
    inst = novaClient.get_instance(instance_uuid)
    if inst is not None:
        LOG.debug("inst:%s" % inst)
        callback(inst)


def query_instance_callback(inst):
    LOG.debug("query inst:%s" % inst)
    pciIrqAffinity.affine_pci_dev_instance(inst)


@periodic_task.periodic_task(spacing=CONF.pci_affine_interval)
def audit_affinity(self, context):
    pciIrqAffinity.audit_pci_irq_affinity()


def audit_work(srv, callback):
    srv.tg.add_dynamic_timer(callback, None, None, None)
    srv.tg.wait()


def audits_initialize():
    """Init periodic audit task for pci interrupt affinity check"""
    srv = service.Service()
    periodicTasks = periodic_task.PeriodicTasks(CONF)
    periodicTasks.add_periodic_task(audit_affinity)
    thread = threading.Thread(target=audit_work, args=(srv, periodicTasks.run_periodic_tasks))
    thread.start()
    return srv


class InstCreateNotificationEp(object):
    filter_rule = oslo_messaging.NotificationFilter(
        event_type=EventType.CREATE)

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        uuid = payload.get('instance_id', None)
        self.instance_create_handler(uuid)

    def instance_create_handler(self, instance_uuid):
        if instance_uuid is not None:
            LOG.info("instance_created: uuid=%s." % instance_uuid)
            eventlet.spawn(get_inst, instance_uuid, query_instance_callback).wait()


class InstResizeNotificationEp(object):
    filter_rule = oslo_messaging.NotificationFilter(
        event_type=EventType.RESIZE)

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        uuid = payload.get('instance_id', None)
        self.instance_resize_handler(uuid)

    def instance_resize_handler(self, instance_uuid):
        if instance_uuid is not None:
            LOG.info("instance_resized: uuid=%s." % instance_uuid)
            eventlet.spawn(get_inst, instance_uuid, query_instance_callback).wait()


class InstDelNotificationEp(object):
    filter_rule = oslo_messaging.NotificationFilter(
        event_type=EventType.DELETE)

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        uuid = payload.get('instance_id', None)
        self.instance_delete_handler(uuid)

    def instance_delete_handler(self, instance_uuid):
        if instance_uuid is not None:
            LOG.info("instance_deleted: uuid=%s." % instance_uuid)
            pciIrqAffinity.reset_irq_affinity(instance_uuid)


def get_rabbit_config():
    """Get rabbit config info from specific system config file."""

    rabbit_cfg = {}
    rabbit_session = 'amqp'
    options = ['host', 'port', 'user_id', 'password',
               'virt_host']
    try:
        for option in options:
            rabbit_cfg[option] = sysconfig.get(rabbit_session, option)

    except Exception as e:
        LOG.error("Could not read all required rabbitmq configuration! Err=%s" % e)
        rabbit_cfg = {}

    return rabbit_cfg


def rpc_work(srv):
    srv.start()
    srv.wait()


def start_rabbitmq_client():
    """Start Rabbitmq client to listen instance notifications from Nova"""
    cfg = get_rabbit_config()
    rabbit_url = "rabbit://%s:%s@%s:%s/%s" % (cfg['user_id'], cfg['password'],
                                              cfg['host'], cfg['port'], cfg['virt_host'])
    LOG.info(rabbit_url)

    target = oslo_messaging.Target(exchange="nova", topic="notifications", server="info",
                                   version="2.1", fanout=True)
    transport = oslo_messaging.get_notification_transport(CONF, url=rabbit_url)
    endpoints = [InstCreateNotificationEp(),
                 InstResizeNotificationEp(),
                 InstDelNotificationEp()]

    server = oslo_messaging.get_notification_listener(transport, [target],
                                                      endpoints, "threading")
    thread = threading.Thread(target=rpc_work, args=(server,))
    thread.start()
    LOG.info("Rabbitmq Client Started!")

    return server


def process_main():
    """Entry function for PCI Interrupt Affinity Agent"""

    LOG.info("Enter PCIInterruptAffinity Agent")

    try:
        signal.signal(signal.SIGTSTP, process_signal_handler)
        openstack_enabled = sysconfig.get('openstack', 'openstack_enabled')
        if openstack_enabled == 'true':
            novaClient.open_libvirt_connect()
            audit_srv = audits_initialize()
            rabbit_client = start_rabbitmq_client()

        while stay_on:
            time.sleep(1)

    except KeyboardInterrupt:
        LOG.info("keyboard Interrupt received.")
        pass

    except Exception as e:
        LOG.info("%s" % e)
        sys.exit(200)

    finally:
        LOG.error("proces_main finalized!!!")
        if openstack_enabled == 'true':
            novaClient.close_libvirt_connect()
            audit_srv.tg.stop()
            rabbit_client.stop()


if __name__ == '__main__':
    process_main()
