##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """ToManyRelationshipBase
Base class for 1:n relations
"""

import logging

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from App.Management import Tabs
from App.special_dtml import DTMLFile

from Products.ZenUtils.deprecated import deprecated
from Products.ZenUtils.Utils import unused

from .RelationshipBase import RelationshipBase
from .RelCopySupport import RelCopyContainer
from .Exceptions import zenmarker

log = logging.getLogger("zen.ToManyRelationshipBase")


class ToManyRelationshipBase(RelCopyContainer, RelationshipBase):
    """
    Abstract base class for all ToMany relationships.
    """

    manage_options = (
        {
            "action": "manage_main",
            "help": ("OFSP", "ObjectManager_Contents.stx"),
            "label": "Contents",
        },
    )

    security = ClassSecurityInfo()

    manage_main = DTMLFile("dtml/ToManyRelationshipMain", globals())

    _operation = -1  # if a Relationship's are only deleted

    @deprecated
    def setCount(self):
        # It appeared that there is a mysterious issue with count syncing in
        # some cases e.g. ZEN-27668 after discussion with Ian decided to
        # remove it as it is redundant.
        pass

    def countObjects(self):
        """Return the number of objects in this relationship"""
        return len(self._objects)

    def findObjectsById(self, partid):
        """Return a list of objects by running find on their id"""
        objects = []
        for id, obj in self.objectItemsAll():
            if id.find(partid) > -1:
                objects.append(obj)
        return objects

    def _delObject(self, id, dp=1, suppress_events=False):
        """Emulate ObjectManager deletetion."""
        unused(dp)
        obj = self._getOb(id, False)
        if not obj:
            log.warning(
                "Tried to delete object id '%s' but didn't find it on %s",
                id,
                self.getPrimaryId(),
            )
            return
        self.removeRelation(obj, suppress_events)
        obj.__primary_parent__ = None

    def _setOb(self, id, obj):
        """don't use attributes in relations"""
        unused(id)
        unused(obj)
        if True:
            raise NotImplementedError

    def _delOb(self, id):
        """don't use attributes in relations"""
        if True:
            raise NotImplementedError

    def _getOb(self, id, default=zenmarker):
        """
        Return object by id if it exists on this relationship.
        If it doesn't exist return default or if default is not set
        raise AttributeError
        """
        unused(default)
        if True:
            raise NotImplementedError

    def manage_workspace(self, REQUEST):
        """if this has been called on us return our workspace
        if not redirect to the workspace of a related object"""
        id = REQUEST["URL"].split("/")[-2]
        if id == self.id:
            Tabs.manage_workspace(self, REQUEST)
        else:
            obj = self._getOb(self, id)
            from zExceptions import Redirect

            raise Redirect((obj.getPrimaryUrlPath() + "/manage_workspace"))


InitializeClass(ToManyRelationshipBase)
