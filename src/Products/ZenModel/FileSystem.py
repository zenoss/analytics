##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""FileSystem

FileSystem is a file system on a server

$Id: FileSystem.py,v 1.12 2004/04/06 22:33:23 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from math import isnan

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenUtils.Utils import convToUnits
from Products.ZenRelations.RelSchema import *

from OSComponent import OSComponent
from Products.ZenUtils.Utils import prepId
from Products.ZenWidgets import messaging

from Products.ZenModel.ZenossSecurity import *

def manage_addFileSystem(context, newId, userCreated, REQUEST=None):
    """make a filesystem"""
    fsid = prepId(newId)
    fs = FileSystem(fsid)
    context._setObject(fsid, fs)
    fs = context._getOb(fsid)
    fs.mount = newId
    if userCreated: fs.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')

addFileSystem = DTMLFile('dtml/addFileSystem',globals())

class FileSystem(OSComponent):
    """
    FileSystem object
    """

    portal_type = meta_type = 'FileSystem'

    manage_editFileSystemForm = DTMLFile('dtml/manageEditFileSystem',globals())

    mount = ""
    storageDevice = ""
    type = ""
    blockSize = 0
    totalBlocks = 0
    totalFiles = 0
    capacity = 0
    inodeCapacity = 0
    maxNameLen = 0

    security = ClassSecurityInfo()

    _properties = OSComponent._properties + (
        {'id':'mount', 'type':'string', 'mode':''},
        {'id':'storageDevice', 'type':'string', 'mode':''},
        {'id':'type', 'type':'string', 'mode':''},
        {'id':'blockSize', 'type':'int', 'mode':''},
        {'id':'totalBlocks', 'type':'long', 'mode':''},
        {'id':'totalFiles', 'type':'long', 'mode':''},
        {'id':'maxNameLen', 'type':'int', 'mode':''},
        )
    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont, "Products.ZenModel.OperatingSystem", "filesystems")),
        )


    factory_type_information = ( 
        { 
            'id'             : 'FileSystem',
            'meta_type'      : 'FileSystem',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'FileSystem_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addFileSystem',
            'immediate_view' : 'viewFileSystem',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewFileSystem'
                , 'permissions'   : (ZEN_VIEW,)
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },                
            )
          },
        )


    def getTotalBlocks(self):

        offset = getattr(self.primaryAq(), 'zFileSystemSizeOffset', 1.0)
        return int(self.totalBlocks) * offset

    
    def totalBytes(self):
        """
        Return the total bytes of a filesytem
        """
        return int(self.blockSize) * self.getTotalBlocks()


    def totalBytesString(self):
        """
        Return the number of total bytes in human readable from ie 10MB
        """
        return convToUnits(self.totalBytes())


    def usedBytes(self):
        """
        Return the number of used bytes on a filesytem.
        """
        blocks = self.usedBlocks()
        if blocks is not None:
            return self.blockSize * blocks
        return None


    def usedBytesString(self):
        """
        Return the number of used bytes in human readable form ie 10MB
        """
        __pychecker__='no-constCond'
        ub = self.usedBytes()
        return ub is None and "unknown" or convToUnits(ub)


    def availBytes(self):
        """
        Return the number of availible bytes for this filesystem
        """
        blocks = self.availBlocks()
        if blocks is not None:
            return self.blockSize * blocks
        return None


    def availBytesString(self):
        """
        Return the number of availible bytes in human readable form ie 10MB
        """
        __pychecker__='no-constCond'
        ab = self.availBytes()
        return ab is None and "unknown" or convToUnits(ab)


    def availFiles(self):
        """
        Not implemented returns 0
        """
        return 0


    def capacity(self):
        """
        Return the percentage capacity of a filesystems using its rrd file.
        Calculate using available blocks instead used blocks to account for
        reserved blocks.
        """
        __pychecker__='no-returnvalues'
        totalBlocks = self.getTotalBlocks()
        availBlocks = self.availBlocks()
        if totalBlocks and availBlocks is not None:
            return round(100.0 * (totalBlocks - availBlocks) / totalBlocks)
        return 'unknown'


    def inodeCapacity(self):
        """
        Not implemented returns 0
        """
        return 0


    def usedBlocks(self, default = None):
        """
        Return the number of used blocks stored in the filesystem's rrd file
        """

        dskPercent = self.cacheRRDValue("dskPercent", default)
        if dskPercent is not None and dskPercent != "Unknown" and not isnan(dskPercent):
            return self.getTotalBlocks() * dskPercent / 100.0

        blocks = self.cacheRRDValue('usedBlocks', default)
        if blocks is not None and not isnan(blocks):
            return long(blocks)
        elif self.blockSize:
            # no usedBlocks datapoint, so this is probably a Windows device
            # using perfmon for data collection and therefore we'll look for
            # the freeMegabytes datapoint
            freeMB = self.cacheRRDValue('FreeMegabytes', default)
            if freeMB is not None and not isnan(freeMB):
                usedBytes = self.totalBytes() - long(freeMB) * 1024 * 1024
                return usedBytes / self.blockSize
        return None


    def availBlocks(self, default = None):
        """
        Return the number of available blocks stored in the filesystem's rrd file
        """
        blocks = self.cacheRRDValue('availBlocks', default)
        if blocks is not None and not isnan(blocks):
            return long(blocks)
        usedBlocks = self.usedBlocks()
        if usedBlocks is None:
            return None
        return self.getTotalBlocks() - usedBlocks


    def usedBlocksString(self):
        """
        Return the number of used blocks in human readable form ie 10MB
        """
        __pychecker__='no-constCond'
        ub = self.usedBlocks()
        return ub is None and "unknown" or convToUnits(ub)

    def viewName(self): 
        """
        Return the mount point name of a filesystem '/boot'
        """
        return self.mount
    name = viewName


    security.declareProtected(ZEN_MANAGE_DEVICE, 'manage_editFileSystem')
    def manage_editFileSystem(self, monitor=False,
                mount=None, storageDevice=None, 
                type=None, blockSize=None, 
                totalFiles=None, maxNameLen=None, 
                snmpindex=None, REQUEST=None):
        """
        Edit a Service from a web page.
        """
        if mount:
            self.mount = mount
            self.storageDevice = storageDevice
            self.type = type
            self.blockSize = blockSize
            self.totalFiles = totalFiles
            self.maxNameLen = maxNameLen
            self.snmpindex = snmpindex

        self.monitor = monitor
        self.index_object()

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Filesystem Updated',
                'Filesystem %s was edited.' % self.id
            )
            return self.callZenScreen(REQUEST)


InitializeClass(FileSystem)
