##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import types
import DateTime

from twisted.web import xmlrpc

from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.Zuul import getFacade
from Products.ZenUtils.ZenTales import talesEval


class XmlRpcService(xmlrpc.XMLRPC):
    # serializable types
    PRIMITIVES = [
        types.IntType,
        types.StringType,
        types.BooleanType,
        types.DictType,
        types.FloatType,
        types.LongType,
        types.NoneType,
    ]

    def __init__(self, dmd):
        xmlrpc.XMLRPC.__init__(self)
        self.dmd = dmd
        self.zem = dmd.ZenEventManager

    def xmlrpc_sendEvent(self, data):
        """XMLRPC requests are processed asynchronously in a thread"""
        result = self.zem.sendEvent(data)
        if result is None:
            result = "none"
        return result

    def xmlrpc_sendEvents(self, data):
        return self.zem.sendEvents(data)

    def xmlrpc_getDevicePingIssues(self, *unused):
        zep = getFacade("zep")
        return zep.getDevicePingIssues()

    def xmlrpc_getDeviceWinInfo(self, *args):
        return self.dmd.Devices.Server.Windows.getDeviceWinInfo(*args)

    def xmlrpc_getWinServices(self, *args):
        return self.dmd.Devices.Server.Windows.getWinServices(*args)

    def xmlrpc_applyDataMap(
        self, devName, datamap, relname="", compname="", modname=""
    ):
        """Apply a datamap passed as a list of dicts through XML-RPC."""
        dev = self.dmd.findDevice(devName)
        adm = ApplyDataMap()
        adm.applyDataMap(
            dev, datamap, relname=relname, compname=compname, modname=modname
        )

    def xmlrpc_getConfigs(self, monitor, dstype):
        """Return the performance configurations for the monitor name and data
        source provided."""

        def toDict(device, ds, dps=[]):
            """marshall the fields from the datasource into a dictionary and
            ignore everything that is not a primitive"""

            vals = {}
            vals["dps"] = []
            vals["dptypes"] = []
            for key, val in ds.__dict__.items():
                if isinstance(val, XmlRpcService.PRIMITIVES):
                    if isinstance(val, basestring) and "$" in val:
                        val = talesEval("string:%s" % (val,), device)
                    vals[key] = val

            for dp in dps:
                vals["dps"].append(dp.id)
                vals["dptypes"].append(dp.rrdtype)

            # add zproperties
            for propertyId in device.propertyIds():
                value = device.getProperty(propertyId)

                # _millis can't be serialized because it is long, so
                # we skip it to avoid an XML-RPC serialization error
                if isinstance(value, DateTime.DateTime):
                    continue

                vals[propertyId] = value

            vals["device"] = device.id
            vals["manageIp"] = device.manageIp

            return vals

        result = []

        # get the performance conf (if it exists)
        conf = getattr(self.dmd.Monitors.Performance, monitor, None)
        if conf is None:
            return result

        # loop over devices that use the performance monitor
        for device in conf.devices():
            device = device.primaryAq()
            for template in device.getRRDTemplates():
                for ds in template.getRRDDataSources():
                    if ds.sourcetype == dstype:
                        result.append(toDict(device, ds, ds.datapoints()))

        return result

    def xmlrpc_writeRRD(self, devId, compType, compId, dpName, value):
        raise NotImplementedError(
            "ZenHub can no longer write RRD values. "
            "Please use the MetricFacade"
        )

    def xmlrpc_getPerformanceConfig(self, monitor):
        """Returns the performance configuration for the monitor provided,
        or {} if no collector with the name provided is located.
        """

        result = {}
        fields = [
            "configCycleInterval",
            "statusCycleInterval",
            "eventlogCycleInterval",
            "winCycleInterval",
        ]

        # get the performance conf (if it exists)
        conf = getattr(self.dmd.Monitors.Performance, monitor, None)
        if conf is None:
            return result

        for field in fields:
            result[field] = getattr(conf, field, None)

        return result
