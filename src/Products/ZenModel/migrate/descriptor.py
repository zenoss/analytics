##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from OFS.ObjectManager import ObjectManager
from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager

def migrateZProps(manager):
    """
    Copy the manager's zProperties from its __dict__ to its _propertyValues
    dictionary. Then do the same recursively for any child 
    ZenPropertyManagers.
    """
    manager._p_changed = True
    for id in vars(manager).keys():
        # PropertyDescriptor moves the value from __dict__ to
        # _propertyValues when getattr is called
        getattr(manager, id)
    if isinstance(manager, ObjectManager):
        for ob in manager.objectValues():
            if isinstance(ob, ZenPropertyManager):
                migrateZProps(ob)

class descriptor(Migrate.Step):
    version = Migrate.Version(2, 5, 0)
    
    def cutover(self, dmd):
        migrateZProps(dmd.Devices)
        
descriptor()
