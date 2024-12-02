##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""DeviceDumpLoadRouter

Import and export device definitions using the same process
provided by zenbatchload and zenbatchdump.
"""

import logging
log = logging.getLogger('zen.devicedumpload.router')

from Products import Zuul
from Products.Zuul.decorators import require
from Products.ZenUtils.Ext import DirectResponse, DirectRouter
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD


class DeviceDumpLoadRouter(DirectRouter):
    """
    Provide a file interface that device configuration can be compared
    against and then imported into Zenoss.  For large groups of devices,
    doing each device separately consumes too much resources.
    """

    def _getFacade(self):
        return Zuul.getFacade('devicedumpload', self.context)

    @require(ZEN_MANAGE_DMD)
    def exportDevices(self, deviceClass='/', options={}):
        """
        Create zenbatchload format file starting from the device class.
        """
        facade = self._getFacade()
        data, dumpedCount = facade.exportDevices(deviceClass=deviceClass,
                                    options=options)
        return DirectResponse.succeed(data=data, deviceCount=dumpedCount)

    @require(ZEN_MANAGE_DMD)
    def importDevices(self, data, options={}):
        """
        Create zenbatchload format file starting from the device class.
        """
        facade = self._getFacade()
        try:
            stats = facade.importDevices(data=data, options=options)
        except Exception:
            log.exception("Unable to import devices: %s", data)
            msg = "Failed -- see $ZENHOME/logs/event.log for details."
            return DirectResponse.fail(msg=msg)
        return DirectResponse.succeed(data=data, stats=stats)

    def listDevices(self, deviceClass='/'):
        """
        List of all devices based at the device class
        """
        facade = self._getFacade()
        data = facade.listDevices(deviceClass)
        count = len(data)
        return DirectResponse.succeed(data=data, count=count,
                                      success=True)

