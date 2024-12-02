##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from App.special_dtml import DTMLFile
from persistent.list import PersistentList
from zExceptions import NotFound

from Products.ZenUtils.Utils import getObjByPath, unused

from .Exceptions import ObjectNotFound, RelationshipExistsError, zenmarker
from .ToManyRelationshipBase import ToManyRelationshipBase


log = logging.getLogger("zen.Relations")


def manage_addToManyRelationship(context, id, REQUEST=None):
    """factory for ToManyRelationship"""
    rel = ToManyRelationship(id)
    context._setObject(rel.id, rel)
    if REQUEST:
        REQUEST["RESPONSE"].redirect(
            context.absolute_url_path() + "/manage_main"
        )
    return rel.id


addToManyRelationship = DTMLFile("dtml/addToManyRelationship", globals())


class ToManyRelationship(ToManyRelationshipBase):
    """
    ToManyRelationship manages the ToMany side of a bi-directional relation
    between to objects.  It does not return values for any of the object*
    calls defined on ObjectManager so that Zope can still work with its
    containment assumptions.  It provides object*All calles that return
    its object in the same way that ObjectManager does.

    Related references are maintained in a list.
    """

    __pychecker__ = "no-override"

    meta_type = "ToManyRelationship"

    security = ClassSecurityInfo()

    def __init__(self, id):
        """ToManyRelationships use an array to store related objects"""
        self.id = id
        self._objects = PersistentList()

    def __call__(self):
        """when we are called return our related object in our aq context"""
        return self.objectValuesAll()

    def hasobject(self, obj):
        "check to see if we have this object"
        try:
            idx = self._objects.index(obj)
            return self._objects[idx]
        except ValueError:
            return None

    def manage_pasteObjects(self, cb_copy_data=None, REQUEST=None):
        """ToManyRelationships link instead of pasting"""
        return self.manage_linkObjects(
            cb_copy_data=cb_copy_data, REQUEST=REQUEST
        )

    def _add(self, obj):
        """add an object to one side of this toMany relationship"""
        if obj in self._objects:
            raise RelationshipExistsError
        self._objects.append(aq_base(obj))
        self.__primary_parent__._p_changed = True

    def _remove(self, obj=None, suppress_events=False):
        """remove object from our side of a relationship"""
        if obj:
            try:
                self._objects.remove(obj)
            except ValueError:
                raise ObjectNotFound(
                    "object %s not found on relation %s"
                    % (obj.getPrimaryId(), self.getPrimaryId())
                )
        else:
            self._objects = PersistentList()
        self.__primary_parent__._p_changed = True

    def _remoteRemove(self, obj=None):
        """remove an object from the far side of this relationship
        if no object is passed in remove all objects"""
        if obj:
            if obj not in self._objects:
                raise ObjectNotFound(
                    "object %s not found on relation %s"
                    % (obj.getPrimaryId(), self.getPrimaryId())
                )
            objs = [obj]
        else:
            objs = self.objectValuesAll()
        remoteName = self.remoteName()
        for obj in objs:
            remoteRel = getattr(obj, remoteName)
            try:
                remoteRel._remove(self.__primary_parent__)
            except ObjectNotFound:
                log.debug(
                    "remote relation already removed  "
                    "obj=%s remote-relation=%s",
                    self.__primary_parent__.getPrimaryId(),
                    remoteRel.getPrimaryId(),
                )

    def _setObject(self, id, object, roles=None, user=None, set_owner=1):
        """Set and object onto a ToMany by calling addRelation"""
        unused(id, roles, user, set_owner)
        self.addRelation(object)

    def _delObject(self, id, dp=1, suppress_events=False):
        """
        Delete object by its absolute id (ie /zport/dmd/bla/bla)
        (this is sent out in the object*All API)
        """
        obj = getObjByPath(self, id)
        self.removeRelation(obj, suppress_events=suppress_events)

    def _getOb(self, id, default=zenmarker):
        """
        Return object based on its primaryId. plain id will not work!!!
        """
        objs = filter(lambda x: x.getPrimaryId() == id, self._objects)
        if len(objs) == 1:
            return objs[0].__of__(self)
        if default != zenmarker:
            return default
        raise AttributeError(id)

    def objectIdsAll(self):
        """
        Return object ids as their absolute primaryId.
        """
        return [obj.getPrimaryId() for obj in self._objects]

    def objectIds(self, spec=None):
        """
        ToManyRelationship doesn't publish objectIds to prevent
        zope recursion problems.
        """
        unused(spec)
        return []

    security.declareProtected("View", "objectValuesAll")

    def objectValuesAll(self):
        """return all related object values"""
        return list(self.objectValuesGen())

    def objectValuesGen(self):
        """Generator that returns all related objects."""
        return (obj.__of__(self) for obj in self._objects)

    def objectValues(self, spec=None):
        """
        ToManyRelationship doesn't publish objectValues to prevent
        zope recursion problems.
        """
        unused(spec)
        return []

    def objectItemsAll(self):
        """
        Return object items where key is primaryId.
        """
        return [(obj.getPrimaryId(), obj) for obj in self._objects]

    def objectItems(self, spec=None):
        """
        ToManyRelationship doesn't publish objectItems to prevent
        zope recursion problems.
        """
        unused(spec)
        return []

    def _getCopy(self, container):
        """
        create copy and link remote objects if remote side is TO_MANY
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        rel = rel.__of__(container)
        norelcopy = getattr(self, "zNoRelationshipCopy", [])
        if self.id in norelcopy:
            return rel
        if self.remoteTypeName() == "ToMany":
            for robj in self.objectValuesAll():
                rel.addRelation(robj)
        return rel

    def exportXml(self, ofile, ignorerels=()):
        """Return an xml representation of a ToManyRelationship
        <tomany id='interfaces'>
            <link>/Systems/OOL/Mail</link>
        </tomany>
        """
        if self.countObjects() == 0:
            return
        ofile.write("<tomany id='%s'>\n" % self.id)
        for id in self.objectIdsAll():
            ofile.write("<link objid='%s'/>\n" % id)
        ofile.write("</tomany>\n")

    def all_meta_types(self, interfaces=None):
        """Return empty list not allowed to add objects to a ToManyRelation"""
        return []

    def convertToPersistentList(self):
        self._objects = PersistentList(self._objects)

    def checkObjectRelation(self, obj, remoteName, parentObject, repair):
        deleted = False
        try:
            ppath = obj.getPrimaryPath()
            getObjByPath(self, ppath)
        except (KeyError, NotFound):
            log.error(
                "object %s in relation %s has been deleted "
                "from its primary path",
                obj.getPrimaryId(),
                self.getPrimaryId(),
            )
            if repair:
                log.warn(
                    "removing object %s from relation %s",
                    obj.getPrimaryId(),
                    self.getPrimaryId(),
                )
                self._objects.remove(obj)
                self.__primary_parent__._p_changed = True
                deleted = True

        if not deleted:
            rrel = getattr(obj, remoteName)
            if not rrel.hasobject(parentObject):
                log.error(
                    "remote relation %s doesn't point back to %s",
                    rrel.getPrimaryId(),
                    self.getPrimaryId(),
                )
                if repair:
                    log.warn(
                        "reconnecting relation %s to relation %s",
                        rrel.getPrimaryId(),
                        self.getPrimaryId(),
                    )
                    rrel._add(parentObject)
        return deleted

    def checkRelation(self, repair=False):
        """Check to make sure that relationship bidirectionality is ok."""
        if len(self._objects):
            log.debug("checking relation: %s", self.id)

        # look for objects that don't point back to us
        # or who should no longer exist in the database
        rname = self.remoteName()
        parobj = self.getPrimaryParent()
        for obj in self._objects:
            self.checkObjectRelation(obj, rname, parobj, repair)

        # find duplicate objects
        keycount = {}
        for obj in self._objects:
            key = obj.getPrimaryId()
            c = keycount.setdefault(key, 0)
            c += 1
            keycount[key] = c
        # Remove duplicate objects or objects that don't exist
        for key, val in keycount.items():
            if val > 1:
                log.critical(
                    "obj:%s rel:%s dup found obj:%s count:%s",
                    self.getPrimaryId(),
                    self.id,
                    key,
                    val,
                )
                if repair:
                    log.critical("repair key %s", key)
                    self._objects = [
                        o for o in self._objects if o.getPrimaryId() != key
                    ]
                    try:
                        obj = self.getObjByPath(key)
                        self._objects.append(obj)
                    except KeyError:
                        log.critical("obj %s not found in database", key)


InitializeClass(ToManyRelationship)
