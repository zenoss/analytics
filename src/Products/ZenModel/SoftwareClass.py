##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""SoftwareClass

SoftwareClass represents a software vendor's product.

$Id: SoftwareClass.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass

from Products.ZenRelations.RelSchema import *

from ProductClass import ProductClass

def manage_addSoftwareClass(context, id, title = None, REQUEST = None):
    """make a SoftwareClass"""
    d = SoftwareClass(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main') 

addSoftwareClass = DTMLFile('dtml/addSoftwareClass',globals())

class SoftwareClass(ProductClass):
    """SoftwareClass object"""
    portal_type = meta_type = 'SoftwareClass'

    build=""
    version=""
    
    _properties = ProductClass._properties + (
        {'id':'version', 'type':'string', 'mode':'w'},
        {'id':'build', 'type':'string', 'mode':'w'},
        )

    def __init__(self, id, title="", prodName=None,
                 productKey=None, partNumber="",description="", isOS=False):
        super(SoftwareClass, self).__init__(id, title, prodName, productKey, partNumber, description)
        self.isOS = isOS

    def type(self):
        """Return the type name of this product (Hardware, Software).
        """
        if self.isOS:
            return "Operating System"
        else:
            return self.meta_type[:-5]
    

InitializeClass(SoftwareClass)


class OSSoftwareClass(SoftwareClass):

    """OSSoftwareClass object"""

    portal_type = meta_type = 'OSSoftwareClass'

    def __init__(self, id, title="", prodName=None,
                 productKey=None, partNumber="",description="", isOS=True):
        super(OSSoftwareClass, self).__init__(id, title, prodName, productKey, partNumber, description, isOS)


InitializeClass(OSSoftwareClass)
