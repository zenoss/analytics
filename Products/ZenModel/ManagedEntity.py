##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""ManagedEntity
Objects that may of be interest from a CMDB perspective.
"""

import logging
log = logging.getLogger("zen.DeviceComponent")

from zope.event import notify

from ZenModelRM import ZenModelRM
from DeviceResultInt import DeviceResultInt
from MetricMixin import MetricMixin
from EventView import EventView
from Products.Zuul.catalog.events import IndexingEvent
from Products.ZenRelations.RelSchema import ToMany, ToManyCont, ToOne
from .ZenossSecurity import ZEN_CHANGE_DEVICE_PRODSTATE
from AccessControl import ClassSecurityInfo
from Products.ZenWidgets.interfaces import IMessageSender
from Products.ZenModel.MaintenanceWindowable import MaintenanceWindowable

from Products.ZenUtils.productionstate.interfaces import IProdStateManager, ProdStateNotSetError
from Products.ZenMessaging.ChangeEvents.subscribers import publishModified
from Acquisition import aq_parent, ImplicitAcquisitionWrapper

class ImplicitAcquisitionWrapper_ManagedEntity(ImplicitAcquisitionWrapper):
    # Zope's wrapper overrides __getattribute__ to ignore attributes on the wrapper class that don't start with "aq"
    #  so rather than creating a property, we will we need to override __getattribute__, __setattr__, and __delattr__
    def __getattribute__(self, name):
        if name=="productionState":
            return self.getProductionState()
        else:
            return super(ImplicitAcquisitionWrapper_ManagedEntity, self).__getattribute__(name)

    def __setattr__(self, name, value):
        if name=="productionState":
            self._setProductionState(value)
        else:
            super(ImplicitAcquisitionWrapper_ManagedEntity, self).__setattr__(name, value)

    def __delattr__(self, name):
        if name=="productionState":
            self.resetProductionState()
        else:
            super(ImplicitAcquisitionWrapper_ManagedEntity, self).__delattr__(name)



class ManagedEntity(ZenModelRM, DeviceResultInt, EventView, MetricMixin,
                    MaintenanceWindowable):
    """
    ManagedEntity is an entity in the system that is managed by it.
    Its basic property is that it can be classified by the ITClass Tree.
    Also has EventView and MetricMixin available.
    """

    # list of performance multigraphs (see PerformanceView.py)
    # FIXME this needs to go to some new setup and doesn't work now
    #_mgraphs = []

    # primary snmpindex for this managed entity
    snmpindex = 0
    snmpindex_dct = {}
    monitor = True

    _properties = (
     {'id':'snmpindex', 'type':'string', 'mode':'w'},
     {'id':'monitor', 'type':'boolean', 'mode':'w'},
    )

    _relations = (
        ("dependencies", ToMany(ToMany, "Products.ZenModel.ManagedEntity", "dependents")),
        ("dependents", ToMany(ToMany, "Products.ZenModel.ManagedEntity", "dependencies")),
        ("componentGroups", ToMany(ToMany, "Products.ZenModel.ComponentGroup", "components")),
        ("maintenanceWindows",ToManyCont(
            ToOne, "Products.ZenModel.MaintenanceWindow", "productionState")),
    )

    security = ClassSecurityInfo()

    def device(self):
        """Overridden in lower classes if a device relationship exists.
        """
        return None
    
    def getProdStateManager(self):
        return IProdStateManager(self)

    def getProductionState(self):
        try:
            return self.getProdStateManager().getProductionState(self)
        except (ProdStateNotSetError, AttributeError, TypeError):
            return aq_parent(self).getProductionState()
        
    def _setProductionState(self, state):
        self.getProdStateManager().setProductionState(self, state)

    def getPreMWProductionState(self):
        try:
            return self.getProdStateManager().getPreMWProductionState(self)
        except (ProdStateNotSetError, AttributeError, TypeError):
            return aq_parent(self).getPreMWProductionState()

    def setPreMWProductionState(self, state):
        self.getProdStateManager().setPreMWProductionState(self, state)

    def resetProductionState(self):
        self.getProdStateManager().clearProductionState(self)

    # In order to maintain backward-compatibility, we need to preserve productionState as a property.
    #  Our getProductionState() method requires acquisition context, so we have to add the property
    #  onto the wrapped object and not on the ManagedEntity object itself.  We do this by sub-classing 
    #  Zope's wrapper. 
    #  Note that sub-classing sope's wrapper only works because we modified the Acquisition
    #  source code to handle it properly. The modifications to Acquisition can be seen here:
    #  https://github.com/zenoss/Acquisition/pull/1
    def __of__(self, container):
        return ImplicitAcquisitionWrapper_ManagedEntity(self, container)

    def getProductionStateString(self):
        """
        Return the prodstate as a string.

        @rtype: string
        """
        return str(self.convertProdState(self.getProductionState()))

    security.declareProtected(ZEN_CHANGE_DEVICE_PRODSTATE, 'setProdState')
    def setProdState(self, state, maintWindowChange=False, REQUEST=None):
        """
        Set the device's production state.

        @parameter state: new production state
        @type state: int
        @parameter maintWindowChange: are we resetting state from inside a MW?
        @type maintWindowChange: boolean
        @permission: ZEN_CHANGE_DEVICE
        """
        self._setProductionState(int(state))

        if not maintWindowChange:
            # Saves our production state for use at the end of the
            # maintenance window.
            self.setPreMWProductionState(self.getProductionState()) 

        publishModified(self, None)


        if REQUEST:
            IMessageSender(self).sendToBrowser(
                "Production State Set",
                "%s's production state was set to %s." % (self.id,
                                      self.getProductionStateString())
            )
            return self.callZenScreen(REQUEST)

    def getComponentGroupNames(self):
        # lazily create the relationship so we don't have to do a migrate script
        if not hasattr(self, "componentGroups"):
            return []
        return [group.getOrganizerName() for group in self.componentGroups()]

    def getComponentGroups(self):
        # lazily create the relationship so we don't have to do a migrate script
        if not hasattr(self, "componentGroups"):
            return []
        return self.componentGroups()

    def setComponentGroups(self, groupPaths):
        relPaths = groupPaths
        if not hasattr(self, "componentGroups"):
            self.buildRelations()
        objGetter = self.dmd.ComponentGroups.createOrganizer
        relName = "componentGroups"
        # set the relations between the component (self) and the groups
        if not isinstance(relPaths, (list, tuple)):
            relPaths = [relPaths, ]
        relPaths = filter(lambda x: x.strip(), relPaths)
        rel = getattr(self, relName, None)
        curRelIds = {}
        # set a relationship for every group
        for value in rel.objectValuesAll():
            curRelIds[value.getOrganizerName()] = value
        for path in relPaths:
            if path not in curRelIds:
                robj = objGetter(path)
                self.addRelation(relName, robj)
            else:
                del curRelIds[path]

        # remove any that were left over
        for obj in curRelIds.values():
            self.removeRelation(relName, obj)

        # reindex
        self.index_object()
        notify(IndexingEvent(self, 'path', False))

