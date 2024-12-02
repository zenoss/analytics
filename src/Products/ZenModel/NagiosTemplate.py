##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from AccessControl.class_init import InitializeClass

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM

import warnings
warnings.warn("NagiosTemplate is deprecated", DeprecationWarning)

class NagiosTemplate(ZenModelRM):

    description = ""

    _relations =  (
        ("deviceClass", ToOne(ToManyCont, "Products.ZenModel.DeviceClass", "nagiosTemplates")),
        ("nagiosCmds", ToManyCont(ToOne, "Products.ZenModel.NagiosCmd", "nagiosTemplate")),
    )    

InitializeClass(NagiosTemplate)
