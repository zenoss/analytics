##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ClassifierEntry

Contains a list of keywords that are used to match an entry to a specific
device.  Once a match is found the Entry provides paths for DeviceClass,
Product, and Company.  This could potentially also provide Location, System
Group etc.

$Id: ClassifierEntry.py,v 1.6 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

from AccessControl import ClassSecurityInfo
from App.special_dtml import DTMLFile

from Products.ZCatalog.CatalogAwareness import CatalogAware
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager


def manage_addClassifierEntry(context, id=None, title=None, 
                    default_catalog = "", keywords = "", deviceClassPath = "", 
                    product = "", systemPath = "",
                    locationPath = "", manufacturer = "", 
                    productDescr = "", REQUEST = None):
    """make a device"""
    if not id:
        id = context.ZenClassifier.getNextClassifierEntryId()
    ce = ClassifierEntry(id, title=title,
                         default_catalog=default_catalog, 
                        keywords=keywords, deviceClassPath=deviceClassPath,
                        product=product, systemPath=systemPath, 
                        locationPath=locationPath, manufacturer=manufacturer,
                        productDescr = productDescr)
    context._setObject(id, ce)
    ce = context._getOb(id)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main')


addClassifierEntry = DTMLFile('dtml/addClassifierEntry',globals())

class ClassifierEntry(PropertyManager, CatalogAware, SimpleItem):
    """ClassifierEntry"""

    meta_type = 'ClassifierEntry'

    manage_options = (PropertyManager.manage_options + 
                    SimpleItem.manage_options
                    )

    _properties = (
                    {'id':'default_catalog', 'type':'selection', 
                        'select_variable':'getClassifierNames'},
                    {'id':'keywords', 'type':'text', 'mode':'rw'},
                    {'id':'deviceClassPath', 'type':'string', 'mode':'rw'},
                    {'id':'manufacturer', 'type':'string', 'mode':'rw'},
                    {'id':'product', 'type':'string', 'mode':'rw'},
                    {'id':'productDescr', 'type':'text', 'mode':'rw'},
                )


    security = ClassSecurityInfo()

    def __init__(self, id, title=None, 
                    default_catalog = "", keywords = "", deviceClassPath = "", 
                    product = "", systemPath = "",
                    locationPath = "", manufacturer = "",
                    snmpAgentPath = "", productDescr = ""):
        from Products.ZenUtils.Utils import unused
        unused(locationPath)
        self.id = id 
        self.title = title
        self.default_catalog = default_catalog
        self.keywords = keywords
        self.deviceClassPath = deviceClassPath
        self.product = product
        self.productDescr = productDescr
        self.systemPath = systemPath
        self.snmpAgentPath = snmpAgentPath
        self.manufacturer = manufacturer
 


    def manage_editProperties(self, REQUEST):
        """ Added indexing call -EAD
        Edit object properties via the web.
        The purpose of this method is to change all property values,
        even those not listed in REQUEST; otherwise checkboxes that
        get turned off will be ignored.  Use manage_changeProperties()
        instead for most situations.
        """
        for prop in self._propertyMap():
            name=prop['id']
            if 'w' in prop.get('mode', 'wd'):
                value=REQUEST.get(name, '')
                if name == 'default_catalog' and self.default_catalog != value:
                    self.unindex_object()
                self._updateProperty(name, value)
        self.index_object()
        if REQUEST:
            message="Saved changes."
            return self.manage_propertiesForm(self,REQUEST,
                                              manage_tabs_message=message)


    def _url(self):
        return "/".join(self.getPhysicalPath())


    def index_object(self):
        """Override so that we can find the catalog no matter where we are
        A common method to allow Findables to index themselves."""
        if hasattr(self.ZenClassifier, self.default_catalog):
            cat = getattr(self.ZenClassifier, self.default_catalog)
            cat.catalog_object(self, self._url())


    def unindex_object(self):
        """Override so that we can find the catalog no matter where we are
        A common method to allow Findables to unindex themselves."""
        if hasattr(self.ZenClassifier, self.default_catalog):
            cat = getattr(self.ZenClassifier, self.default_catalog)
            cat.uncatalog_object(self._url())

    
    def getClassifierNames(self):
        """allow select in property manager to find ZenClassifier"""
        return self.ZenClassifier.getClassifierNames()


    def getKeywords(self):
        """base class just returns attribute mobile subclass returns
        a concatination of all keyword values up its aquisition path"""
        return self.keywords


    def getDeviceClassPath(self):
        """base class just returns attribute mobile subclass returns
        builds its path based on its current aquisition path"""
        return self.deviceClassPath


    def getProduct(self):
        """return the product path for this classifier entry"""
        return self.product


    def getManufacturer(self):
        """return the manufacturer for this classifier entry"""
        return self.manufacturer
    
    def getProductDescr(self):
        """return the productDescr for this classifier entry"""
        return self.productDescr
