##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import time
import re
import sre_constants
from itertools import islice
from zope.interface import implements
from BTrees.OOBTree import OOBTree
from BTrees.IIBTree import IIBTree
from Products.AdvancedQuery import Eq, Or, Generic, And, In, MatchRegexp
from Products.ZCatalog.interfaces import ICatalogBrain
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.interfaces import ITreeNode, ICatalogTool, IInfo
from Products.Zuul.utils import dottedname, unbrain, allowedRolesAndGroups
from Products.Zuul.utils import UncataloguedObjectException, PathIndexCache
from AccessControl import getSecurityManager
from Products.Zuul.infos import InfoBase
from Products.Zuul import getFacade
from Products.Zuul.decorators import memoize
from Products.ZenUtils.NaturalSort import natural_compare
from Products import Zuul
from Products.ZenModel.ZenossSecurity import ZEN_VIEW
import logging
log = logging.getLogger("zen.tree")


class TreeNode(object):
    """
    Adapts a brain.
    """
    implements(ITreeNode)

    def __init__(self, ob, root=None, parent=None):
        self._root = root or self
        if getattr(self._root, '_ob_cache', None) is None:
            self._root._ob_cache = {}
        if not ICatalogBrain.providedBy(ob):
            brain = IModelCatalogTool(ob).getBrainFromObject(ob)
            if brain is None:
                raise UncataloguedObjectException(ob)
            # We already have the object - cache it here so _get_object doesn't
            # have to look it up again.
            self._root._ob_cache[brain.getPath()] = ob
            ob = brain
        self._object = ob
        self._parent = parent or None
        self._severity = None
        # allow showing the event severity icons to be configurable
        if not hasattr(self._root, '_showSeverityIcons'):
            self._root._showSeverityIcons = self._shouldShowSeverityIcons()

    def _shouldShowSeverityIcons(self):
        return self._get_object().dmd.UserInterfaceSettings.getInterfaceSettings().get('showEventSeverityIcons')

    def _get_object(self):
        obj = self._root._ob_cache.get(self.uid)
        if not obj:
            obj = self._object._unrestrictedGetObject()
            self._root._ob_cache[self.uid] = obj
        return obj

    def _buildCache(self, orgtype=None, instancetype=None, relname=None,
                    treePrefix=None, orderby=None):
        if orgtype and not getattr(self._root, '_cache', None):
            cat = ICatalogTool(self._object.unrestrictedTraverse(self.uid))
            results = cat.search(orgtype, orderby=orderby)
            if instancetype:
                instanceresults = cat.search(instancetype, orderby=None)
                self._root._cache = PathIndexCache(results, instanceresults,
                                                   relname, treePrefix)
            else:
                self._root._cache = PathIndexCache(results)
        return self._root._cache

    @property
    def uuid(self):
        return self._object.uuid

    @property
    def uid(self):
        return self._object.getPath()

    @property
    def path(self):
        """
        Get the tree path for an object by querying the catalog.

        This is cheaper than modifying getPrimaryPath(), which has to wake up
        each parent object just to get its id.
        """
        return self.uid.replace('/zport/dmd/', '')

    @property
    def id(self):
        return self.uid.replace('/', '.')

    @property
    def text(self):
        return self._object.name

    def setSeverity(self, severity):
        self._severity = severity

    def _loadSeverity(self):
        if self._severity is None:
            if self.uuid:
                zep = getFacade('zep')
                sev = zep.getSeverityName(zep.getWorstSeverity([self.uuid]).get(self.uuid, 0)).lower()
                self._severity = sev
        return self._severity

    @property
    def iconCls(self):
        icon = None
        if self._root._showSeverityIcons:
            obj = self._get_object()
            if Zuul.checkPermission(ZEN_VIEW, obj):
                sev = self._loadSeverity()
                icon = self.getIconCls(sev)
        return icon

    def getIconCls(self, sev):
        return 'tree-severity-icon-small-%s' % (sev or 'clear')

    @property
    def children(self):
        raise NotImplementedError

    def __repr__(self):
        return "<TreeNode %s>" % self.uid

    @property
    @memoize
    def hidden(self):
        """
        Make sure we don't show the root node of a tree
        if we don't have permission on it or any of its children
        """
        # always show the root Device organizer so restricted users can see
        # all of the devices they have access to
        if self.uid == '/zport/dmd/Devices':
            return False

        # make sure we are looking at a root node
        pieces = self.uid.split('/')
        if len(pieces) != 4:
            return False

        # check for our permission
        manager = getSecurityManager()
        obj = self._object.unrestrictedTraverse(self.uid)
        if manager.checkPermission("View", obj):
            return False

        # search the catalog to see if we have permission with any of the children
        cat = ICatalogTool(obj)
        numInstances = cat.count('Products.ZenModel.DeviceOrganizer.DeviceOrganizer', self.uid)


        # if anything is returned we have view permissions on a child
        return not numInstances > 0


class StaleResultsException(Exception):
    """
    The hash check failed. Selections need to be refreshed.
    """


class SearchResults(object):

    def __init__(self, results, total, hash_, areBrains=True):
        self.results = results
        self.total = total
        self.hash_ = hash_
        self.areBrains = areBrains

    def __hash__(self):
        return self.hash_

    def __iter__(self):
        return self.results



class CountCache(PathIndexCache):
    def __init__(self, results, path, expires):
        PathIndexCache.__init__(self, (), results, (), path)
        self.expires = expires

    def insert(self, idx, results, relnames=None, treePrefix=None):
        unindex = None
        for brain in results:
            # Use the first brain to get a reference to the index, then reuse
            # that reference
            unindex = unindex or brain.global_catalog._catalog.indexes['path']._unindex
            path = brain.getPath()
            if treePrefix and not path.startswith(treePrefix):
                for p in unindex[brain.getRID()]:
                    if p.startswith(treePrefix):
                        path = p
                        break
            path = path.split('/', 3)[-1]
            for depth in xrange(path.count('/')+1):
                comp = idx.setdefault(path, IIBTree())
                comp[depth] = comp.get(depth, 0) + 1
                path = path.rsplit('/', 1)[0]

    def count(self, path, depth=None):
        path = path.split('/', 3)[-1]
        try:
            idx = self._instanceidx[path]
            depth = depth or max(idx.keys())
            return sum(idx[d] for d in xrange(depth+1) if d in idx.keys())
        except KeyError:
            return 0

    @property
    def expired(self):
        return time.time() >= self.expires


class CatalogTool(object):
    implements(ICatalogTool)

    def __init__(self, context):
        self.context = context
        self.model_catalog = IModelCatalogTool(self.context)

    def getBrain(self, path):
        return self.model_catalog.global_catalog.getBrain(path)

    def parents(self, path):
        return self.model_catalog.parents(path)

    def count(self, types=(), path=None, filterPermissions=True):
        return self.model_catalog.count(types=types, path=path, filterPermissions=filterPermissions)

    def search(self, types=(), start=0, limit=None, orderby=None,
               reverse=False, paths=(), depth=None, query=None,
               hashcheck=None, filterPermissions=True, globFilters=None):

        return self.model_catalog.global_catalog.search(types=types, start=start, limit=limit, orderby=orderby,
               reverse=reverse, paths=paths, depth=depth, query=query,
               hashcheck=hashcheck, filterPermissions=filterPermissions, globFilters=globFilters)

    def update(self, obj):
        self.model_catalog.update(obj)


class PermissionedCatalogTool(CatalogTool):
    """
    A specialized catalog tool used for searching the other
    catalogs that still have permissions but are not the global
    catalog
    """
    def __init__(self, context, catalog):
        super(PermissionedCatalogTool, self).__init__(context)
        self.catalog = catalog

    def _queryCatalog(self, types=(), orderby=None, reverse=False, paths=(),
                     depth=None, query=None, filterPermissions=True):
        # Identical to global catalog query, except without types
        query = self._buildQuery((), paths, depth, query, filterPermissions)
        sort = self._buildSort(orderby, reverse)
        args = (query, sort) if sort else (query, )

        # Get the brains
        result = self.catalog.evalAdvancedQuery(*args)
        return result
