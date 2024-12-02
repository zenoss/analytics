##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenRelations.RelSchema import *
from ZenModelRM import ZenModelRM
from ZenossSecurity import *


class AdministrativeRole(ZenModelRM):

    meta_type = "AdministrativeRole"

    _relations = (
        ("userSetting", ToOne(ToMany, "Products.ZenModel.UserSettings", "adminRoles")),
        ("managedObject", ToOne(ToManyCont, "Products.ZenModel.AdministrativeRoleable", "adminRoles")),
    )

    role = ZEN_USER_ROLE

    def __init__(self, userSettings, managedObject):
        userid = userSettings.getId()
        ZenModelRM.__init__(self, userid)
        self.role = userSettings.defaultAdminRole
        self.id = userid
        managedObject = managedObject.primaryAq()
        managedObject.adminRoles._setObject(userid, self)
        self.userSetting.addRelation(userSettings)
        managedObject.manage_setLocalRoles(userid, (self.role,),)
        managedObject.index_object()


    def update(self, role):
        self.role = role
        managedObject = self.managedObject().primaryAq()
        managedObject.manage_setLocalRoles(self.getId(), (self.role,))
        managedObject.index_object()


    def delete(self):
        managedObject = self.managedObject().primaryAq()
        managedObject.manage_delLocalRoles((self.getId(),))
        managedObject.index_object()
        self.userSetting.removeRelation()
        self.managedObject.removeRelation()


    def email(self):
        return self.userSetting().email
  

    def pager(self):
        return self.userSetting().pager

   
    def userLink(self):
        return self.userSetting().getPrimaryUrlPath()

    def managedObjectName(self):
        from Device import Device
        mo = self.managedObject()
        if isinstance(mo, Device) or mo.meta_type == 'Device':
            return mo.id
        return mo.getOrganizerName()

    def getEventSummary(self):
        return self.managedObject().getEventSummary()
    
    def managedObjectType(self):
        return self.managedObject().meta_type

DeviceAdministrativeRole = AdministrativeRole
DevOrgAdministrativeRole = AdministrativeRole
