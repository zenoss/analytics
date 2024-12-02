##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenRelations.RelSchema import *


class ZenPackable(object):
    "mix-in allows an object to be referenced by a ZenPack"

    meta_type = "ZenPackable"

    _relations = (
        ("pack", ToOne(ToMany, "Products.ZenModel.ZenPack", "packables")),
    )
