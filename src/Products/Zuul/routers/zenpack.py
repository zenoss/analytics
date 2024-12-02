##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
Operations for ZenPacks.

Available at:  /zport/dmd/zenpack_router
"""

import logging
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products import Zuul
from Products.Zuul.decorators import require
from Products.ZenMessaging.audit import audit

log = logging.getLogger('zen.ZenPackRouter')
class ZenPackRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on ZenPacks
    """

    def _getFacade(self):
        return Zuul.getFacade('zenpack', self.context)

    def getEligiblePacks(self, **data):
        """
        Get a list of eligible ZenPacks to add to.

        @rtype:   DirectResponse
        @return:  B{Properties}:
             - packs: ([dictionary]) List of objects representing ZenPacks
             - totalCount: (integer) Total number of eligible ZenPacks
        """
        devZenPacks = self._getFacade().getDevelopmentZenPacks()
        packs = [{'name': zp.getId()} for zp in devZenPacks]
        packs = sorted(packs, key=lambda pack: pack['name'])
        return DirectResponse(packs=packs, totalCount=len(packs))

    @require('Manage DMD')
    def addToZenPack(self, topack, zenpack):
        """
        Add an object to a ZenPack.

        @type  topack: string
        @param topack: Unique ID of the object to add to ZenPack
        @type  zenpack: string
        @param zenpack: Unique ID of the ZenPack to add object to
        @rtype:   DirectResponse
        @return:  Success message
        """
        self._getFacade().addToZenPack(topack, zenpack)
        audit('UI.ZenPack.AddObject', zenpack, object=topack)
        return DirectResponse.succeed()

    def getZenPackMetaData(self, zenpacks=None):
        """
        Return the list of meta-data information about installed ZenPacks.

        @type  topack: list of strings
        @param topack: Unique IDs of the installed ZenPack
        @rtype:   DirectResponse
        @return:  Success message
        """
        infos = self._getFacade().getZenPackInfos(zenpacks)
        data = Zuul.marshal(infos)
        return DirectResponse.succeed(count=len(infos), data=data)

