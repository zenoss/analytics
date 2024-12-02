##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ManufacturerRoot

The Manufacturer classification class.  default identifiers and screens,
live here.

$Id: ManufacturerRoot.py,v 1.10 2004/04/22 02:14:12 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

import logging
log = logging.getLogger('zen')

import transaction

from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from AccessControl import Permissions as permissions, ClassSecurityInfo
from Products.ZenModel.ZenossSecurity import *

from Products.ZenRelations.PrimaryPathObjectManager import \
    PrimaryPathBTreeFolder2

from ZenModelItem import ZenModelItem
from ZenPacker import ZenPacker
from Products.ZenUtils.Search import \
    makeCaseSensitiveKeywordIndex, makeCaseInsensitiveFieldIndex
from Products.ManagableIndex import FieldIndex

def manage_addManufacturerRoot(context, REQUEST=None):
    """make a Manufacturer class"""
    m = ManufacturerRoot()
    context._setObject(m.getId(), m)
    m = context._getOb(m.dmdRootName)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')


#addManufacturerRoot = DTMLFile('dtml/addManufacturerRoot',globals())

_MARKER = object()

class ManufacturerRoot(ZenModelItem, PrimaryPathBTreeFolder2, ZenPacker):
    """
    The root organizer for manufacturers.  May become a BtreeFolder2 at
    some point (to scale better).  Has interface to manage Manufacturers
    and the products that they create.
    """
    dmdRootName = "Manufacturers"
    meta_type = "ManufacturerRoot"
    sub_classes = ('Manufacturer',)
    default_catalog = "productSearch"

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'Manufacturer',
            'meta_type'      : 'Manufacturer',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'Manufacturer_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addManufacturer',
            'immediate_view' : 'viewManufacturers',
            'actions'        :
            (
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewManufacturers'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    def __init__(self, id=None):
        if not id: id = self.dmdRootName
        super(ManufacturerRoot, self).__init__(id)
        PrimaryPathBTreeFolder2.__init__(self, id)
        self.createCatalog()
        self.buildzProperties()


    def manage_addManufacturer(self, manufacturerName=None, REQUEST=None):
        """Add a manufacturer from UI code.
        """
        if manufacturerName:
            self.createManufacturer(manufacturerName)
        if REQUEST: return self.callZenScreen(REQUEST)
       

    def manage_deleteManufacturers(self, ids=None, REQUEST=None):
        """Delete a list of manufacturers from UI.
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids: self._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_ADD, 'createManufacturer')
    def createManufacturer(self, manufacturerName=None):
        """Return and create if nessesary manufacturerName.
        """
        from Products.ZenModel.Manufacturer import manage_addManufacturer
        if manufacturerName and not self.has_key(manufacturerName):
            logging.info("Creating Manufacturer %s", manufacturerName)
            manage_addManufacturer(self, manufacturerName)
        if manufacturerName:
            return self._getOb(manufacturerName)
        return None


    def getManufacturer(self, manufacturerName):
        """
        Return manufacturerName.  If it doesn't exist, create it.
        """
        manufacturerName = self.prepId(manufacturerName)
        if self.has_key(manufacturerName):
            return self._getOb(manufacturerName)
        else:
            for m in self.objectValues(spec="Manufacturer"):
                if m.matches(manufacturerName):
                    return m

        return self.createManufacturer(manufacturerName)
        
        
    def getManufacturerNames(self):
        """return list of all companies"""
        return self.objectIds(spec=("Manufacturer"))


    def getProductNames(self, mname, type=None):
        """return a list of all products this Manufacturer makes"""
        productFilter = dict(getManufacturerName=mname)
        if type == "OS":
            productFilter['meta_type'] = "SoftwareClass"
            productFilter['isOS'] = True
        elif type:
            productFilter['meta_type'] = type

        cat = getattr(self, self.default_catalog)
        return sorted(['']+[entry.id for entry in cat(productFilter)])


    def findProduct(self, query):
        """Find a product by is productKey.
        """
        cat = getattr(self, self.default_catalog)
        brains = cat({'productKeys': query})
        if not brains: return None
        try:
            return self.getObjByPath(brains[0].getPrimaryId)
        except KeyError:
            log.warn("bad path '%s' index '%s'", 
                        brains[0].getPrimaryId, self.default_catalog)

    
    security.declareProtected(ZEN_ADD, 'createHardwareProduct')
    def createHardwareProduct(self,prodName,manufacturer="Unknown",**kwargs):
        """Return and create if necessary a HardwareClass object.
        """
        from Products.ZenModel.HardwareClass import HardwareClass
        return self._getProduct(prodName, manufacturer, HardwareClass, **kwargs)


    security.declareProtected(ZEN_ADD, 'createSoftwareProduct')
    def createSoftwareProduct(self, prodName, manufacturer="Unknown", isOS=False, **kwargs):
        """Return and create if necessary a SoftwareClass object.
        """
        from Products.ZenModel.SoftwareClass import SoftwareClass
        prod = self._getProduct(prodName, manufacturer, SoftwareClass, isOS=isOS, **kwargs)
        return prod


    def _getProduct(self, prodName, manufacturer, factory, **kwargs):
        prod = self.findProduct(prodName)
        if prod:
            # Product already exists. Return it.
            return prod

        #delegate find/create to the manufacturer
        manufobj = self.getManufacturer(manufacturer)
        prod = manufobj._getProduct(prodName, factory, **kwargs)
        return prod


    def getProductsGen(self):
        """Return a generator that gets all products.
        """
        for manuf in self.values(spec="Manufacturer"):
            for prod in manuf.products.objectValuesGen():
                yield prod
        
    
    security.declareProtected(ZEN_MANAGE_DMD, 'reIndex')
    def reIndex(self):
        """Go through all devices in this tree and reindex them."""
        zcat = self._getOb(self.default_catalog)
        zcat.manage_catalogClear()
        for prod in self.getProductsGen():
            prod.index_object()


    security.declareProtected(ZEN_ADD, 'createCatalog')
    def createCatalog(self):
        """Create a catalog for EventClassRecord searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        # XXX update to use ManagableIndex
        manage_addZCatalog(self, self.default_catalog, self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        cat.addIndex('productKeys',
            makeCaseSensitiveKeywordIndex('productKeys'))
        cat.addIndex('meta_type',
            makeCaseInsensitiveFieldIndex('meta_type'))
        cat.addIndex('getManufacturerName',
            makeCaseInsensitiveFieldIndex('getManufacturerName'))
        cat.addIndex('isOS', FieldIndex('isOS'))
        zcat.addColumn('getPrimaryId')
        zcat.addColumn('id')


    def exportXml(self, ofile, ignorerels=[], root=False):
        """Return an xml based representation of a RelationshipManager
        <object id='/Devices/Servers/Windows/dhcp160.confmon.loc' 
            module='Products.Confmon.IpInterface' class='IpInterface'>
            <property id='name'>jim</property>
            <toone></toone>
            <tomany></tomany>
            <tomanycont></tomanycont>
        </object>
        """
        modname = self.__class__.__module__
        classname = self.__class__.__name__
        id = root and self.getPrimaryId() or self.id
        stag = "<object id='%s' module='%s' class='%s'>\n" % (
                    id , modname, classname)
        ofile.write(stag)
        for obj in self.objectValues():
            if getattr(aq_base(obj), 'exportXml', False):
                obj.exportXml(ofile, ignorerels)
        ofile.write("</object>\n")

    def primaryAq(self):
        """Return self with is acquisition path set to primary path"""
        # This is copied from PrimaryPathObjectManager - ZenModelItem one is bogus
        parent = getattr(self, "__primary_parent__", _MARKER)
        if parent is _MARKER: # dmd - no __primary_parent__
            base = self.getPhysicalRoot().zport
            return aq_base(self).__of__(base)
        if parent is None: # Deleted object
            raise KeyError(self.id)
        return aq_base(self).__of__(parent.primaryAq())
        
    def buildzProperties(self):
        if getattr(aq_base(self), "zDeviceClass", False): return
        self._setProperty("zDeviceClass", "")
        self._setProperty("zDeviceGroup", "")
        self._setProperty("zSystem", "")


InitializeClass(ManufacturerRoot)
