##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import math

import transaction

from ipaddr import IPNetwork
from twisted.spread import pb
from ZODB.transact import transact

from Products.Jobber.exceptions import NoSuchJobException
from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenModel.Device import manage_createDevice
from Products.ZenModel.Exceptions import DeviceExistsError
from Products.ZenRelations.ZenPropertyManager import iszprop
from Products.ZenRelations.zPropertyCategory import getzPropertyCategory
from Products.ZenUtils.IpUtil import strip, ipunwrap, isip

from ..errors import translateError
from .ModelerService import ModelerService

DEFAULT_PING_THRESH = 168
log = logging.getLogger("zen.DiscoverService")


class JobPropertiesProxy(pb.Copyable, pb.RemoteCopy):
    def __init__(self, jobrecord):
        self.zProperties = {}
        for prop in jobrecord.__dict__:
            if iszprop(prop):
                self.zProperties[prop] = getattr(jobrecord, prop)


pb.setUnjellyableForClass(JobPropertiesProxy, JobPropertiesProxy)


class IpNetProxy(pb.Copyable, pb.RemoteCopy):
    "A class that will represent a ZenModel/IpNetwork in zendisc"

    id = ""
    _children = None
    netmask = None

    def __init__(self, ipnet):
        self.id = ipnet.id
        self._children = map(IpNetProxy, ipnet.children())
        self.netmask = ipnet.netmask
        for (
            prop
        ) in "zAutoDiscover zDefaultNetworkTree zPingFailThresh".split():
            if hasattr(ipnet, prop):
                setattr(self, prop, getattr(ipnet, prop))

    def children(self):
        return self._children

    def fullIpList(self):
        "copied from IpNetwork"
        log.debug(
            "fullIpList: using ipaddr IPNetwork on %s (%s)",
            self.id,
            ipunwrap(self.id),
        )
        net = IPNetwork(ipunwrap(self.id))
        if self.netmask == net.max_prefixlen:
            return [ipunwrap(self.id)]
        ipnumb = long(int(net))
        maxip = math.pow(2, net.max_prefixlen - self.netmask)
        start = int(ipnumb + 1)
        end = int(ipnumb + maxip - 1)
        return map(strip, range(start, end))

    def getNetworkName(self):
        return "%s/%d" % (ipunwrap(self.id), self.netmask)


pb.setUnjellyableForClass(IpNetProxy, IpNetProxy)


class DiscoverService(ModelerService):
    @translateError
    def remote_getNetworks(self, net, includeSubNets):
        """
        Get network objects to scan networks should be in
        CIDR form 1.1.1.0/24
        """
        netObj = self.dmd.Networks.getNetworkRoot().findNet(net)
        if not netObj:
            return None
        nets = [netObj]
        if includeSubNets:
            nets += netObj.getSubNetworks()
        return map(IpNetProxy, nets)

    @translateError
    def remote_pingStatus(self, net, goodips, badips, resetPtr, addInactive):
        "Create objects based on ping results"
        net = self.dmd.Networks.getNetworkRoot().findNet(net.id, net.netmask)
        pingthresh = getattr(net, "zPingFailThresh", DEFAULT_PING_THRESH)
        ips = []
        for ip in goodips:
            ipobj = net.createIp(ip, net.netmask)
            if resetPtr:
                ipobj.setPtrName()
            if not ipobj.device():
                ips.append(ip)
            self.sendIpStatusEvent(ipobj, sev=0)
        for ip in badips:
            ipobj = self.dmd.Networks.getNetworkRoot().findIp(ip)
            if not ipobj and addInactive:
                ipobj = net.createIp(ip, net.netmask)
            if ipobj:
                if resetPtr:
                    ipobj.setPtrName()
                elif ipobj.getStatus(Status_Ping) > pingthresh:
                    net.ipaddresses.removeRelation(ipobj)
                if ipobj:
                    self.sendIpStatusEvent(ipobj)
        transaction.commit()
        return ips

    def sendIpStatusEvent(self, ipobj, sev=2):
        """Send an ip down event.  These are used to cleanup unused ips."""
        ip = ipobj.id
        dev = ipobj.device()
        if sev == 0:
            msg = "ip %s is up" % ip
        else:
            msg = "ip %s is down" % ip
        if dev:
            devname = dev.id
            comp = ipobj.interface().id
        else:
            devname = comp = ip
        self.sendEvent(
            {
                "device": devname,
                "ipAddress": ip,
                "eventKey": ip,
                "component": comp,
                "eventClass": Status_Ping,
                "summary": msg,
                "severity": sev,
                "agent": "Discover",
            }
        )

    @translateError
    def remote_createDevice(self, ip, force=False, **kw):
        """
        Create a device.

        @param ip: The manageIp of the device
        @param kw: The args to manage_createDevice.
        """
        # During discovery, if the device
        # shares an id with another device
        # with a different ip, set the device
        # title to the supplied id and replace
        # the id with the ip
        deviceName = kw["deviceName"]
        if deviceName:
            device = self.dmd.Devices.findDeviceByIdExact(deviceName)
            if device and all(
                (
                    device.manageIp,
                    not device._temp_device,
                    ip != device.manageIp,
                )
            ):
                kw["deviceName"] = ip
                kw["title"] = deviceName

        dev, deviceIsNew = _update_device(self.dmd, ip, force, **kw)
        if dev is not None:
            return self.createDeviceProxy(dev), deviceIsNew
        else:
            return None, False

    @translateError
    def remote_getJobProperties(self, jobid):
        try:
            jobrecord = self.dmd.JobManager.getJob(jobid)
            if jobrecord:
                return JobPropertiesProxy(jobrecord)
        except NoSuchJobException:
            pass

    @translateError
    def remote_succeedDiscovery(self, id):
        dev = self.dmd.Devices.findDeviceByIdOrIp(id)
        if dev:
            dev._temp_device = False
        transaction.commit()
        return True

    @translateError
    def remote_followNextHopIps(self, device):
        """
        Return the ips that the device's indirect routes point to
        which aren't currently connected to devices.
        """
        dev = self.getPerformanceMonitor().findDevice(device)
        ips = []
        for r in dev.os.routes():
            ipobj = r.nexthop()
            if ipobj:
                ips.append(ipobj.id)
        return ips

    @translateError
    def remote_getSubNetworks(self):
        "Fetch proxies for all the networks"
        return map(
            IpNetProxy, self.dmd.Networks.getNetworkRoot().getSubNetworks()
        )

    @translateError
    def remote_getDeviceClassSnmpConfig(self, devicePath, category="SNMP"):
        "Get the snmp configuration defaults for scanning a device"
        devRoot = self.dmd.Devices.createOrganizer(devicePath)
        snmpConfig = {}
        for name, value in devRoot.zenPropertyItems():
            if getzPropertyCategory(name) == category:
                snmpConfig[name] = value
        return snmpConfig

    @translateError
    def remote_moveDevice(self, dev, path):
        self.dmd.Devices.moveDevices(path, [dev])
        transaction.commit()

    @translateError
    def remote_getDefaultNetworks(self):
        monitor = self.dmd.Monitors.Performance._getOb(self.instance)
        return list(monitor.discoveryNetworks)

    @translateError
    def remote_removeInterfaces(self, net):
        """
        Remove IPs for particular network
        already assigned to interfaces (device components)

        @param net - network to discover
        @return:  a list of IPs without addresses assigned for interfaces
        @rtype: list
        """

        full_ip_list = net.fullIpList()

        for d in self.dmd.Devices.getSubDevicesGen():
            for interface in d.os.interfaces():
                for addr in interface.ipaddresses():
                    ip = addr.getIp()
                    if net.netmask == addr.netmask and ip in full_ip_list:
                        full_ip_list.remove(ip)

        return full_ip_list


@transact
def _update_device(dmd, ip, force, **kw):
    """
    return device object (either new or existing), and flag indicating
    whether device was newly created, or just updated
    """
    from Products.ZenModel.Device import getNetworkRoot

    try:
        monitor = kw.get("performanceMonitor", "localhost")
        netroot = getNetworkRoot(dmd, monitor)
        netobj = netroot.getNet(ip)
        netmask = _get_netmask(netroot, netobj)
        autoDiscover = getattr(netobj, "zAutoDiscover", True)
        # If we're not supposed to discover this IP, return None
        if not force and not autoDiscover:
            return (None, False)
        kw["manageIp"] = ipunwrap(ip)
        dev = manage_createDevice(dmd, **kw)
        netroot.createIp(ip, netmask)
        return dev, True
    except DeviceExistsError as e:
        # Update device with latest info from zendisc
        # (if necessary)
        if not e.dev.getManageIp():
            e.dev.setManageIp(kw["manageIp"])

        # only overwrite title if it has not been set
        if not e.dev.title or isip(e.dev.title):
            if not isip(kw.get("deviceName")):
                e.dev.setTitle(kw["deviceName"])

        # copy kw->updateAttributes, to keep kw intact in case
        # we need to retry transaction
        updateAttributes = {}
        for k, v in kw.items():
            if k not in (
                "manageIp",
                "deviceName",
                "devicePath",
                "discoverProto",
                "performanceMonitor",
                "productionState",
            ):
                updateAttributes[k] = v
        # use updateDevice so we don't clobber existing device
        # properties.
        e.dev.updateDevice(**updateAttributes)
        return e.dev, False
    except Exception as ex:
        log.exception(
            "IP address %s (kw = %s) encountered error",
            ipunwrap(ip),
            kw,
        )
        raise pb.CopyableFailure(ex)


def _get_netmask(netroot, netobj):
    if netobj is not None:
        return netobj.netmask
    defaultNetmasks = getattr(netroot, "zDefaultNetworkTree", [])
    if defaultNetmasks:
        return defaultNetmasks[0]
    return 24
