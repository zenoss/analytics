##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """RelationshipBase

RelationshipBase is the base class for RelationshipManager
and ToManyRelationship.

"""

import logging

from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from zope.interface import implementer, Interface

from Products.ZenRelations.utils import importClass

from .Exceptions import (
    RelationshipExistsError,
    ZenRelationsError,
    ZenSchemaError,
)
from .PrimaryPathObjectManager import PrimaryPathManager

log = logging.getLogger("zen.Relations")


class IRelationship(Interface):
    """
    Marker interface.
    """


@implementer(IRelationship)
class RelationshipBase(PrimaryPathManager):
    """
    Abstract base class for all relationship classes.
    """

    _operation = -1  # if a Relationship's are only deleted

    def __call__(self):
        """Return the contents of this relation."""
        raise NotImplementedError

    def getId(self):
        return self.id

    def hasobject(self, obj):
        """Does this relationship relate to obj."""
        raise NotImplementedError

    def _add(self, obj):
        """Add object to local side of relationship."""
        raise NotImplementedError

    def _remove(self, obj=None, suppress_events=False):
        """
        Remove object from local side of relationship.
        If obj=None remove all object in the relationship
        """
        raise NotImplementedError

    def _remoteRemove(self, obj=None):
        """Remove obj form the remote side of this relationship."""
        raise NotImplementedError

    def addRelation(self, obj):
        """Form a bi-directional relation between self and obj."""
        if obj is None:
            raise ZenRelationsError("Can not add None to relation")
        if not isinstance(obj, self.remoteClass()):
            raise ZenSchemaError(
                "%s restricted to class %s. %s is class %s"
                % (
                    self.id,
                    self.remoteClass().__name__,
                    obj.id,
                    obj.__class__.__name__,
                )
            )
        try:
            self._add(obj)
            rname = self.remoteName()
            # make sure remote rel is on this obj
            getattr(aq_base(obj), rname)
            remoteRel = getattr(obj, self.remoteName())
            remoteRel._add(self.__primary_parent__)
        except RelationshipExistsError:
            log.debug(
                "obj %s already exists on %s",
                obj.getPrimaryId(),
                self.getPrimaryId(),
            )

    def removeRelation(self, obj=None, suppress_events=False):
        """remove an object from a relationship"""
        self._remoteRemove(obj)
        self._remove(obj, suppress_events=suppress_events)

    def remoteType(self):
        """Return the type of the remote end of our relationship."""
        schema = self.__primary_parent__.lookupSchema(self.id)
        return schema.remoteType

    def remoteTypeName(self):
        """Return the type of the remote end of our relationship."""
        schema = self.__primary_parent__.lookupSchema(self.id)
        return schema.remoteType.__name__

    def remoteClass(self):
        """Return the class at the remote end of our relationship."""
        classdef = getattr(aq_base(self), "_v_remoteClass", None)
        if not classdef:
            schema = self.__primary_parent__.lookupSchema(self.id)
            classdef = importClass(schema.remoteClass)
            self._v_remoteClass = classdef
        return classdef

    def remoteName(self):
        """Return the name at the remote end of our relationship."""
        schema = self.__primary_parent__.lookupSchema(self.id)
        return schema.remoteName

    def getPrimaryParent(self):
        """Return our parent object by our primary path"""
        return self.__primary_parent__.primaryAq()

    def getRelationshipManagerClass(self):
        """
        Return the local class of this relationship. For all relationshps
        this is the class of our __primary_parent___.
        """
        return self.__primary_parent__.__class__

    def cb_isCopyable(self):
        """Don't let relationships move off their managers"""
        return 0

    def cb_isMoveable(self):
        """Don't let relationships move off their managers"""
        return 0

    def checkRelation(self, repair=False):
        """Check to make sure that relationship bidirectionality is ok."""
        return


InitializeClass(RelationshipBase)
