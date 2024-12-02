##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM


import warnings
warnings.warn("NagiosCmd is deprecated", DeprecationWarning)
class NagiosCmd(ZenModelRM):

    _relations =  (
        ("nagiosTemplate", ToOne(ToManyCont, "Products.ZenModel.NagiosTemplate", "nagiosCmds")),
    )    

    security = ClassSecurityInfo()

InitializeClass(NagiosCmd)
