##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface
from Products.Zuul.interfaces import IInfo, IFacade 

class IDeviceManagement(Interface):
    """
    Marker interface for Properties. 
    """

class IDeviceManagementFacade(IFacade): 

    def addMaintWindow(self, params):
        """
        adds a new Maintenance Window
        """        
            
    def deleteMaintWindow(self, uid, id):
        """
        delete a selected entry
        """    
   
    def getMaintWindows(self, uid):
        """
        Returns information about and the value of maintenance windows.  
        """

    def editMaintWindow(self, params):
        """
        Edits the values of a maintenance window.  
        """        
        
    def getUserCommands(self, uid=None):
        """
        gets all the user commands associated with a device or devices
        """ 
        
    def addUserCommand(self, params):
        """
        add a new user command id
        """
        
    def deleteUserCommand(self, uid, id):
        """
        delete a selected command entry
        """       
        
    def updateUserCommand(self, params):
        """
        complete a new user command, or update an existing one
        """    
        
    def getUserList(self, uid):
        """
        Returns a list of users from all ZenUsers.  
        """
        
    def getRolesList(self, uid):
        """
        Returns a list of users and roles from all ZenUsers.  
        """       
        
    def getAdminRoles(self, uid):
        """
        Returns admin roles associated with this device.  
        """    
        
    def addAdminRole(self, params):
        """
        adds an administrator to a device
        """
        
    def updateAdminRole(self, params):
        """
        adds or updates a role on an existing device administrator
        """
        
    def removeAdmin(self, uid, id):
        """
        removes admin role on an existing device
        """
    
class IMaintenanceWindowInfo(IInfo):
    pass
    
class IUserCommandManagementInfo(IInfo):
    pass
    
class IAdminRoleManagementInfo(IInfo):
    pass    
