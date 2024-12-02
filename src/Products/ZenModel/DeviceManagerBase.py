##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from ZenossSecurity import ZEN_VIEW
from Products.ZenUtils.Utils import getDisplayType, getDisplayId
from Products.ZenMessaging.audit import audit

class DeviceManagerBase:
    """
    Default implementation of IDeviceManager interface.  This interface
    is implemented by classes that have a device relationship to allow them
    to manage their device relations.
    """

    def getDevices(self):
        return [ dev for dev in self.devices()
                    if self.checkRemotePerm(ZEN_VIEW, dev)]

    def deviceMoveTargets(self):
        """see IManageDevice"""
        raise NotImplementedError

    def removeDevices(self, deviceNames=None, deleteStatus=False, 
                      deleteHistory=False, deletePerf=False,REQUEST=None):
        """see IManageDevice"""
        from Products.ZenUtils.Utils import unused
        unused(deleteHistory, deletePerf, deleteStatus)
        if not deviceNames: return self()
        if isinstance(deviceNames, basestring): deviceNames = (deviceNames,)
        for devname in deviceNames:
            self.devices._delObject(devname)
            if REQUEST:
                if self.meta_type == 'PerformanceConf':
                    actionName = 'RemoveFromCollector'
                    objId = self.id
                else:
                    actionName = 'Remove'
                    objId = self.getPrimaryId()
                objType = getDisplayType(self)
                audit(['UI.Device', actionName], devname, data_={objType:objId})
        if REQUEST:
            return self()
