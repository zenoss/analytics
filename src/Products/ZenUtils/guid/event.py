##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
from zope.event import notify
from zope.component import adapter, getUtility
from zope.interface import implements
from zope.component.interfaces import ObjectEvent
from zope.container.interfaces import IObjectMovedEvent, IObjectRemovedEvent
from OFS.interfaces import IObjectWillBeMovedEvent, IObjectWillBeAddedEvent
from .interfaces import IGUIDEvent, IGUIDManager, IGloballyIdentifiable
from .interfaces import IGlobalIdentifier
from Products.Zuul.catalog.interfaces import IModelCatalog

log = logging.getLogger('zen.UUID')


class GUIDEvent(ObjectEvent):
    implements(IGUIDEvent)
    def __init__(self, obj, old, new, update_global_catalog=True):
        super(GUIDEvent, self).__init__(obj)
        self.old = old
        self.new = new
        self.update_global_catalog = update_global_catalog


@adapter(IGloballyIdentifiable, IGUIDEvent)
def registerGUIDToPathMapping(obj, event):
    mgr = IGUIDManager(obj)
    if event.new:
        mgr.setObject(event.new, obj)
        if event.update_global_catalog:
            try:
                getUtility(IModelCatalog).catalog_object(obj, idxs=("uuid"))
            except Exception:
                log.exception('Encountered a guid exception')
    if event.old and event.old != event.new:
        # When we move a component around,
        # we don't want to remove the guid
        # from the catalog
        if mgr.getPath(event.old) == obj.getPrimaryUrlPath():
            mgr.remove(event.old)


@adapter(IGloballyIdentifiable, IObjectMovedEvent)
def refireEventOnObjectAddOrMove(obj, event):
    if not IObjectRemovedEvent.providedBy(event):
        oldguid = IGlobalIdentifier(obj).getGUID()
        if oldguid is None:
            IGlobalIdentifier(obj).create()
        else:
            # Refire in the case where an object already has a guid
            # but that guid has been removed from the guid table
            notify(GUIDEvent(obj, oldguid, oldguid, False))


@adapter(IGloballyIdentifiable, IObjectWillBeMovedEvent)
def refireEventOnObjectBeforeRemove(obj, event):
    if not IObjectWillBeAddedEvent.providedBy(event):
        guid = IGlobalIdentifier(obj).guid
        notify(GUIDEvent(obj, guid, None))
