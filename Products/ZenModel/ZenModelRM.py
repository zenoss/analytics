##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """ZenModelRM

$Id: ZenModelRM.py,v 1.50 2004/05/10 20:49:09 edahl Exp $"""

__version__ = "$Revision: 1.50 $"[11:-2]

import os
import time

from DateTime import DateTime
from OFS.History import Historical
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from ZPublisher.Converters import type_converters
from zope.interface import implements
from OFS.interfaces import IItem

from ZenModelBase import ZenModelBase, iscustprop
from ZenPacker import ZenPacker
from Products.ZenWidgets import messaging
from Products.ZenUtils.path import zenPath
from Products.ZenUtils.Utils import getSubObjects
from Products.ZenRelations.ImportRM import ImportRM
from Products.ZenRelations.RelationshipManager import RelationshipManager
from Products.ZenModel.ZenossSecurity import (
    ZEN_MANAGE_DMD,
    ZEN_VIEW,
    ZEN_CHANGE_DEVICE_PRODSTATE
)


from Products.Zuul.catalog.indexable import BaseIndexable
from Products.Zuul.catalog.interfaces import IModelCatalogTool

class ZenModelRM(ZenModelBase, RelationshipManager, Historical, ZenPacker, BaseIndexable):
    """
    Base class for all Persistent classes that have relationships.
    Provides RelationshipManagement, Customized PropertyManagement,
    Catalog Indexing, and Historical change tracking.
    """
    implements(IItem)
    meta_type = 'ZenModelRM'

    default_catalog = ''

    isInTree = 0  # should this class show in left nav tree

    security = ClassSecurityInfo()

    def __init__(self, id, title=None, buildRelations=True):
        self._created_timestamp = time.time()
        self.createdTime = DateTime(self._created_timestamp)
        RelationshipManager.__init__(self, id, title, buildRelations)

    @property
    def created_timestamp(self):
        try:
            return self._created_timestamp
        except AttributeError:
            self._created_timestamp = self.createdTime.timeTime()
            return self._created_timestamp

    security.declareProtected(ZEN_MANAGE_DMD, 'setTitle')
    def setTitle(self, title):
        self.title = title
        IModelCatalogTool(self).update(self)

    security.declareProtected(ZEN_MANAGE_DMD, 'rename')
    def rename(self, newId, REQUEST=None):
        """Delete device from the DMD"""
        renamed = False
        if newId and newId != self.getId():
            parent = self.getPrimaryParent()
            oldId = self.getId()
            parent.manage_renameObject(oldId, newId)
            renamed = True
        if REQUEST:
            if renamed:
                messaging.IMessageSender(self).sendToBrowser(
                    'Object Renamed',
                    "Object %s was renamed to %s." % (oldId, newId)
                )
            return self.callZenScreen(REQUEST, renamed)
        return renamed

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None, redirect=False, audit=True):
        """Edit a ZenModel object and return its proper page template
        """
        redirect = False
        if "newId" in REQUEST.form:
            redirect = self.rename(REQUEST.form["newId"])
        return ZenModelBase.zmanage_editProperties(
            self, REQUEST, redirect, audit
        )

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_addProperty')
    def zmanage_addProperty(
        self, id, value, type, label, visible, prefix='c', REQUEST=None
    ):
        """Add a new property via the web.
        Sets a new property with the given id, type, and value.
        Id must start with a 'c' for custom attributes added via the
        Custom Schema tab.
        """
        if type in type_converters and value:
            value = type_converters[type](value)
        id = id.strip()
        if prefix and not id.startswith(prefix):
            id = prefix + id
        if not iscustprop(id):
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    "Custom property name should be in this format: cProperty",
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
        elif self.hasProperty(id):
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    "Custom property: %s already exists" % id,
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
        else:
            self._setProperty(id, value, type, label, visible)
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Property Added',
                    "Custom property: %s added" % id
                )
                return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_exportObject')
    def zmanage_exportObject(self, context=None, REQUEST=None):
        """Export objects to specific locations.
        """
        if not context:
            context = self
        redirect = False
        dest = 'filesystem'
        if REQUEST:
            dest = REQUEST.form.get('dest')
        fileBase = '%s_%s.xml' % (context.getNodeName(), context.id)
        if dest == 'filesystem':
            filename = zenPath('export', fileBase)
            msg = "Item has been exported to: %s at " % filename
        elif dest == 'zenossdotnet':
            # create temp file
            filename = ''
            # get https URL for user space at Zenoss.net
            url = 'https://%s:%s@zenoss.net/'
            # build XML-RPC proxy object for publishing to Zenoss.net
            import xmlrpclib
            server = xmlrpclib.ProxyServer(url)
            msg = "Item has been exported to: %s. Note that you will need to "
            msg += "login at Zenoss.net and publish this template in order to "
            msg += "share it with others. Exported at "
            msg %= url
        # open file
        exportFile = open(filename, 'w+')
        # export object to file
        context.exportXml(exportFile)
        # cleanup
        exportFile.close()
        if dest == 'zenossdotnet':
            # get data
            exportFile = open(filename)
            dataToSend = exportFile.read()
            exportFile.close()
            # push data up to Zenoss.net
            server.postUserTemplate(dataToSend)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Export Object', msg)
            return self.callZenScreen(REQUEST, redirect)

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_importObjects')
    def zmanage_importObjects(self, context=None, REQUEST=None):
        """Import an XML file as the Zenoss objects and properties it
        represents.
        """
        # XXX
        # for right now, we're only using this through the web, so a REQUEST is
        # always define; when we have a use-case for imports via command line,
        # we will add that code here
        if not context:
            context = self.getPhysicalRoot()
        # get the submitted data
        filenames = REQUEST.form.get('filenames')
        urlnames = REQUEST.form.get('urlnames')
        doDelete = REQUEST.form.get('dodelete')
        xmlfiles = []
        for collection in [filenames, urlnames]:
            if collection:
                if isinstance(collection, list):
                    xmlfiles.extend(collection)
                else:
                    xmlfiles.append(collection)
        # load the objects into Zenoss
        im = ImportRM(noopts=True, app=self.getPhysicalRoot())
        for xmlfile in xmlfiles:
            im.loadObjectFromXML(context, xmlfile)
            if doDelete and xmlfile in filenames:
                os.unlink(xmlfile)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Import Objects', 'Objects imported')
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_importObject')
    def zmanage_importObject(self, REQUEST=None):
        """Import objects into Zenoss.
        """
        pass

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_delProperties')
    def zmanage_delProperties(self, ids=(), REQUEST=None):
        """Delete properties from an object.
        """
        for id in ids:
            self._delProperty(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Properties Deleted',
                'Properties %s have been deleted' % (', '.join(ids))
            )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_delObjects')
    def zmanage_delObjects(self, ids=(), relation="", REQUEST=None):
        """Delete objects from this object or one of its relations.
        """
        target = self
        if relation:
            target = self._getOb(relation)
        for id in ids:
            target._delObject(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Objects Deleted',
                'Objects %s have been deleted' % (', '.join(ids))
            )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_VIEW, 'getDmdKey')
    def getDmdKey(self):
        """
        Hook to get the name of an object.  Usually its self.getId() but is
        overridden by Organizer to be getOrganizerName.

        >>> dmd.Manufacturers.createManufacturer('Cisco').getDmdKey()
        'Cisco'
        >>> dmd.Devices.Server.getDmdKey()
        '/Server'
        """
        return self.getId()

    security.declareProtected(ZEN_VIEW, 'primarySortKey')
    def primarySortKey(self):
        """
        Hook for the value used to sort this object.  Defaults to self.getId().
        """
        return self.titleOrId()

    security.declareProtected(ZEN_VIEW, 'viewName')
    def viewName(self):
        return self.titleOrId()

    def getTreeItems(self):
        nodes = []
        for item in self.objectValues():
            if hasattr(aq_base(item), "isInTree") and item.isInTree:
                nodes.append(item)
        return nodes

    def getSubObjects(self, filter=None, decend=None, retobjs=None):
        return getSubObjects(self, filter, decend, retobjs)

    def getCreatedTimeString(self):
        """return the creation time as a string"""
        return self.createdTime.strftime('%Y/%m/%d %H:%M:%S')

    def getModificationTimeString(self):
        """return the modification time as a string"""
        return self.bobobase_modification_time().strftime('%Y/%m/%d %H:%M:%S')

    def changePythonClass(self, newPythonClass, container):
        """change the python class of a persistent object"""
        id = self.id
        nobj = newPythonClass(id)  # make new instance from new class
        nobj = nobj.__of__(container)  # make aq_chain same as self
        nobj.oldid = self.id
        nobj.setPrimaryPath()  # set up the primarypath for the copy
        # move all sub objects to new object
        nrelations = self.ZenSchemaManager.getRelations(nobj).keys()
        for sobj in self.objectValues():
            RelationshipManager._delObject(self, sobj.getId())
            if not hasattr(nobj, sobj.id) and sobj.id in nrelations:
                setObject = RelationshipManager._setObject
                setObject(nobj, sobj.id, sobj)
        nobj.buildRelations()  # build out any missing relations
        # copy properties to new object
        noprop = getattr(nobj, 'zNoPropertiesCopy', [])
        for name in nobj.getPropertyNames():
            if (
                getattr(self, name, None)
                and name not in noprop
                and hasattr(nobj, "_updateProperty")
            ):
                val = getattr(self, name)
                nobj._updateProperty(name, val)
        return aq_base(nobj)

    def getZenRootNode(self):
        """Return the root node for our zProperties."""
        return self.getDmdRoot(self.dmdRootName)

    def editableDeviceList(self):
        """
        Return true if user has Manager role and self has a deviceList.
        """
        if not getattr(aq_base(self), "deviceMoveTargets", False):
            return False

        return bool(
            self.isManager() or
            self.checkRemotePerm(ZEN_CHANGE_DEVICE_PRODSTATE, self)
        )

    def creator(self):
        """
        Method needed for CatalogAwarnessInterface.  Implemented here so that
        Subclasses (who would have the same implementation) don't need to.
        Other methods (except reindex_all) are implemented on the concreate
        class.
        """
        users = []
        for user, roles in self.get_local_roles():
            if 'Owner' in roles:
                users.append(user)
        return ', '.join(users)

    def index_object(self, idxs=None):
        """A common method to allow Findables to index themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat is not None:
            cat.catalog_object(self, self.getPrimaryId(), idxs=idxs)

    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat is not None:
            cat.uncatalog_object(self.getPrimaryId())

    def reindex_all(self, obj=None):
        """
        Called for in the CataLogAwarenessInterface not sure this is needed.
        """
        if obj is None:
            obj = self
        if hasattr(aq_base(obj), 'index_object'):
            obj.index_object()
        if hasattr(aq_base(obj), 'objectValues'):
            sub = obj.objectValues()
            for item in sub:
                self.reindex_all(item)
        return 'done!'

    def findChild(self, path):
        """
        Find child using the ids found in path. Path separator is '/'.  This
        is similar to using attributes, but doesn't use acquisition.  For
        example, if 'Devices/Server/Linux' exists, but
        'Devices/Server/SSH/Linux' does not, then the two methods will behave
        differently.  dmd.Devices.Server.SSH.Linux will return
        'Devices/Server/Linux', whereas this method will throw an exception.
        """
        child = self
        for id in path.split('/'):
            child = child._getOb(id)
        return child
