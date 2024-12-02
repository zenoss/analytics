##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import

import logging
import time

from multiprocessing import Process

from metrology.instruments import Gauge, HistogramExponentiallyDecaying

from zenoss.modelindex import constants
from zope.component import createObject

import Products.ZenCollector.configcache as CONFIGCACHE_MODULE

from Products.ZenModel.Device import Device
from Products.ZenModel.MibModule import MibModule
from Products.ZenModel.MibNode import MibNode
from Products.ZenModel.MibNotification import MibNotification
from Products.ZenModel.MibOrganizer import MibOrganizer
from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from .app import Application
from .app.args import get_subparser
from .cache import ConfigStatus, DeviceQuery
from .debug import Debug as DebugCommand
from .dispatcher import DeviceConfigTaskDispatcher, OidMapTaskDispatcher
from .handlers import (
    NewDeviceHandler,
    DeviceUpdateHandler,
    MissingConfigsHandler,
    RemoveConfigsHandler,
)
from .modelchange import InvalidationCause
from .utils import (
    DeviceProperties,
    getDeviceConfigServices,
    OidMapProperties,
    RelStorageInvalidationPoller,
)

_default_interval = 30.0


class Invalidator(object):
    description = (
        "Analyzes changes in ZODB to determine whether to update "
        "device configurations"
    )

    configs = (("modelchange.zcml", CONFIGCACHE_MODULE),)

    metric_prefix = "configcache.invalidations."

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers, "invalidator", description=Invalidator.description
        )
        subsubparsers = subp.add_subparsers(title="Invalidator Commands")

        subp_run = get_subparser(
            subsubparsers, "run", description="Run the invalidator service"
        )
        Application.add_all_arguments(subp_run)
        subp_run.add_argument(
            "--poll-interval",
            default=_default_interval,
            type=float,
            help="Invalidation polling interval (in seconds)",
        )
        subp_run.set_defaults(
            factory=Application.from_args,
            parser=subp_run,
            task=Invalidator,
        )

        subp_debug = get_subparser(
            subsubparsers,
            "debug",
            description=(
                "Signal the invalidator service to toggle debug logging"
            ),
        )
        Application.add_pidfile_arguments(subp_debug)
        subp_debug.set_defaults(factory=DebugCommand.from_args)

        Application.add_genconf_command(subsubparsers, (subp_run, subp_debug))

    def __init__(self, config, context):
        self.log = logging.getLogger("zen.configcache.invalidator")
        self.ctx = context

        deviceconfigClasses = getDeviceConfigServices()
        for cls in deviceconfigClasses:
            self.log.info(
                "using service class %s.%s", cls.__module__, cls.__name__
            )
        self.dispatchers = type(
            "Dispatchers",
            (object,),
            {
                "__slots__": ("device", "oidmap"),
                "device": DeviceConfigTaskDispatcher(deviceconfigClasses),
                "oidmap": OidMapTaskDispatcher(),
            },
        )()

        client = getRedisClient(url=getRedisUrl())
        self.stores = type(
            "Stores",
            (object,),
            {
                "__slots__": ("device", "oidmap"),
                "device": createObject("deviceconfigcache-store", client),
                "oidmap": createObject("oidmapcache-store", client),
            },
        )()

        self._process = _InvalidationProcessor(
            self.log, self.stores, self.dispatchers
        )

        self.interval = config["poll-interval"]

        # metrics
        self.ctx.metric_reporter.add_tags({"zenoss_daemon": "invalidator"})
        self._metrics = _Metrics(self.ctx.metric_reporter)

    def run(self):
        # Handle changes that occurred when Invalidator wasn't running.
        self._synchronize()

        poller = RelStorageInvalidationPoller(
            self.ctx.db.storage, self.ctx.dmd
        )
        self.log.info(
            "polling for device changes every %s seconds", self.interval
        )
        while not self.ctx.controller.shutdown:
            try:
                self.ctx.session.sync()
                invalidations = poller.poll()

                self._metrics.received.mark(len(invalidations))
                self._metrics.processed.update(len(invalidations))

                if not invalidations:
                    continue

                self._process_invalidations(invalidations)
            finally:
                self.ctx.metric_reporter.save()
                # Call cacheGC to aggressively trim the ZODB cache
                self.ctx.session.cacheGC()
                self.ctx.controller.wait(self.interval)

    def _synchronize(self):
        sync_deviceconfigs = Process(
            target=_synchronize_deviceconfig_cache,
            args=(self.log, self.ctx.dmd, self.dispatchers.device),
        )
        sync_oidmaps = Process(
            target=_synchronize_oidmap_cache,
            args=(self.log, self.ctx.dmd, self.dispatchers.oidmap),
        )
        sync_deviceconfigs.start()
        sync_oidmaps.start()
        sync_deviceconfigs.join()  # blocks until subprocess has exited
        sync_oidmaps.join()  # blocks until subprocess has exited

    def _process_invalidations(self, invalidations):
        self.log.debug("found %d relevant invalidations", len(invalidations))
        for inv in invalidations:
            try:
                self._process(inv.entity, inv.oid, inv.reason)
            except Exception:
                self.log.exception(
                    "failed to process invalidation  entity=%s",
                    inv.entity,
                )


class InvalidationGauge(Gauge):
    def __init__(self):
        self._value = 0

    @property
    def value(self):
        return self._value

    def mark(self, value):
        self._value = value


def _synchronize_oidmap_cache(log, dmd, dispatcher):
    store = createObject(
        "oidmapcache-store", getRedisClient(url=getRedisUrl())
    )
    if store:
        return
    now = time.time()
    store.set_pending(now)
    buildlimit = OidMapProperties().build_timeout
    dispatcher.dispatch(buildlimit, now)
    log.info("submitted build job for oidmap")


_deviceconfig_solr_fields = ("id", "collector", "uid")


def _synchronize_deviceconfig_cache(log, dmd, dispatcher):
    store = createObject(
        "deviceconfigcache-store", getRedisClient(url=getRedisUrl())
    )
    tool = IModelCatalogTool(dmd)
    catalog_results = tool.cursor_search(
        types=("Products.ZenModel.Device.Device",),
        limit=constants.DEFAULT_SEARCH_LIMIT,
        fields=_deviceconfig_solr_fields,
    ).results
    devices = {
        (brain.id, brain.collector): brain.uid
        for brain in catalog_results
        if brain.collector is not None
    }
    _removeDeleted(log, store, devices)
    _addNewOrChangedDevices(log, store, dispatcher, dmd, devices)


def _removeDeleted(log, store, devices):
    """
    Remove deleted devices from the cache.

    @param devices: devices that currently exist
    @type devices: Mapping[Sequence[str, str], str]
    """
    devices_not_found = tuple(
        key
        for key in store.search()
        if (key.device, key.monitor) not in devices
    )
    if devices_not_found:
        RemoveConfigsHandler(log, store)(devices_not_found)
    else:
        log.info("no dangling configurations found")


def _addNewOrChangedDevices(log, store, dispatcher, dmd, devices):
    # Add new devices to the config and metadata store.
    # Also look for device that have changed their device class.
    # Query the catalog for all devices
    new_devices = 0
    changed_devices = 0
    handle = NewDeviceHandler(log, store, dispatcher)
    for (deviceId, monitorId), uid in devices.iteritems():
        try:
            device = dmd.unrestrictedTraverse(uid)
        except Exception as ex:
            log.warning(
                "failed to get device  error-type=%s error=%s uid=%s",
                type(ex),
                ex,
                uid,
            )
            continue
        timeout = DeviceProperties(device).build_timeout
        keys_with_configs = tuple(
            store.search(DeviceQuery(monitor=monitorId, device=deviceId))
        )
        uid = device.getPrimaryId()
        if not keys_with_configs:
            handle(deviceId, monitorId, timeout)
            new_devices += 1
        else:
            current_uid = store.get_uid(deviceId)
            # A device with a changed device class will have a different uid.
            if current_uid != uid:
                handle(deviceId, monitorId, timeout, False)
                changed_devices += 1
    if new_devices == 0:
        log.info("no missing configurations found")
    if changed_devices == 0:
        log.info("no devices with a different device class found")


class _InvalidationProcessor(object):
    def __init__(self, log, stores, dispatchers):
        self.log = log
        self.stores = stores
        self._remove = RemoveConfigsHandler(log, stores.device)
        self._update = DeviceUpdateHandler(
            log, stores.device, dispatchers.device
        )
        self._missing = MissingConfigsHandler(
            log, stores.device, dispatchers.device
        )
        self._new = NewDeviceHandler(log, stores.device, dispatchers.device)

    def __call__(self, obj, oid, reason):
        if isinstance(obj, Device):
            self._handle_device(obj, oid, reason)
        elif isinstance(
            obj, (MibOrganizer, MibModule, MibNode, MibNotification)
        ):
            self._handle_mib(obj, oid, reason)

    def _handle_device(self, device, oid, reason):
        uid = device.getPrimaryId()
        self.log.info("handling device %s", uid)
        devprops = DeviceProperties(device)
        buildlimit = devprops.build_timeout
        minttl = devprops.minimum_ttl
        monitor = device.getPerformanceServerName()
        if monitor is None:
            self.log.warn(
                "ignoring invalidated device having undefined collector  "
                "device=%s reason=%s",
                device,
                reason,
            )
            return
        keys_with_config = tuple(
            self.stores.device.search(
                DeviceQuery(monitor=monitor, device=device.id)
            )
        )
        if not keys_with_config:
            self._new(device.id, monitor, buildlimit)
        elif reason is InvalidationCause.Updated:
            # Check for device class change
            stored_uid = self.stores.device.get_uid(device.id)
            if uid != stored_uid:
                self._new(device.id, monitor, buildlimit, False)
            else:
                self._update(keys_with_config, minttl)
                self._missing(device.id, monitor, keys_with_config, buildlimit)
        elif reason is InvalidationCause.Removed:
            self._remove(keys_with_config)
        else:
            self.log.warn(
                "ignored unexpected reason  "
                "reason=%s device=%s collector=%s device-oid=%r",
                reason,
                device,
                monitor,
                oid,
            )

    def _handle_mib(self, obj, oid, reason):
        status = self.stores.oidmap.get_status()
        if isinstance(status, (ConfigStatus.Expired, ConfigStatus.Pending)):
            # Status is already updated, so do nothing.
            return
        now = time.time()
        self.stores.oidmap.set_expired(now)
        self.log.info("expired oidmap")


class _Metrics(object):
    def __init__(self, reporter):
        self.received = InvalidationGauge()
        self.processed = HistogramExponentiallyDecaying()
        reporter.register("received", self.received)
        reporter.register("processed", self.processed)
