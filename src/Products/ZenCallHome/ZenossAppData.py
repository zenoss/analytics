##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import time

from itertools import chain

from zenoss.protocols.services.zep import ZepConnectionError
from zope.interface import implementer
from zope.component import subscribers, getAdapters

from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.Zuul import getFacade
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from . import (
    IDeviceCpuCount,
    IDeviceLink,
    IDeviceResource,
    IDeviceType,
    IVirtualDeviceType,
    IZenossData,
)

log = logging.getLogger("zen.callhome")


@implementer(IZenossData)
class ZenossAppData(object):
    def callHomeData(self, dmd):
        self.dmd = dmd
        self._catalog = IModelCatalogTool(self.dmd)
        stats = (
            self.server_key,
            self.google_key,
            self.all_versions,
            self.event_classes,
            self.event_count,
            self.reports,
            self.templates,
            self.systems,
            self.groups,
            self.locations,
            self.total_collectors,
            self.zenpacks,
            self.user_count,
            self.product_count,
            self.product_name,
            self.components,
        )
        return chain.from_iterable(map(lambda fn: fn(), stats))

    def components(self):
        brains = self._catalog.search(
            types=(DeviceComponent,), facets_for_field=["meta_type"]
        )
        if brains.facets and brains.facets.get("meta_type"):
            facets = brains.facets["meta_type"]
            comps = facets.get_values()
            for comp, count in comps.iteritems():
                if count > 0:
                    yield "Components", "{}: {}".format(comp, count)
        yield "Components:", []

    def product_name(self):
        yield "Product", self.dmd.getProductName()

    def product_count(self):
        manufacturers = self.dmd.Manufacturers.objectValues(
            spec="Manufacturer"
        )
        prodCount = 0
        for m in manufacturers:
            prodCount += m.products.countObjects()

        yield "Product Count", prodCount

    def user_count(self):
        yield "User Count", len(self.dmd.ZenUsers.objectIds())

    def server_key(self):
        key = self.dmd.uuid or "NOT ACTIVATED"
        yield "Server Key", key

    def google_key(self):
        yield "Google Key", self.dmd.geomapapikey

    def zenpacks(self):
        for zenpack in self.dmd.ZenPackManager.packs():
            yield (
                "Zenpack",
                "{zenpack.id} {zenpack.version}".format(**locals()),
            )

    def all_versions(self):
        zenoss_version, cc_version = (
            self.dmd.About.getZenossVersion(),
            self.dmd.About.getControlCenterVersion(),
        )
        yield zenoss_version.name, zenoss_version.full()
        yield cc_version.name, cc_version.full()

    def event_classes(self):
        yield "Evt Mappings", self.dmd.Events.countInstances()

    def reports(self):
        yield "Reports", self.dmd.Reports.countReports()

    def templates(self):
        yield "Templates", len(self.dmd.searchRRDTemplates)

    def systems(self):
        yield "Systems", self.dmd.Systems.countChildren()

    def groups(self):
        yield "Groups", self.dmd.Groups.countChildren()

    def locations(self):
        yield "Locations", self.dmd.Locations.countChildren()

    def total_collectors(self):
        results = self.dmd.Monitors.getPerformanceMonitorNames()
        yield "Collectors", len(results)

    def event_count(self):
        zep = getFacade("zep", self.dmd)
        try:
            yield (
                "Event Count",
                zep.countEventsSince(time.time() - 24 * 60 * 60),
            )
        except ZepConnectionError:
            yield "Event Count: last 24hr", "Not Available"


VM_MACS = {
    "00:0C:29": "VMware Guest",
    "00:50:56": "VMware Guest",
    "00:16:3e": "Xen Guest",
}


@implementer(IVirtualDeviceType)
class MacAddressVirtualDeviceType(object):
    def __init__(self, device):
        self._device = device
        self._vmType = None

    def vmType(self):
        if self._vmType is None:
            for mac in self._device.getMacAddresses():
                if mac and mac[:8] in VM_MACS.keys():
                    self._vmType = VM_MACS[mac[:8]]
        return self._vmType


@implementer(IDeviceType)
class DeviceType(object):
    def __init__(self, device):
        self._device = device
        self._isVM = None
        self._vmType = None

    def isVM(self):
        if self._isVM is None:
            self._isVM = False
            for deviceType in subscribers((self._device,), IVirtualDeviceType):
                vmType = deviceType.vmType()
                if vmType is not None:
                    self._vmType = vmType
                    self._isVm = True
                    break
        return self._isVM

    def type(self):
        dType = "Physical"
        if self._isVM is None:
            self.isVM()
        if self._vmType:
            dType = self._vmType
        return dType


@implementer(IDeviceResource)
class DeviceTypeCounter(object):
    def __init__(self, device):
        self._device = device

    def processDevice(self, stats):
        suffix, isVm = self._get_type()
        log.debug("Device %s is type %s", self._device, suffix)
        devTypes = [suffix]
        if isVm:
            devTypes.append("Virtual")
        for type in devTypes:
            key = "Devices - %s" % type
            stats[key] = stats.get(key, 0) + 1

    def _get_type(self):
        dev = IDeviceType(self._device)
        return dev.type(), dev.isVM()


@implementer(IDeviceResource)
class DeviceClassProductionStateCount(object):
    def __init__(self, device):
        self._device = device

    def processDevice(self, stats):
        key = "%s: %s" % (
            self._device.getDeviceClassPath(),
            self._device.getProductionStateString(),
        )
        stats.setdefault(key, 0)
        stats[key] += 1


@implementer(IDeviceCpuCount)
class DeviceCpuCounter(object):
    def __init__(self, device):
        self._device = device

    def cpuCount(self):
        dev = IDeviceType(self._device)
        if not dev.isVM():
            return len(self._device.hw.cpus())
        return 0


@implementer(IZenossData)
class ZenossResourceData(object):
    def __init__(self):
        self._dmd = None
        self._catalog = None

    def callHomeData(self, dmd):
        self._dmd = dmd
        self._catalog = IModelCatalogTool(self._dmd)
        stats = self._process_devices()
        for key, value in stats.items():
            yield key, value

    def _process_devices(self):
        stats = {
            "Device Count": 0,
            "Decommissioned Devices": 0,
            "CPU Cores": 0,
        }
        LINKED_DEVICES = "Linked Devices"
        if LINKED_DEVICES not in stats:
            stats[LINKED_DEVICES] = 0
        for device in self._dmd.Devices.getSubDevicesGen_recursive():
            stats["Device Count"] += 1
            if device.getProductionState() < 0:
                stats["Decommissioned Devices"] += 1
            cpuCount = IDeviceCpuCount(device).cpuCount()
            log.debug("Devices %s has %s cpu cores", device, cpuCount)
            stats["CPU Cores"] += cpuCount
            for adapter in subscribers([device], IDeviceResource):
                adapter.processDevice(stats)
            found_linked = False
            for name, adapter in getAdapters((device,), IDeviceLink):
                if (
                    adapter.linkedDevice()
                    and adapter.linkedDevice().device().getProductionState()
                    > 0
                ):
                    key = "%s - %s" % (LINKED_DEVICES, name)
                    if key not in stats:
                        stats[key] = 0
                    stats[key] += 1
                    if not found_linked:
                        stats[LINKED_DEVICES] += 1
                        found_linked = True
        return stats
