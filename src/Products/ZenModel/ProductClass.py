##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ProductClass

The product classification class.  default identifiers, screens,
and data collectors live here.

$Id: ProductClass.py,v 1.10 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from zope.interface import implements

from Products.ZenModel.interfaces import IIndexed
from Products.ZenModel.ZenossSecurity import *
from Products.ZenWidgets import messaging

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable

from Products.ZenRelations.RelSchema import *

from Products.Zuul.catalog.interfaces import IModelCatalogTool

class ProductClass(ZenModelRM, ZenPackable):
    implements(IIndexed)
    meta_type = "ProductClass"

    #itclass = ""
    name = ""
    productKeys = []
    isOS = False

    default_catalog = "productSearch"

    _properties = (
        #{'id':'itclass', 'type':'string', 'mode':'w'},
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'productKeys', 'type':'lines', 'mode':'w'},
        {'id':'partNumber', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
        {'id':'isOS', 'type':'boolean', 'mode':'w'},
    )

    _relations = ZenPackable._relations + (
        ("manufacturer", ToOne(ToManyCont,"Products.ZenModel.Manufacturer","products")),
    )

    factory_type_information = ( 
        { 
            'id'             : 'ProductClass',
            'meta_type'      : 'ProductClass',
            'description'    : """Class to manage product information""",
            'icon'           : 'ProductClass.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addProductClass',
            'immediate_view' : 'viewProductClassOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewProductClassOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editProductClass'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'config'
                , 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEditNew'
                , 'permissions'   : ("Manage DMD",)
                },
            )
          },
        )
    
    security = ClassSecurityInfo()

    def __init__(self, id, title="", prodName=None,
                 productKey=None, partNumber="",description=""):
        ZenModelRM.__init__(self, id, title)
        # XXX per a comment in #406 from Erik, we may want to get rid
        # of prodName and only use productKey, to avoid redundancy
        if productKey:
            self.productKeys = [productKey]
        elif prodName:
            self.productKeys = [prodName]
        else:
            # When adding manually through the gui or via device discovery if
            # the device model is not already in the system, both prodName
            # and productKey will be None
            self.productKeys = [id]
        self.name = prodName if prodName is not None else id
        self.partNumber = partNumber
        self.description = description

    def type(self):
        """Return the type name of this product (Hardware, Software).
        """
        return self.meta_type[:-5]

    def _find_instances_in_catalog(self, count=False):
        model_catalog = IModelCatalogTool(self.dmd)
        query = { "productClassId": self.idx_uid() }
        if count:
            return model_catalog.search(query=query, limit=0)
        else:
            return model_catalog.search(query=query)

    def instances(self):
        for brain in self._find_instances_in_catalog():
            if brain:
                ob = brain.getObject()
                yield aq_base(ob).__of__(self)

    def count(self):
        """ Return the number of existing instances for this class. """
        search_results = self._find_instances_in_catalog(count=True)
        return search_results.total

    def getProductKey(self):
        """Return the first product key of the device.
        """
        if len(self.productKeys) > 0:
            return self.productKeys[0]
        return ""

    def getManufacturerName(self):
        if not self.manufacturer():
            return ''
        return self.manufacturer().getId()

    security.declareProtected('Manage DMD', 'manage_editProductClass')
    def manage_editProductClass(self, name="", productKeys=(), isOS=False,
                               partNumber="", description="", REQUEST=None):
        """
        Edit a ProductClass from a web page.
        """
        redirect = self.rename(name)
        productKeys = [ l.strip() for l in productKeys.split('\n') ]
        if productKeys != self.productKeys:
            self.unindex_object()
            self.productKeys = productKeys
        self.partNumber = partNumber
        self.description = description
        self.isOS = isOS
        self.name = name
        self.index_object()
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            messaging.IMessageSender(self).sendToBrowser(
                'Product Class Saved',
                SaveMessage()
            )
            return self.callZenScreen(REQUEST, redirect)


InitializeClass(ProductClass)
