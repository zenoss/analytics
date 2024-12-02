##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from Products.ZenModel.ZenModelRM import ZenModelRM


class RRDToolItem(ZenModelRM):
    """base class for RRDTool persistent classes"""

    security = ClassSecurityInfo()

    def getName(self):
        """Return the name of this item (take off the type from the id)."""
        return self.id


InitializeClass(RRDToolItem)
