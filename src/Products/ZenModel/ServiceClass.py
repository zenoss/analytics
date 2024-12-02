##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ServiceClass

The service classification class.  default identifiers, screens,
and data collectors live here.

$Id: ServiceClass.py,v 1.9 2003/03/11 23:32:13 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
import zope.interface
from Products.ZenModel.ZenossSecurity import *
from Products.ZenModel.interfaces import IIndexed
from Commandable import Commandable
from ZenPackable import ZenPackable

from Products.ZenRelations.RelSchema import *
from Products.ZenRelations.ZenPropertyManager import iszprop
from Products.ZenWidgets import messaging
from zope.component import adapter
from OFS.interfaces import IObjectWillBeRemovedEvent

from ZenModelRM import ZenModelRM

from zope.event import notify
from Products.Zuul.catalog.events import IndexingEvent

def manage_addServiceClass(context, id=None, REQUEST = None):
    """make a device class"""
    if id:
        sc = ServiceClass(id)
        context._setObject(id, sc)
        sc = context._getOb(id)
        sc.createCatalog()
        sc.buildZProperties()

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main') 

addServiceClass = DTMLFile('dtml/addServiceClass',globals())

class ServiceClass(ZenModelRM, Commandable, ZenPackable):
    zope.interface.implements(IIndexed)
    meta_type = "ServiceClass"
    dmdRootName = "Services"
    default_catalog = "serviceSearch"

    name = ""
    serviceKeys = ()
    description = ""
    port = 0 #FIXME prevent failures when ServiceClass is added manually
    
    _properties = (
        {'id':'name', 'type':'string', 'mode':'w'},
        {'id':'serviceKeys', 'type':'lines', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'port', 'type':'int', 'mode':'w'},
        ) 

    _relations = ZenPackable._relations + (
        ("instances", ToMany(ToOne, "Products.ZenModel.Service", "serviceclass")),
        ("serviceorganizer", 
            ToOne(ToManyCont,"Products.ZenModel.ServiceOrganizer","serviceclasses")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        )


    factory_type_information = ( 
        { 
            'id'             : 'ServiceClass',
            'meta_type'      : 'ServiceClass',
            'icon'           : 'ServiceClass.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addServiceClass',
            'immediate_view' : 'serviceClassStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'serviceClassStatus'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'serviceClassEdit'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'serviceClassManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'zProperties'
                , 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
            )
         },
        )
    
    security = ClassSecurityInfo()
   

    def __init__(self, id, serviceKeys=(), description=""):
        self.name = id
        id = self.prepId(id)
        super(ServiceClass, self).__init__(id)
        self.serviceKeys = serviceKeys
        self.description = description
  

    def addServiceKey(self, key):
        """Add a key to the service keys.
        """
        if key not in self.serviceKeys:
            self.serviceKeys = self.serviceKeys + (key,)
            self.index_object()


    def count(self):
        """Return count of instances in this class.
        """
        return self.instances.countObjects()


    def getServiceClassName(self):
        """Return the full name of this service class.
        """
        return self.getPrimaryDmdId("Services", "serviceclasses")


    def saveZenProperties(self, pfilt=iszprop, REQUEST=None):
        """
        Save all ZenProperties found in the REQUEST.form object.
        Overridden so that service instances can be re-indexed if needed
        """
        #get value to see if it changes
        monitor = self.zMonitor
        result = super(ServiceClass, self).saveZenProperties( pfilt, REQUEST)
        if monitor != self.zMonitor :
            #indexes need to be updated so that the updated config will be sent
            self._indexInstances()
        
        return result

    def deleteZenProperty(self, propname=None, REQUEST=None):
        """
        Delete device tree properties from the this DeviceClass object.
        Overridden to intercept zMonitor changes
        """
        monitor = self.zMonitor
        result = super(ServiceClass, self).deleteZenProperty( propname, REQUEST)
        if monitor != self.zMonitor :
            #indexes need to be updated so that the updated config will be sent
            self._indexInstances()
        
        return result

    def _indexInstances(self):
        """
        index instances of this service class to ensure changes made on the
        Service Class are reflected in the instances indexes
        """
        monitor = self.zMonitor
        for inst in self.instances(): 
            inst.monitor = monitor
            inst = inst.primaryAq()
            inst.index_object()

    security.declareProtected('Manage DMD', 'manage_editServiceClass')
    def manage_editServiceClass(self, name="", monitor=False, serviceKeys="",
                               port=0, description="", REQUEST=None):
        """
        Edit a ProductClass from a web page.
        """
        self.name = name
        id = self.prepId(name)
        if self.zMonitor != monitor:
            self.setZenProperty("zMonitor", monitor)
            self._indexInstances()
        redirect = self.rename(id)
        serviceKeys = [ l.strip() for l in serviceKeys.split('\n') ]
        if serviceKeys != self.serviceKeys:
            self.unindex_object()
            self.serviceKeys = serviceKeys
            self.index_object()
        self.port = port
        self.description = description
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            messaging.IMessageSender(self).sendToBrowser(
                'Service Class Saved',
                SaveMessage()
            )
            return self.callZenScreen(REQUEST, redirect)


    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return self.instances()


    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/serviceClassManage'

    def updateServicesInGlobalCatalog(self): 
        """ 
        Method to update global catalog entries for Services under a ServiceClass 
        """ 
        for service in self.instances(): 
            notify(IndexingEvent(service))


InitializeClass(ServiceClass)

@adapter(ServiceClass, IObjectWillBeRemovedEvent)
def onServiceClassRemoved(ob, event):
    # if _operation is set to 1 it means we are moving it, not deleting it
    if getattr(ob, '_operation', None) != 1:
        for i in ob.instances():
            i.manage_deleteComponent()
