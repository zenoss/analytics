##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Manufacturer

Manufacturer is a base class that represents a vendor of Products.

$Id: Manufacturer.py,v 1.11 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

import re

from Globals import DTMLFile, InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Products.ZenModel.ZenossSecurity import (
    MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE,
    TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION,
    UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD,
    ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE,
    ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE,
    ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS,
    ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE,
    ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER,
    ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT,
    ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE,
    ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER,
    ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE,
    ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS,
    ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW)
from Products.ZenWidgets import messaging
from Products.ZenUtils.deprecated import deprecated

from Products.ZenRelations.RelSchema import (
    RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne)

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable


def manage_addManufacturer(context, id=None, REQUEST = None):
    """make a Manufacturer"""
    if id:
        d = Manufacturer(id)
        context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addManufacturer = DTMLFile('dtml/addManufacturer',globals())

class Manufacturer(ZenModelRM, ZenPackable):
    """Manufacturer object"""
    portal_type = meta_type = 'Manufacturer'

    url = ''
    supportNumber = ''
    address1 = ''
    address2 = ''
    city = ''
    state = ''
    zip = ''
    country = ''
    regexes = ()

    _properties = (
        {'id':'url', 'type':'string', 'mode':'w'},
        {'id':'supportNumber', 'type':'string', 'mode':'w'},
        {'id':'address1', 'type':'string', 'mode':'w'},
        {'id':'address2', 'type':'string', 'mode':'w'},
        {'id':'city', 'type':'string', 'mode':'w'},
        {'id':'state', 'type':'string', 'mode':'w'},
        {'id':'zip', 'type':'string', 'mode':'w'},
        {'id':'country', 'type':'string', 'mode':'w'},
        {'id':'regexes', 'type':'lines', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ("products", ToManyCont(ToOne,"Products.ZenModel.ProductClass","manufacturer")),
    )
 
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Manufacturer',
            'meta_type'      : 'Manufacturer',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'Manufacturer_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addManufacturer',
            'immediate_view' : 'viewManufacturerOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewManufacturerOverview'
                , 'permissions'   : (permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editManufacturer'
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


    def count(self):
        """Return the number of products for this manufacturer.
        """
        return self.products.countObjects()


    def manage_addHardware(self, prodName=None, REQUEST=None):
        """Add a hardware product from UI code.
        """
        if prodName:
            from Products.ZenModel.HardwareClass import HardwareClass
            self._getProduct(prodName, HardwareClass)
        if REQUEST: return self.callZenScreen(REQUEST)


    def manage_addSoftware(self, prodName=None, isOS=False, REQUEST=None):
        """Add a software product from UI code.
        """
        if prodName:
            from Products.ZenModel.SoftwareClass import SoftwareClass
            prod = self._getProduct(prodName, SoftwareClass, isOS=isOS)
        if REQUEST: return self.callZenScreen(REQUEST)

   
    def moveProducts(self, moveTarget=None, ids=None, REQUEST=None):
        """Move product to different manufacturer.
        """
        if not moveTarget or not ids: return self()
        target = self.getManufacturer(moveTarget)
        if isinstance(ids, basestring): ids = (ids,)
        for id in ids:
            obj = self.products._getOb(id)
            obj._operation = 1 # moving object state
            self.products._delObject(id)
            target.products._setObject(id, obj)
        if REQUEST: return self.callZenScreen(REQUEST)


    def _getProduct(self, prodName, factory, **kwargs):
        """Add a product to this manufacturer based on its factory type.
        """
        prod = self.products._getOb(prodName, None)
        if not prod:
            prodid = self.prepId(prodName)
            prod = factory(prodid, **kwargs)
            for k, v in kwargs.iteritems():
                if not hasattr(prod, k):
                    setattr(prod, k, v)
            self.products._setObject(prodid, prod)
            prod = self.products._getOb(prodid)
        return prod 


    def manage_deleteProducts(self, ids=None, REQUEST=None):
        """Delete a list of products from UI.
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids: self.products._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)

    @deprecated
    def getProductNames(self):
        """return a list of all products this Manufacturer makes"""
        prods = [""]
        prods.extend(map(lambda x: x.getId(),
                         self.products.objectValuesAll()))
        prods.sort()
        return prods


    def matches(self, name):
        """
        Returns true if this manufacturer name or any of the regexes defined
        match the provided string.
        
        @param name: Manufacturer name
        @type name: string
        @return: True if this manufacturer matches the given name
        @rtype: bool
        """
        if self.id == name:
            return True
        for regex in self.regexes:
            if re.search(regex, name):
                return True
        return False


    security.declareProtected('Manage DMD', 'manage_editManufacturer')
    def manage_editManufacturer(self, id='', title='', url='', supportNumber='',
                address1='', address2='', city='', state='', zip='',
                country='', regexes=[], REQUEST=None):
        """
        Edit a Manufacturer from a web page.
        """
        redirect = self.rename(id)
        self.title = title
        self.url = url
        self.supportNumber = supportNumber
        self.address1 = address1
        self.address2 = address2
        self.city = city
        self.state = state
        self.zip = zip
        self.country = country
        self.regexes = regexes
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            messaging.IMessageSender(self).sendToBrowser(
                'Saved',
                SaveMessage()
            )
            return self.callZenScreen(REQUEST, redirect)


InitializeClass(Manufacturer)
