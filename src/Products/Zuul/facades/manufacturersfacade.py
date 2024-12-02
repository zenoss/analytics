##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013 - 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import inspect
import re
import sre_constants
import logging
log = logging.getLogger('zen.ManufacturersFacade')
from pprint import pprint
from zope.interface import implements
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IManufacturersFacade, IManufacturersInfo, IInfo
from Products.ZenEvents import EventClass
from Acquisition import aq_parent
from Products.ZenModel.Manufacturer import manage_addManufacturer
from Products.Jobber.jobs import FacadeMethodJob

class ManufacturersFacade(TreeFacade):
    implements(IManufacturersFacade)

    def addNewProduct(self, params=None):
        """
        Add new product for the current context
        @params.uid = the manufacturer this product will be added to
        @params.prodname = the name of the product
        @params.partno = the part number if there is one
        @params.type  = software/hardware/os
        @params.prodkeys = the key(s) for the product
        @params.desc = a description of the product
        """
        manufacturer = self._getObject(params['uid'])
        prodName = params['prodname']
        prod = manufacturer.products._getOb(prodName, None)
        if not prod:
            isOS = False
            if (params['type'] == "Hardware"):
                from Products.ZenModel.HardwareClass import HardwareClass
                prod = self._processProduct(manufacturer, prodName, HardwareClass)
            else:
                from Products.ZenModel.SoftwareClass import SoftwareClass
                if (params['type'] == "Operating System"):
                    isOS = True
                prod = self._processProduct(manufacturer, prodName, SoftwareClass, isOS=isOS)
            if prod:
                prod.partNumber  = params['partno']
                prod.isOS        = isOS
                prod.productKeys = [ l.strip() for l in (params['prodkeys']).split('\n') ]
                prod.description = params['description']

    def _processProduct(self, manufacturer, prodName, factory, **kwargs):
        """
        process the adding of a product
        """
        prodid = manufacturer.prepId(prodName)
        prod = factory(prodid, **kwargs)
        for k, v in kwargs.iteritems():
            if not hasattr(prod, k):
                setattr(prod, k, v)
        manufacturer.products._setObject(prodid, prod)
        prod = manufacturer.products._getOb(prodid)
        return prod

    def _editProduct(self, params, instances_uids=None):
        manufacturer = self._getObject(params['uid'])
        prodName = params['oldname']
        prod = manufacturer.products._getOb(prodName, None)
        isOS = True if params['type'] == "Operating System" else False
        productKeys = [l.strip() for l in (params['prodkeys']).split('\n')]
        if productKeys != prod.productKeys:
            prod.unindex_object()
            prod.productKeys = productKeys
        prod.partNumber = params['partno']
        prod.description = params['description']
        prod.isOS = isOS
        prod.name = params['prodname']
        prod.rename(params['prodname'])
        prod.index_object()
        if instances_uids:
            # change product_class for every instance
            for uid in instances_uids:
                obj = self._dmd.Devices.getObjByPath(uid)
                obj.setProductClass(prod)
            log.debug(
                "Updated %d instances for %s product class.",
                len(instances_uids), params['prodname']
            )

    def editProduct(self, params=None):
        """
        edit a product
        """
        manufacturer = self._getObject(params['uid'])
        prodName = params['oldname']
        prod = manufacturer.products._getOb(prodName, None)
        if not prod:
            return False
        scheduled = False
        result = prod._find_instances_in_catalog()
        if params['oldname'] != params['prodname'] and result.total > 0:
            instances_uids = [i.uid for i in result.results]
            self._dmd.JobManager.addJob(
                FacadeMethodJob,
                description=(
                    "Updating product class for %s instances"
                ) % params['prodname'],
                kwargs={
                    "facadefqdn": FacadeMethodJob.getClassPathOf(self),
                    "method": "_editProduct",
                    "params": params,
                    "instances_uids": instances_uids,
                }
            )
            scheduled = True
        else:
            self._editProduct(params)
        return scheduled

    def _removeProducts(self, products):
        for entry in products:
            manufacturer = self._getObject(entry['context'])
            prod = manufacturer.products._getOb(entry['id'])
            result = prod._find_instances_in_catalog()
            instances_uids = [i.uid for i in result.results]
            manufacturer.products._delObject(entry['id'])
            for uid in instances_uids:
                obj = self._dmd.Devices.getObjByPath(uid)
                obj.setProductClass(productClass=None)

    def removeProducts(self, products):
        """
        remove product(s) from a manufacturer
        @products['context']
        @products['id']
        """
        self._dmd.JobManager.addJob(
            FacadeMethodJob,
            description=(
                "Removing %d products and clearing product class "
                "for their instances"
            ) % len(products),
            kwargs={
                "facadefqdn": FacadeMethodJob.getClassPathOf(self),
                "method": "_removeProducts",
                "products": products,
            },
        )

    def getProductsByManufacturer(self, uid, params={}):
        """
        The all the products for this manufacturer
        """
        obj = self._getObject(uid)
        products = [IInfo(i) for i in obj.products.objectValuesAll()]
        prods = []
        filt = params.get('prod_id', "")
        for entry in products:
            if filt.lower() in entry.id.lower():
                prod = obj.products._getOb(entry.id, None)
                prods.append({
                                'id': entry.id,
                                'uid':entry.uid,
                                'key':prod.productKeys,
                                'type':prod.type(),
                                'count':prod.count()
                            })
        return prods

    def getProductData(self, uid, prodname):
        """
        return product data for a given product
        """
        manufacturer = self._getObject(uid)
        prod = manufacturer.products._getOb(prodname, None)
        info = [{
            'name'      : prod.name,
            'partno'    : prod.partNumber,
            'prodKeys'  : prod.productKeys,
            'type'      : prod.type(),
            'desc'      : prod.description,
            'os'        : prod.isOS
        }]
        return info

    def getProductInstances(self, uid, id, params={}):
        """
        return product instances
        """
        manufacturer = self._getObject(uid)
        prod = manufacturer.products._getOb(id, None)
        instlist = prod.instances()
        instances = []
        filt = params.get('device_id', "")
        for instance in instlist:
            if filt.lower() in instance.getDeviceName().lower():
                instances.append({
                       'id': id,
                        'device':instance.getDeviceName(),
                        'uid':instance.getDeviceUrl()
                })
        return instances

    def getManufacturerData(self, uid):
        """
        return all extra data for manufacturer id
        """
        obj = self._getObject(uid)
        info = [{
            'id'            :obj.id,
            'url'           :obj.url,
            'phone'         :obj.supportNumber,
            'address1'      :obj.address1,
            'address2'      :obj.address2,
            'city'          :obj.city,
            'state'         :obj.state,
            'zip'           :obj.zip,
            'country'       :obj.country,
            'regexes'       :obj.regexes
        }]
        return info

    def getManufacturers(self):
        """
        return all manufacturers
        """
        id = "zport/dmd/Manufacturers"
        obj = self._getObject(id)
        data = []
        for sub in obj.getChildNodes():
            if (sub.id != "productSearch"):
                data.append({
                    'id':".zport.dmd.Manufacturers."+sub.id
                })
        return data

    def addManufacturer(self, id):
        """
        add a new manufacturer
        """
        context = self._dmd.Manufacturers
        manage_addManufacturer(context, id)

    def editManufacturer(self, params):
        """
        edit the information for a given manufacturer
        """
        # 'oldname' is not in params when this method is called while adding a
        # new manufacturer. In such case, get an object with params['name']
        # instead of params['oldname'].
        manufacturer = self._getObject(
                "/zport/dmd/Manufacturers/" +
                params.get('oldname', params['name']))

        # Create the pair of products and these products instances which
        # should be updated.
        product_instance_pairs = []
        products = manufacturer.products()
        for product in products:
            result = product._find_instances_in_catalog()
            instances_uids = [i.uid for i in result.results]

            product_instances = [
                (self._dmd.Devices.getObjByPath(uid), product)
                for uid in instances_uids
            ]
            product_instance_pairs.extend(product_instances)

        manufacturer.url = params['URL']
        manufacturer.supportNumber = params['phone']
        manufacturer.address1 = params['address1']
        manufacturer.address2 = params['address2']
        manufacturer.city = params['city']
        manufacturer.state = params['state']
        manufacturer.zip = params['zip']
        manufacturer.country = params['country']
        manufacturer.regexes = params['regexes']
        if manufacturer.id != params['name']:
            manufacturer.rename(params['name'])

        # Set updated instances to the product
        for obj, prod in product_instance_pairs:
            obj.setProductClass(prod)

    def _moveProduct(self, moveFrom, moveTarget, ids):
        target = self._getObject(moveTarget)
        origin = self._getObject(moveFrom)
        for id in ids:
            prod = origin.products._getOb(id)
            result = prod._find_instances_in_catalog()
            prod._operation = 1
            instances_uids = [i.uid for i in result.results]
            origin.products._delObject(id)
            target.products._setObject(id, prod)
            prod = target.products._getOb(id)
            for uid in instances_uids:
                obj = self._dmd.Devices.getObjByPath(uid)
                obj.setProductClass(prod)
                log.debug(
                    "Updated %d instances for %s product class.", len(instances_uids), moveTarget
                )

    def moveProduct(self, moveFrom, moveTarget, ids):
        """
        move a product to a different organizer
        """
        self._dmd.JobManager.addJob(
            FacadeMethodJob,
            description=(
                "Moving %d products and updating product "
                "class for their instances"
            ) % len(ids),
            kwargs={
                "facadefqdn": FacadeMethodJob.getClassPathOf(self),
                "method": "_moveProduct",
                "moveFrom": moveFrom,
                "moveTarget": moveTarget,
                "ids": ids,
            },
        )

    def getManufacturerList(self):
        """
        build a custom tree that works for the left panel
        """
        id = "zport/dmd/Manufacturers"
        obj = self._getObject(id)
        data = []
        for sub in obj.getChildNodes():
            if (sub.id != "productSearch"):
                data.append({
                    'id':".zport.dmd.Manufacturers."+sub.id,
                    'path':"Manufacturers/"+sub.id,
                    'text':{'text':sub.id,'description':sub.supportNumber, 'url': sub.url},
                    'uid':"/zport/dmd/Manufacturers/"+sub.id
                })
        return data


def _get_classfqdn(obj):
    name = obj.__class__.__name__
    module = inspect.getmodule(obj)
    return "%s.%s" % (module.__name__, name)
