##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import zope.component
from Products.Five.browser import BrowserView
from Products.ZenModel.interfaces import IZenDocProvider

class EditZendoc(BrowserView):
    """
    Populates the component table that appears on the device status page.
    """
    def _getZendocProvider(self):
        return zope.component.queryAdapter( self.context,
                                            IZenDocProvider )

    def getZendoc(self):
        zendocProvider = self._getZendocProvider()
        return zendocProvider.getZendoc()

    def saveZendoc(self, zendocText):
        zendocProvider = self._getZendocProvider()
        zendocProvider.setZendoc( zendocText )
