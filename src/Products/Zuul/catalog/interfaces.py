##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface, Attribute
from zope.component.interfaces import IObjectEvent


class IIndexableWrapper(Interface):
    """
    Wraps IGloballyIndexed objects to provide attrs for the catalog to index.
    """


class IGloballyIndexed(Interface):
    """
    Marker interface for objects indexed by the global_catalog.
    """


class ITreeSpanningComponent(Interface):
    """
    Components that place devices in other trees via non-contained relationship.
    """
    def device():
        """
        Return the device associated with this component.
        """

    def get_indexable_peers():
        """
        return the other tree object/objects that need to be indexed when this
         spanning component is updated
        """

        
class IDeviceOrganizer(Interface):
    """
    An interface that represents acollection of devices
    """
    
    def devices():
        """
        Returns all of the devices that belong to this collection
        """
        

class IIndexingEvent(IObjectEvent):
    """
    An event causing the object to be indexed.
    """
    idxs = Attribute("The names of the indices to be reindexed")
    update_metadata = Attribute("Whether to update the metadata of the object")


class IAfterIndexingEventSubscriber(Interface):
    """
    Notify interested subscribers that IndexingEvent has been processed
    """
    def after_indexing_event(event):
        """
        Custom behavior after the IndexingEvent is processed
        @param event: processed IndexingEvent
        """


class IPathReporter(Interface):
    """
    An adapter that reports the paths under which an object can live, including
    non-containment paths.
    """
    def getPaths():
        """
        Return all paths by which this object may be found.
        """


class IGlobalCatalogFactory(Interface):
    def create(portal_object):
        """
        Creates and sets the global catalog

        @param portal_object: The portal object on which to create the global catalog.
        @type portal_object: zport
        """

    def remove(portal_object):
        """
        Removes the global catalog.

        @param portal_object: The portal object on which to remove the global catalog.
        @type portal_object: zport
        """

class IComponentFieldSpec(Interface):
    def get_fields():
        """
        Returns the fields associated with this type.
        """


class IModelCatalog(Interface):
    """ Marker Interface to register an utility for the model catalog """


class IModelCatalogTool(Interface):
    """ Marker interface for the model catalog search tool """

