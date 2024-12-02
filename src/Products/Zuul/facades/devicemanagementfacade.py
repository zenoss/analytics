##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re
log = logging.getLogger('zen.DeviceManagementFacade')

from zope.interface import implements
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IDeviceManagementFacade, IInfo
from Products.ZenMessaging.audit import audit

class DeviceManagementFacade(ZuulFacade):
    implements(IDeviceManagementFacade)
    
# ---------------------------------------------------- Maintenance Windows:    
         
    def addMaintWindow(self, params):
        """
        adds a new Maintenance Window
        """
        newMw = None
        obj = self._getObject(params['uid'])

        id = params['name'].strip()
        if not id:
            raise Exception('Missing Maintenance Window name.')
        if re.compile(r'[^a-zA-Z0-9-_,.$\(\) ]').findall(id):
            raise Exception('`name` contains bad characters. '
                'Use only a-z, A-Z, 0-9, (, ), $, _, dash, dot '
                'and whitespace.')
        obj.manage_addMaintenanceWindow(id)
        maintenanceWindows = (IInfo(s) for s in obj.maintenanceWindows())
        try:
            newMw = (x for x in maintenanceWindows if x.id == id).next()
        except StopIteration:
            pass
        if newMw:
            newMw.updateWindow(params)
            
    def deleteMaintWindow(self, uid, id):
        """
        delete a selected entry
        """
        obj = self._getObject(uid)
        obj.manage_deleteMaintenanceWindow((id))          
   
    def getMaintWindows(self, uid):
        """
        Returns information about and the value of maintenance windows.  

        @type  uid: string
        @param uid: unique identifier of an object
        """
        obj = self._getObject(uid)      
        maintenanceWindows = [IInfo(s) for s in obj.maintenanceWindows()]    
        return maintenanceWindows   

    def editMaintWindow(self, params):
        """
        Edits the values of a maintenance window.  

        @type  params: dict
        @param params: 
        """
        obj = self._getObject(params['uid'])
        maintenanceWindows = []
        oldData = {}
        for s in obj.maintenanceWindows():
            maintenanceWindowInfo = IInfo(s)
            if (maintenanceWindowInfo.id == params['id']):
                durationString = s.niceDuration()
                durationDict = s.durationStringParser(durationString)
                oldData.update({
                    'repeat': s.repeat,
                    'durationMinutes': durationDict.get('minutes', '00'),
                    'uid': maintenanceWindowInfo.uid,
                    'durationHours': durationDict.get('hours', '00'),
                    'startProductionState': s.startProductionState,
                    'enabled': s.enabled,
                    'durationDays': durationDict.get('days', '0'),
                    'startDateTime': s.start,
                    'id': s.id
                })
                maintenanceWindowInfo.updateWindow(params)
            maintenanceWindows.append(maintenanceWindowInfo)

        audit('UI.MaintenanceWindow.Edit', params['uid'] + '/' + params['id'], oldData_=oldData, data_=params)
        return maintenanceWindows
        
# ---------------------------------------------------- User Commands:        
        
    def getUserCommands(self, uid=None):
        """
        gets all the user commands associated with a device or devices
        """
        obj = self._getObject(uid)
        userCommands = (IInfo(s) for s in obj.getUserCommands())        
        return userCommands      
        
    def addUserCommand(self, params):
        """
        add a new user command id
        """
        obj = self._getObject(params['uid'])

        if not obj.ZenUsers.authenticateCredentials(obj.ZenUsers.getUser().getId(), params['password']):
            raise Exception('Add new command failed. Incorrect or missing password.')
            
        obj.manage_addUserCommand(newId=params['name'], cmd=params['command'], desc=params['description'])
        
    def deleteUserCommand(self, uid, id):
        """
        delete a selected command entry
        """
        obj = self._getObject(uid)
        obj.manage_deleteUserCommand((id))        
        
    def updateUserCommand(self, params):
        """
        complete a new user command, or update an existing one
        """
        obj = self._getObject(params['uid'])

        if not obj.ZenUsers.authenticateCredentials(obj.ZenUsers.getUser().getId(), params['password']):
            raise Exception('Update failed. Incorrect or missing password.')
            
        userCommands = [IInfo(s) for s in obj.getUserCommands()]
        for cmd in userCommands:
            if(cmd.id == params['id']):
                cmd.updateUserCommand(params)    
        
# ---------------------------------------------------- Admin Roles:        
        
    def getUserList(self, uid):
        """
        Returns a list of users from all ZenUsers.  

        @type  uid: string
        @param uid: unique identifier of an object
        """
        users = self._dmd.ZenUsers.getAllUserSettingsNames()
        return users 
        
    def getRolesList(self, uid):
        """
        Returns a list of users and roles from all ZenUsers.  

        @type  uid: string
        @param uid: unique identifier of an object
        """
        roles = self._dmd.ZenUsers.getAllRoles()
        return roles         
        
    def getAdminRoles(self, uid):
        """
        Returns admin roles associated with this device.  

        @type  uid: string
        @param uid: unique identifier of an object
        """
        obj = self._getObject(uid)
        adminRoles = (IInfo(s) for s in obj.adminRoles())         
        return adminRoles           
        
    def addAdminRole(self, params):
        """
        adds an administrator to a device
        """
        id = params['name'].strip()         
        obj = self._getObject(params['uid'])
        obj.manage_addAdministrativeRole(id)
        
    def updateAdminRole(self, params):
        """
        adds or updates a role on an existing device administrator
        """
        obj = self._getObject(params['uid'])
        obj.manage_editAdministrativeRoles((params['name']), (params['role']))
        
    def removeAdmin(self, uid, id):
        """
        removes admin role on an existing device
        """
        obj = self._getObject(uid)
        obj.manage_deleteAdministrativeRole((id))
