##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from zope.component import adapter
from zope.container.interfaces import IObjectAddedEvent, IObjectRemovedEvent
from OFS.interfaces import IObjectWillBeMovedEvent, IObjectWillBeAddedEvent


def unindexBeforeDelete(ob, event):
    """
    Multisubscriber for IIndexed + IObjectWillBeMovedEvent
    """
    if not IObjectWillBeAddedEvent.providedBy(event):
        ob.unindex_object()

def indexAfterAddOrMove(ob, event):
    """
    Multisubscriber for IIndexed + IObjectMovedEvent.
    """
    if not IObjectRemovedEvent.providedBy(event):
        ob.index_object()


"""
    New handlers, once model catalog is implemented for all ZCatalogs
    the above handlers will be removed
"""


def onBeforeObjectDeleted(ob, event):
    """ Subscriber for IObjectEventsSubscriber + IObjectWillBeMovedEvent """
    if not IObjectWillBeAddedEvent.providedBy(event):
        if hasattr(ob, "before_object_deleted_handler"):
            ob.before_object_deleted_handler()


def onAfterObjectAddedOrMoved(ob, event):
    """ Subscriber for IObjectEventsSubscriber + IObjectMovedEvent """
    if not IObjectRemovedEvent.providedBy(event):
        if hasattr(ob, "after_object_added_or_moved_handler"):
            ob.after_object_added_or_moved_handler()


def onObjectAdded(ob, event):
    """ """
    if hasattr(ob, "object_added_handler"):
        ob.object_added_handler()

