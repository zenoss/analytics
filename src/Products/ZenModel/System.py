##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""System

$Id: System.py,v 1.45 2004/04/14 22:11:48 edahl Exp $"""

__version__ = "$Revision: 1.45 $"[11:-2]

from AccessControl import ClassSecurityInfo
from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from DeviceOrganizer import DeviceOrganizer
from ZenPackable import ZenPackable


def manage_addSystem(context, id, description = None, REQUEST = None):
    """make a System"""
    d = System(id, description)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main') 


addSystem = DTMLFile('dtml/addSystem',globals())



class System(DeviceOrganizer, ZenPackable):
    """
    System class is a device organizer that represents a business system.
    May need to manage "services" as well so that more sophisticated 
    dependencies can be tracked.
    """

    # Organizer configuration
    dmdRootName = "Systems"

    portal_type = meta_type = 'System'

    event_key = "System"

    default_catalog = 'systemSearch'
    
    _properties = (
        {'id':'systemClass', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        )
    _relations = DeviceOrganizer._relations + ZenPackable._relations + (
        ("devices", ToMany(ToMany, "Products.ZenModel.Device", "systems")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'System',
            'meta_type'      : 'System',
            'description'    : """Base class for all devices""",
            'icon'           : 'System_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addSystem',
            'immediate_view' : 'deviceOrganizerStatus',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'deviceOrganizerStatus'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'deviceOrganizerManage'
                , 'permissions'   : ('Manage DMD',)
                },
            )
         },
        )


    security = ClassSecurityInfo()


    security.declareProtected('View', 'omniPingStatus')
    def omniPingStatus(self):
        """pingStatus() -> return the number of devices that are down"""
        status = -1
        try:
            status = self.netcool.getPingStatus(system=self.getOrganizerName())
            status = self.convertStatus(status)
        except Exception: pass
        return status
   

    security.declareProtected('View', 'omniCmtsPingStatus')
    def omniCmtsPingStatus(self):
        """omniCmtsPingStatus() -> return the number of ubrs that are down"""
        status = -1
        try:
            status = self.netcool.getOmniStatus(
                   systemName=self.getOrganizerName(),
                   where=" Class=100 and Severity=5 and Node like '.*cmts.*'")
            status = self.convertStatus(status)
        except Exception: pass
        return status


    security.declareProtected('View', 'omniSnmpStatus')
    def omniSnmpStatus(self):
        """snmpStatus() -> return the number of devices with snmp problems"""
        status = -1
        try:
            status = self.netcool.getSnmpStatus(system=self.getOrganizerName())
            status = self.convertStatus(status)
        except Exception: pass
        return status


    security.declareProtected('View', 'omniXmlRpcStatus')
    def omniXmlRpcStatus(self):
        """xmlRpcStatus() -> return the number of devices with xmlrpc problems"""
        status = -1
        try:
            status = self.netcool.getXmlRpcStatus(system=self.getOrganizerName())
            status = self.convertStatus(status)
        except Exception: pass
        return status


    security.declareProtected('View', 'omniEventCount')
    def omniEventCount(self):
        """eventCount() -> return the number of devices with snmp problems"""
        status = 0 
        try:
            status = self.netcool.getEventCount(system=self.getOrganizerName())
        except Exception: pass
        return status


    def summary(self):
        """text summary of object for indexing"""
        return self.getOrganizerName() + " " + self.description
    

    security.declareProtected('View', 'convertProdState')
    def convertProdState(self, prodState):
        '''convert a numeric production state to a
        textual representation using the prodStateConversions
        map'''
        
        if self.prodStateConversions:
            for line in self.prodStateConversions: #aq
                line = line.rstrip()
                (sev, num) = line.split(':')
                if int(num) == prodState:
                    return sev
        return "Unknown"


InitializeClass(System)
