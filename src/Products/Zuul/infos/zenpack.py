##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.interfaces.zenpack import IZenPackInfo
from Products.Zuul.infos import ProxyProperty, InfoBase


class ZenPackInfo(InfoBase):
    implements(IZenPackInfo)

    version = ProxyProperty('version')
    author = ProxyProperty('author')
    organization = ProxyProperty('organization')
    url = ProxyProperty('url')
    license = ProxyProperty('license')
    compatZenossVers = ProxyProperty('compatZenossVers')

    @property
    def path(self):
        return self._object.path()

    @property
    def isDevelopment(self):
        return self._object.isDevelopment()

    @property
    def isEggPack(self):
        return self._object.isEggPack()

    @property
    def isBroken(self):
        return self._object.isBroken()

    @property
    def namespace(self):
        return self._object.id.rsplit('.', 1)[0].replace('ZenPacks.', '')

    @property
    def ZenPackName(self):
        return self._object.id.rsplit('.', 1)[1]

