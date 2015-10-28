##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""HardwareClass

HardwareClass represents a software vendor's product.

$Id: HardwareClass.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.ZenRelations.RelSchema import (
    RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne)

from ProductClass import ProductClass

def manage_addHardwareClass(context, id, title = None, REQUEST = None):
    """make a HardwareClass"""
    d = HardwareClass(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addHardwareClass = DTMLFile('dtml/addHardwareClass',globals())

class HardwareClass(ProductClass):
    """HardwareClass object"""
    portal_type = meta_type = 'HardwareClass'

InitializeClass(HardwareClass)
