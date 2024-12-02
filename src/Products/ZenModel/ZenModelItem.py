##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ZenModelItem

$Id: ZenModelItem.py,v 1.3 2003/10/04 15:54:36 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo

from ZenModelBase import ZenModelBase

class ZenModelItem(ZenModelBase): 
    """
    Simple class that non RelationshipManager items inherit from to
    provide primary path functionality.
    """

    meta_type = 'ZenModelItem'

    security = ClassSecurityInfo()


    def __init__(self, id):
        self.id = id


    security.declareProtected('View', 'getPrimaryPath')
    def getPrimaryPath(self):
        return self.getPhysicalPath()


    security.declareProtected('View', 'getPrimaryUrlPath')
    def getPrimaryUrlPath(self, ignored=None):
        """get the physicalpath as a url"""
        return self.absolute_url_path()


    def primaryAq(self):
        """return this object with is acquisition path set to primary path"""
        return self


InitializeClass(ZenModelItem)
