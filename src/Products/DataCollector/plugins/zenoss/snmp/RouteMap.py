##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import (
    GetTableMap,
    SnmpPlugin,
)


class RouteMap(SnmpPlugin):
    """Gathers and stores routing information."""

    maptype = "RouteMap"
    relname = "routes"
    compname = "os"
    modname = "Products.ZenModel.IpRouteEntry"
    deviceProperties = SnmpPlugin.deviceProperties + (
        "zRouteMapCollectOnlyLocal",
        "zRouteMapCollectOnlyIndirect",
        "zRouteMapMaxRoutes",
    )
    columns = {
        ".1": "id",
        ".2": "setInterfaceIndex",
        ".3": "metric1",
        # '.4': 'metric2',
        # '.5': 'metric3',
        # '.6': 'metric4',
        ".7": "setNextHopIp",
        ".8": "routetype",
        ".9": "routeproto",
        # '.10' : 'routeage',
        ".11": "routemask",
        # '.12': 'metric5',
    }

    snmpGetTableMaps = (
        GetTableMap("routetable", ".1.3.6.1.2.1.4.21.1", columns),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        routetable = tabledata.get("routetable")
        localOnly = getattr(device, "zRouteMapCollectOnlyLocal", False)
        indirectOnly = getattr(device, "zRouteMapCollectOnlyIndirect", False)
        maxRoutes = getattr(device, "zRouteMapMaxRoutes", 500)
        rm = self.relMap()
        for route in routetable.values():
            om = self.objectMap(route)
            if not hasattr(om, "id"):
                continue
            if not hasattr(om, "routemask"):
                continue
            om.routemask = self.maskToBits(om.routemask)

            # Workaround for existing but invalid netmasks
            if om.routemask is None:
                continue

            om.setTarget = om.id + "/" + str(om.routemask)
            om.id = om.id + "_" + str(om.routemask)
            if om.routemask == 32:
                continue
            routeproto = getattr(om, "routeproto", "other")
            om.routeproto = self.mapSnmpVal(routeproto, self.routeProtoMap)
            if localOnly and om.routeproto != "local":
                continue
            if not hasattr(om, "routetype"):
                continue
            om.routetype = self.mapSnmpVal(om.routetype, self.routeTypeMap)
            if indirectOnly and om.routetype != "indirect":
                continue
            if len(rm.maps) > maxRoutes:
                log.error("Maximum number of routes (%d) exceeded", maxRoutes)
                return
            rm.append(om)
        return rm

    def mapSnmpVal(self, value, map):
        if len(map) + 1 >= value:
            value = map[value - 1]
        return value

    routeTypeMap = ("other", "invalid", "direct", "indirect")
    routeProtoMap = (
        "other",
        "local",
        "netmgmt",
        "icmp",
        "egp",
        "ggp",
        "hello",
        "rip",
        "is-is",
        "es-is",
        "ciscoIgrp",
        "bbnSpfIgrp",
        "ospf",
        "bgp",
        "idpr",
        "ciscoEigrp",
    )
