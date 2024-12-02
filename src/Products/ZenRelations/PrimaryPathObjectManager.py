##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

import App.Undo

from AccessControl.Role import RoleManager
from Acquisition import Implicit, aq_base
from OFS.ObjectManager import ObjectManager
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2

from .RelCopySupport import RelCopyContainer
from .ZItem import ZItem

log = logging.getLogger("zen.PrimaryPathObjectManager")

_MARKER = object()


class PrimaryPathManager(ZItem, Implicit, RoleManager):
    def getPrimaryPath(self, fromNode=None):
        """
        Return the primary path of this object by following __primary_parent__
        """
        ppath = []
        obj = aq_base(self)
        while True:
            ppath.append(obj.id)
            parent = getattr(obj, "__primary_parent__", None)
            if parent is None:
                break
            obj = parent
        ppath.reverse()
        basepath = getattr(obj, "zPrimaryBasePath", [])
        for i in range(len(basepath) - 1, -1, -1):
            ppath.insert(0, basepath[i])
        try:
            idx = ppath.index(fromNode)
            ppath = ppath[idx + 1 :]
        except ValueError:
            pass
        return tuple(ppath)

    def getPrimaryId(self, fromNode=None):
        """Return the primary path in the form /zport/dmd/xyz"""
        pid = "/".join(self.getPrimaryPath(fromNode))
        if fromNode:
            pid = "/" + pid
        return pid

    def getPrimaryUrlPath(self, full=False):
        """Return the primary path as an absolute url"""
        objaq = self.primaryAq()
        if full:
            return objaq.absolute_url()
        return objaq.absolute_url_path()

    def primaryAq(self):
        """Return self with is acquisition path set to primary path"""
        parent = getattr(self, "__primary_parent__", _MARKER)
        if parent is _MARKER:
            # dmd is the only PrimaryPathManager with no __primary_parent__.
            # Need to go get zport in a safe way to be the acquisition parent.
            app = self.getPhysicalRoot()
            basepath = getattr(self, "zPrimaryBasePath", ())
            if basepath:
                # Hooray, we can get zport.
                zport = getattr(app, basepath[-1])
                return aq_base(self).__of__(zport)
            # No base path; probably in a test scenario. This is as far
            # as we can go, anyway. Just return self as the root.
            return aq_base(self)
        if parent is None:  # Deleted object
            raise KeyError(self.id)
        return aq_base(self).__of__(parent.primaryAq())

    def getPrimaryParent(self):
        """Return our parent object by our primary path"""
        return self.__primary_parent__.primaryAq()


class PrimaryPathObjectManager(
    RelCopyContainer,
    ObjectManager,
    PrimaryPathManager,
    App.Undo.UndoSupport,
):
    """PrimaryPathObjectManager with basic Zope persistent classes."""

    manage_options = (
        ObjectManager.manage_options
        + RoleManager.manage_options
        + ZItem.manage_options
    )

    def _setObject(self, id, obj, roles=None, user=None, set_owner=1):
        """Track __primary_parent__ when we are set into an object"""
        obj.__primary_parent__ = aq_base(self)
        return ObjectManager._setObject(self, id, obj, roles, user, set_owner)

    def _delObject(self, id, dp=1, suppress_events=False):
        """When deleted clear __primary_parent__."""
        obj = self._getOb(id, None)
        if obj is None:
            # Added this check because we are seeing stack traces in the UI.
            # We aren't 100% sure what is causing the object to disappear from
            # the ObjectManager. It could be that a different user had already
            # deleted it or that a single user had two brower tabs open.
            # Ian saw a case were the references on an object were wrong
            # (getPrimaryId pointed to the wrong location) but I'm not sure
            # that is what is causing this problem. -EAD
            log.warning(
                "Tried to delete object id '%s' but didn't find it on %s",
                id,
                self.getPrimaryId(),
            )
            return
        ObjectManager._delObject(self, id, dp, suppress_events)
        obj.__primary_parent__ = None


class PrimaryPathBTreeFolder2(BTreeFolder2):
    """
    BTreeFolder2 PrimaryPathObjectManager.
    """

    def _setObject(self, id, obj, roles=None, user=None, set_owner=1):
        """Track __primary_parent__ when we are set into an object"""
        obj.__primary_parent__ = aq_base(self)
        return ObjectManager._setObject(self, id, obj, roles, user, set_owner)

    def _delObject(self, id, dp=1, suppress_events=False):
        """When deleted clear __primary_parent__."""
        obj = self._getOb(id)
        ObjectManager._delObject(self, id, dp, suppress_events)
        obj.__primary_parent__ = None
