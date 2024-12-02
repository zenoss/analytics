##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from AccessControl.class_init import InitializeClass

from Products.ZenRelations.RelSchema import ToMany
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.AdvancedQuery import Eq, Not, And
from .ComponentOrganizer import (
    ComponentOrganizer,
)


def manage_addComponentGroup(context, id, description=None, REQUEST=None):
    """add a ComponentGroup"""
    d = ComponentGroup(id, description)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')


class ComponentGroup(ComponentOrganizer):
    """
    ComponentGroup is a Component Group Organizer
    that allows generic component groupings.
    """

    # Organizer configuration
    dmdRootName = "ComponentGroups"

    portal_type = meta_type = event_key = 'ComponentGroup'

    event_key = "ComponentGroup"

    _relations = ComponentOrganizer._relations + (
        ("components", ToMany(
            ToMany, "Products.ZenModel.DeviceComponent", "componentGroups")),
    )

    def getComponents(self):
        return [comp.primaryAq() for comp in self.components()]

    def getSubComponents(self):
        cat = IModelCatalogTool(self)
        # @TODO: Can we avoid NOTs ?
        query = Eq('objectImplements', 'Products.ZenModel.DeviceComponent.DeviceComponent')
        brains = cat.search(query=query)
        children = []
        for brain in brains:
            try:
                children.append(brain.getObject())
            except Exception:
                pass
        return children

InitializeClass(ComponentGroup)
