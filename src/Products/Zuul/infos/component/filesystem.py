##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.interfaces import IFileSystemInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo


class FileSystemInfo(ComponentInfo):
    implements(IFileSystemInfo)

    mount = ProxyProperty('mount')
    storageDevice = ProxyProperty('storageDevice')
    type = ProxyProperty('type')
    blockSize = ProxyProperty('blockSize')
    totalBlocks = ProxyProperty('totalBlocks')
    totalFiles = ProxyProperty('totalFiles')
    maxNameLength = ProxyProperty('maxNameLen')

    @property
    def totalBytes(self):
        return self._object.totalBytes()

    @property
    def usedBytes(self):
        return self._object.usedBytes()

    @property
    def availableBytes(self):
        return self._object.availBytes()

    @property
    def capacityBytes(self):
        return self._object.capacity()

    @property
    def availableFiles(self):
        return self._object.availFiles()

    @property
    def capacityFiles(self):
        return self._object.inodeCapacity()
