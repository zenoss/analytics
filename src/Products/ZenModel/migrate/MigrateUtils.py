##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
Utilities to help with migration scripts.
"""

from OFS.ObjectManager import ObjectManager
from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager
from Products.ZenRelations.ZenPropertyManager import IdentityTransformer

def migratePropertyType(id, dmd, oldType):
    """
    migrate the value of a zProperty that has changed it's type from the
    previous version of the zenpack. there is a chance that the old type or
    new type has a transformer associated with it, so this function handles
    transforming from the old type to the new type.
    
    id is the ID of a zProperty that is know to have changed its type in the
    new version of the zenpack. This function finds all instances of that
    zprop throughout the hierarchy of DeviceClasses and Devices and grabs the 
    raw value and applies the transform that is registered for the oldType.
    It then calls _updateProperty which applies the transform of the new type.
    """
    
    def _genInstanceValues(manager):
        "walk the hierarchy to find all instances of the zproperty id"
        if id in manager._propertyValues:
            yield manager, manager._propertyValues[id]
        elif id in vars(manager):
            yield manager, vars(manager)[id]
        if isinstance(manager, ObjectManager):
            for ob in manager.objectValues():
                if isinstance(ob, ZenPropertyManager):
                    _genInstanceValues(ob)
    
    oldTransformerFactory = dmd.propertyTransformers.get(oldType, 
                                                         IdentityTransformer)
    oldTransformer = oldTransformerFactory()
    for obj, rawValue in _genInstanceValues(dmd.Devices):
        value = oldTransformer.transformForGet(rawValue)
        obj._updateProperty(id, value)
