##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
Operations for Settings.

Available at:  /zport/dmd/settings_router
"""
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul.decorators import require
from Products import Zuul
from Products.ZenMessaging.audit import audit


class SettingsRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on settings
    """

    def _getUISettings(self):
        return self.context.zport.dmd.UserInterfaceSettings

    def getUserInterfaceSettings(self):
        """
        Retrieves the collection of User interface settings
        """
        settings = self._getUISettings()
        return DirectResponse.succeed(data=Zuul.marshal(settings.getSettingsData()))

    @require('Manage DMD')
    def setUserInterfaceSettings(self, **kwargs):
        """
        Accepts key value pair of user interface settings.
        """
        settings = self._getUISettings()
        oldValues = {}
        newValues = {}
        for key, value in kwargs.iteritems():
            oldValues[key] = str(getattr(settings, key, None))
            newValues[key] = str(value)
            setattr(settings, key, value)
        audit('UI.InterfaceSettings.Edit', data_=newValues, oldData_=oldValues)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def setDmdSettings(self, **kwargs):
        """
        Accepts key value pair of dmd settings
        """
        dmd = self.context.zport.dmd
        for key, value in kwargs.iteritems():
            if hasattr(dmd, key):
                setattr(dmd, key, value)

        return DirectResponse.succeed()