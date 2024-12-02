##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Hardware

Hardware represents a hardware vendor's product.

$Id: Hardware.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from Products.ZenWidgets import messaging

from Products.ZenRelations.RelSchema import *

from MEProduct import MEProduct

def manage_addHardware(context, id, title = None, REQUEST = None):
    """make a Hardware"""
    d = Hardware(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main') 

addHardware = DTMLFile('dtml/addHardware',globals())

class Hardware(MEProduct):
    """Hardware object"""
    portal_type = meta_type = 'Hardware'

    tag = ""
    serialNumber = ""

    _properties = MEProduct._properties + (
        {'id':'tag', 'type':'string', 'mode':'w'},
        {'id':'serialNumber', 'type':'string', 'mode':'w'},
    )

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'setProduct')
    def setProduct(self, productName,  manufacturer="Unknown", 
                    newProductName="", REQUEST=None, **kwargs):
        """Set the product class of this software.
        """
        if not manufacturer: manufacturer = "Unknown"
        if newProductName: productName = newProductName
        prodobj = self.getDmdRoot("Manufacturers").createHardwareProduct(
                                        productName, manufacturer, **kwargs)
        self.setProductClass(prodobj)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Product Set',
                'Manufacturer %s and product %s set.' % (manufacturer,
                                                         productName)
            )
            return self.callZenScreen(REQUEST)


    def setProductKey(self, prodKey, manufacturer=None):
        """Set the product class of this software by its productKey.
        """
        if prodKey:
            # Store these so we can return the proper value from getProductKey
            self._prodKey = prodKey
            self._manufacturer = manufacturer

            if manufacturer is None:
                manufacturer = 'Unknown'

            manufs = self.getDmdRoot("Manufacturers")
            prodobj = manufs.createHardwareProduct(prodKey, manufacturer)
            self.setProductClass(prodobj)
        else:
            self.removeProductClass()



InitializeClass(Hardware)
