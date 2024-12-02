##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, 2021 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.Manufacturers")
from pprint import pprint
from Products.ZenUtils.Ext import DirectResponse
from Products import Zuul
from Products.Zuul.decorators import require, serviceConnectionError
from Products.Zuul.routers import TreeRouter
from Products.Zuul.utils import sanitizeUrl
from Products.ZenMessaging.audit import audit


class ManufacturersRouter(TreeRouter):
    """
    Manufacturers and their products, and the instances of those products
    """

    def _getFacade(self):
        return Zuul.getFacade('manufacturers', self.context)

    @serviceConnectionError
    def addNewProduct(self, params=None):
        """
        Add new product for the current manufacturer context
        """
        facade = self._getFacade()
        facade.addNewProduct(params)
        audit('UI.Manufacturers.AddNewProduct', params['uid'], data_=params)
        return DirectResponse.succeed()
        
    @require('Manage DMD')
    def removeProducts(self, products):
        """
        remove product(s) from a manufacturer
        """
        facade = self._getFacade()
        facade.removeProducts(products)
        audit('UI.Manufacturers.RemoveProducts', products=products)
        return DirectResponse.succeed(
            "Scheduled job to remove %d product(s)." % len(products)
        )

    @serviceConnectionError        
    @require('Manage DMD')
    def editProduct(self, params=None):
        """
        Edit a product
        """
        facade = self._getFacade()
        oldData = facade.getProductData(params['uid'], params['oldname'])[0]
        scheduled = facade.editProduct(params)
        audit('UI.Manufacturers.editProduct', params['uid'],
              data_=params, oldData_=oldData)
        if scheduled:
            return DirectResponse.succeed(
                "Scheduled job to update product %s." %  params['oldname']
            )
        return DirectResponse.succeed()

    @serviceConnectionError
    def getProductsByManufacturer(self, uid, params={}):
        """
        Returns products for the current context
        """
        facade = self._getFacade()
        data = facade.getProductsByManufacturer(uid, params)

        return DirectResponse( data=Zuul.marshal(data) )

    @serviceConnectionError
    def getProductData(self, uid, prodname):
        """
        return all extra data for product id
        """
        facade = self._getFacade()
        data = facade.getProductData(uid, prodname)
        return DirectResponse(data=Zuul.marshal(data) )
        
    @serviceConnectionError
    def getProductInstances(self, uid, id, params={}):
        """
        return all instances of this product
        """
        facade = self._getFacade()
        data = facade.getProductInstances(uid, id, params)
        return DirectResponse(data=Zuul.marshal(data) )        
        
    @serviceConnectionError
    def getManufacturerData(self, uid):
        """
        return all extra data for manufacturer id
        """
        facade = self._getFacade()
        data = facade.getManufacturerData(uid)
        return DirectResponse(data=Zuul.marshal(data) ) 

    @serviceConnectionError
    def getManufacturers(self):
        """
        return all manufacturers
        """
        facade = self._getFacade()
        data = facade.getManufacturers()
        return DirectResponse(data=Zuul.marshal(data))
        
    @require('Manage DMD')
    def addManufacturer(self, id):
        """
        add  a manufacturer
        """
        facade = self._getFacade()
        facade.addManufacturer(id)
        audit('UI.Manufacturers.addManufacturers', Manufacturer=id)      
        return DirectResponse.succeed()      

    @require('Manage DMD')
    def editManufacturer(self, params):
        """
        edit a manufacturer
        """
        params['URL'] = sanitizeUrl(params.get('URL'))
        facade = self._getFacade()
        facade.editManufacturer(params)
        audit('UI.Manufacturers.EditManufacturer', Manufacturer=params['name'])        
        return DirectResponse.succeed()
        
    @require('Manage DMD')
    def deleteManufacturer(self, uid, params=None):
        """
        remove a manufacturer
        """
        facade = self._getFacade()
        facade.deleteNode(uid)
        audit('UI.Manufacturers.DeleteManufacturer', deletedManufacturer=uid)
        return DirectResponse.succeed()
        
    @require('Manage DMD')
    def moveProduct(self, moveFrom, moveTarget, ids):
        """
        move products to a different organizer
        """
        facade = self._getFacade()
        if isinstance(ids, basestring):
            ids = (ids,)
        facade.moveProduct(moveFrom, moveTarget, ids)
        audit('UI.Manufacturers.MoveProduct', movedProducts=ids, target=moveTarget)
        return DirectResponse.succeed(
            "Scheduled job to move %d product(s)." % len(ids)
        )
        
    def getManufacturerList(self):
        """
        return a usable tree
        """
        facade = self._getFacade()
        data = facade.getManufacturerList()
        return DirectResponse(data=Zuul.marshal(data))
