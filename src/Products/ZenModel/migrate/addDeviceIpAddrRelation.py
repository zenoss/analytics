##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = '''
Create relations between device and Ip Address under Network
'''

import Migrate
import logging
log = logging.getLogger("zen.migrate")
from zope.event import notify
from Products.ZenModel.IpAddress import IpAddress
from Products.Zuul.catalog.events import IndexingEvent
from Products.ZenUtils.IpUtil import ipAndMaskFromIpMask
from Products.Zuul.catalog.interfaces import IModelCatalogTool


class addDeviceIpAddrRelation(Migrate.Step):
    version = Migrate.Version(200, 2, 0)

    def cutover(self, dmd):

        log.info("Updating relationships on Ip Addresses")
        catalog = IModelCatalogTool(dmd.Networks)
        for ip in catalog.search(IpAddress):
            try:
                ip.getObject().buildRelations()
            #some objects can fail relations building process
            except (Exception,):
                continue

        log.info("Updating relationships on Devices")
        for dev in dmd.Devices.getSubDevices():
            try:
                dev.buildRelations()
                if dev.manageIp:
                    ipobj = dev.getNetworkRoot().findIp(dev.manageIp)
                    if ipobj:
                        dev.ipaddress.addRelation(ipobj)
                    else:
                        ipWithoutNetmask, netmask = ipAndMaskFromIpMask(dev.manageIp)
                        ipobj = dev.getNetworkRoot().createIp(ipWithoutNetmask, netmask)
                        dev.ipaddress.addRelation(ipobj)
                        notify(IndexingEvent(ipobj))
            #some objects can fail relations building process
            except (Exception,):
                continue

addDeviceIpAddrRelation()

