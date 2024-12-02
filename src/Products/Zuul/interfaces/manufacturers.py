##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import Interface
from Products.Zuul.interfaces import IInfo, IFacade

class IManufacturers(Interface):
    """
    Marker interface for Manufacturers.
    """

class IManufacturersFacade(IFacade):

    def addNewProduct(params=None):
        """
        Add new product for the current context
        """

    def editProduct(params=None):
        """
        edit a product instance
        """

    def removeProduct(products):
        """
        remove product(s) from a manufacturer
        """

    def getProductsByManufacturer(uid):
        """
        The all the products for a manufacturer
        """

    def getProductData(uid):
        """
        return all extra data for a product id
        """
        
    def addManufacturer(params):
        """
        add new manufacturer
        """
        
    def editManufacturer(params):
        """
        edit a manufacturer
        """

    def moveProduct(moveFrom, moveTarget, ids):
        """
        move a product to a different manufacturer
        """

    def deleteManufacturer(uid, params):
        """
        delete selected entry
        """
        
    def getManufacturerList(self):
        """
        return menu list with custom formatted data
        """

class IManufacturersInfo(IInfo):
    """
    Info object adapter for manufacturers
    """

