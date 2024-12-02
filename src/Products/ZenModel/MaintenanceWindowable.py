##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """MaintenanceWindowable

Management functions for devices and device classes on their
maintenance windows.

"""

import logging
log = logging.getLogger("zen.MaintenanceWindowable")

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from ZenossSecurity import *
from MaintenanceWindow import MaintenanceWindow
from Products.ZenUtils.Utils import prepId
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit

class MaintenanceWindowable:

    security = ClassSecurityInfo()

    security.declareProtected(ZEN_MAINTENANCE_WINDOW_VIEW,
        'getMaintenanceWindows')
    def getMaintenanceWindows(self):
        "Get the Maintenance Windows on this device"
        return self.maintenanceWindows.objectValuesAll()
    
    security.declareProtected(ZEN_MAINTENANCE_WINDOW_EDIT, 
        'manage_addMaintenanceWindow')
    def manage_addMaintenanceWindow(self, newId=None, REQUEST=None):
        "Add a Maintenance Window to this device"
        mw = None
        if newId:
            preppedId = prepId(newId)
            mw = MaintenanceWindow(preppedId)
            mw.name = newId
            self.maintenanceWindows._setObject(preppedId, mw)
            if hasattr(self, 'setLastChange'):
                # Only Device and DeviceClass have setLastChange for now.
                self.setLastChange()
        if REQUEST:
            if mw:
                messaging.IMessageSender(self).sendToBrowser(
                    'Window Added',
                    'Maintenance window "%s" has been created.' % mw.name
                )
                audit('UI.MaintenanceWindow.Add', mw)
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MAINTENANCE_WINDOW_EDIT, 
        'manage_deleteMaintenanceWindow')
    def manage_deleteMaintenanceWindow(self, maintenanceIds=(), REQUEST=None):
        "Delete a Maintenance Window to this device"
        if isinstance(maintenanceIds, basestring):
            maintenanceIds = [maintenanceIds]
        for id in maintenanceIds:
            mw = getattr(self.maintenanceWindows, id)
            if mw.started:
                if REQUEST:
                    msg = "Closing and removing maintenance window " \
                          "%s which affects %s" % (
                         mw.displayName(), self.id)
                    log.info(msg)
                    messaging.IMessageSender(self).sendToBrowser(
                        'Window Stopping',
                        msg,
                    )
                mw.end()

            if REQUEST:
                audit('UI.MaintenanceWindow.Delete', mw)
            self.maintenanceWindows._delObject(id)
        if hasattr(self, 'setLastChange'):
            # Only Device and DeviceClass have setLastChange for now.
            self.setLastChange()
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Windows Deleted',
                'Maintenance windows deleted: %s' % ', '.join(maintenanceIds)
            )
            return self.callZenScreen(REQUEST)


InitializeClass(MaintenanceWindowable)
