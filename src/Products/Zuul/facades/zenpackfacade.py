##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
from Products.Zuul.facades import ZuulFacade
from itertools import ifilter
from itertools import imap
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.interfaces.info import IInfo
from Products.Zuul.utils import unbrain
from Products.ZenModel.ZenPack import ZenPack

log = logging.getLogger('zen.ZenPackFacade')


class ZenPackFacade(ZuulFacade):

    def getDevelopmentZenPacks(self, uid='/zport/dmd/ZenPackManager'):
        catalog = IModelCatalogTool(self._dmd.unrestrictedTraverse(uid))
        brains = catalog.search(types=ZenPack)
        zenpacks = imap(unbrain, brains)
        return ifilter(lambda zp: not hasattr(zp, 'isDevelopment') or zp.isDevelopment(), zenpacks)

    def addToZenPack(self, topack, zenpack):
        self._dmd.ZenPackManager.addToZenPack(ids=[topack], pack=zenpack)

    def getZenPackInfos(self, zenpacks=None):
        zpInfo = {}
        for zenpack in self._dmd.ZenPackManager.packs():
            if zenpacks is None:
                zpInfo[zenpack.id] = IInfo(zenpack)
            elif zenpack.id in zenpacks:
                zpInfo[zenpack.id] = IInfo(zenpack)
        return zpInfo
