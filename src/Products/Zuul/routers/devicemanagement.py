##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import logging
log = logging.getLogger("zen.MaintenanceWindows")

from Products.ZenUtils.Ext import DirectResponse
from Products import Zuul
from Products.Zuul.decorators import require, serviceConnectionError
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils import Time
from Products.ZenMessaging.audit import audit

class DeviceManagementRouter(DirectRouter): 
    """
    Allows setting up of users for administration purposes on devices along
    with maintenance windows and user commands
    """

    def _getFacade(self):
        return Zuul.getFacade('devicemanagement', self.context)  

# ---------------------------------------------------- Maintenance Windows:        
        
    def addMaintWindow(self, params):
        """
        adds a new Maintenance Window
        """    
        facade = self._getFacade()
        facade.addMaintWindow(params)
        audit('UI.MaintenanceWindow.Add', params['uid'] + '/' + params['name'], data_=params)
        return DirectResponse.succeed(msg="Maintenance Window %s added successfully." % (params['name']))
            
    def deleteMaintWindow(self, uid, id):
        """
        delete a maintenance window
        """
        facade = self._getFacade()
        data = facade.deleteMaintWindow(uid, id)
        audit('UI.MaintenanceWindow.Delete', uid + '/' + id)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    def getTimeZone(self):
        """
        Returns local timezone.
        """
        return DirectResponse(data=Time.getLocalTimezone())

    @serviceConnectionError
    def getMaintWindows(self, uid, params=None):
        """
        Returns the definition and values of all
        the maintenance windows for this context
        @type  uid: string
        @param uid: unique identifier of an object
        @type params: none
        @param params: none for page reloads and error avoidance
        """
        facade = self._getFacade()
        data = facade.getMaintWindows(uid)
        return DirectResponse( data=Zuul.marshal(data) )  
        
    def editMaintWindow(self, params):
        """
        Edits the values of of a maintenance window
        for this context and window id
        @type  params: dict
        @param params: 
        """
        facade = self._getFacade()
        data = facade.editMaintWindow(params)
        return DirectResponse( data=Zuul.marshal(data) ) 
        
# ---------------------------------------------------- User Commands:       

    @serviceConnectionError
    def getUserCommands(self, uid, params=None):
        """
        Get a list of user commands for a device uid.

        @type  uid: string
        @param uid: Device to use to get user commands
        @rtype:   [dictionary]
        @return:  List of objects representing user commands
        """
        facade = self._getFacade()
        data = facade.getUserCommands(uid)
        return DirectResponse( data=Zuul.marshal(data) )       

    @require('Define Commands Edit')
    def addUserCommand(self, params):
        """
        add a new user command to devices
        """
        facade = self._getFacade()
        facade.addUserCommand(params)
        #work in password and not just succeed()
        audit('UI.UserCommand.Add', params['name'], data_=params)
        return DirectResponse.succeed()
        
    @require('Define Commands Edit')
    def deleteUserCommand(self, uid, id):
        """
        delete a user command
        """
        facade = self._getFacade()
        data = facade.deleteUserCommand(uid, id)
        audit('UI.UserCommand.Delete', uid + '/' + id)
        return DirectResponse.succeed(data=Zuul.marshal(data))

    @require('Define Commands Edit')
    def updateUserCommand(self, params):
        """
        completes or updates an existing user command
        """
        facade = self._getFacade()
        facade.updateUserCommand(params)
        #work in password and not just succeed()
        audit('UI.UserCommand.Edit', params['uid'] + '/' + params['id'])
        return DirectResponse.succeed()
        
# ---------------------------------------------------- Admin Roles:    
        
    @serviceConnectionError
    def getUserList(self, uid):
        """
        Returns the admin roles associated with
        the device for this context
        @type  uid: string
        @param uid: unique identifier of an object
        """
        facade = self._getFacade()
        data = facade.getUserList(uid)
        return DirectResponse( data=Zuul.marshal(data) ) 
        
    @serviceConnectionError
    def getRolesList(self, uid):
        """
        Returns the admin roles associated with
        the device for this context
        @type  uid: string
        @param uid: unique identifier of an object
        """
        facade = self._getFacade()
        data = facade.getRolesList(uid)
        return DirectResponse( data=Zuul.marshal(data) )         
        
    @serviceConnectionError
    def getAdminRoles(self, uid, params=None):
        """
        Returns the admin roles associated with
        the device for this context
        @type  uid: string
        @param uid: unique identifier of an object
        """
        facade = self._getFacade()
        data = facade.getAdminRoles(uid)
        return DirectResponse( data=Zuul.marshal(data) )        
        
    def addAdminRole(self, params):
        """
        add an admin with a role to a device
        """
        facade = self._getFacade()
        facade.addAdminRole(params)
        audit('UI.AdminRole.Add', params['uid'] + '/' + params['name'])
        return DirectResponse.succeed(msg="New Administrator added successfully.")
        
    def updateAdminRole(self, params):
        """
        adds or updates a role on a existing device administrator
        """
        facade = self._getFacade()
        facade.updateAdminRole(params)
        audit('UI.AdminRole.Update', params['uid'] + '/' + params['name'])
        return DirectResponse.succeed()
        
    def removeAdmin(self, uid, id):
        """
        removes admin and role on a existing device
        """
        facade = self._getFacade()
        facade.removeAdmin(uid, id)
        audit('UI.AdminRole.Delete', uid + '/' + id)
        return DirectResponse.succeed()
