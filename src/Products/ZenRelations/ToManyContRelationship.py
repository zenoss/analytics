##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """ToManyContRelationship
A to-many container relationship
"""

import logging
import sys

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from App.special_dtml import DTMLFile
from BTrees.OOBTree import OOBTree
from OFS.event import ObjectWillBeAddedEvent, ObjectWillBeRemovedEvent
from OFS.ObjectManager import checkValidId
from zope.container.contained import ObjectAddedEvent, ObjectRemovedEvent
from zope.event import notify

from Products.ZenUtils.tbdetail import log_tb
from Products.ZenUtils.Utils import unused

from .Exceptions import (
    ObjectNotFound,
    RelationshipExistsError,
    zenmarker,
)
from .ToManyRelationshipBase import ToManyRelationshipBase

log = logging.getLogger("zen.Relations")


def manage_addToManyContRelationship(context, id, REQUEST=None):
    """factory for ToManyRelationship"""
    rel = ToManyContRelationship(id)
    context._setObject(rel.id, rel)
    if REQUEST:
        REQUEST["RESPONSE"].redirect(
            context.absolute_url_path() + "/manage_main"
        )
    return rel.id


addToManyContRelationship = DTMLFile(
    "dtml/addToManyContRelationship", globals()
)


class ToManyContRelationship(ToManyRelationshipBase):
    """
    ToManyContRelationship is the ToMany side of a realtionship that
    contains its related objects (like the normal Zope ObjectManager)
    """

    meta_type = "ToManyContRelationship"

    security = ClassSecurityInfo()

    def __init__(self, id):
        """set our instance values"""
        self.id = id
        self._objects = OOBTree()

    def _safeOfObjects(self):
        """
        Try to safely return ZenPack objects rather than
        causing imports to fail.
        """
        objs = []
        for ob in self._objects.values():
            try:
                objs.append(ob.__of__(self))
            except AttributeError:
                log.info("Ignoring unresolvable object '%s'", ob)
        return objs

    def __call__(self):
        """when we are called return our related object in our aq context"""
        return self._safeOfObjects()

    def __getattr__(self, name):
        """look in the two object stores for related objects"""
        if "_objects" in self.__dict__:
            objects = self._objects
            if name in objects:
                return objects[name]
        raise AttributeError("Unable to find the attribute '%s'" % name)

    def __hasattr__(self, name):
        """check to see if we have an object by an id
        this will fail if passed a short id and object is stored
        with fullid (ie: it is related not contained)
        use hasobject to get around this issue"""
        return name in self._objects

    def hasobject(self, obj):
        "check to see if we have this object"
        return self._objects.get(obj.id) == obj

    def addRelation(self, obj):
        """Override base to run manage_afterAdd like ObjectManager"""
        if obj.getId() in self._objects:
            log.debug(
                "obj %s already exists on %s",
                obj.getPrimaryId(),
                self.getPrimaryId(),
            )

        notify(ObjectWillBeAddedEvent(obj, self, obj.getId()))
        ToManyRelationshipBase.addRelation(self, obj)
        obj = obj.__of__(self)
        o = self._getOb(obj.id)
        notify(ObjectAddedEvent(o, self, obj.getId()))

    def _setObject(self, id, object, roles=None, user=None, set_owner=1):
        """ObjectManager interface to add contained object."""
        unused(user, roles, set_owner)
        object.__primary_parent__ = aq_base(self)
        self.addRelation(object)
        return object.getId()

    def manage_afterAdd(self, item, container):
        # Don't do recursion anymore, a subscriber does that.
        pass

    manage_afterAdd.__five_method__ = True

    def manage_afterClone(self, item):
        # Don't do recursion anymore, a subscriber does that.
        pass

    manage_afterClone.__five_method__ = True

    def manage_beforeDelete(self, item, container):
        # Don't do recursion anymore, a subscriber does that.
        pass

    manage_beforeDelete.__five_method__ = True

    def _add(self, obj):
        """add an object to one side of a ToManyContRelationship."""
        id = obj.id
        if id in self._objects:
            raise RelationshipExistsError
        v = checkValidId(self, id)
        if v is not None:
            id = v
        self._objects[id] = aq_base(obj)
        obj = aq_base(obj).__of__(self)

    def _remove(self, obj=None, suppress_events=False):
        """remove object from our side of a relationship"""
        if obj:
            objs = [obj]
        else:
            objs = self.objectValuesAll()
        if not suppress_events:
            for robj in objs:
                notify(ObjectWillBeRemovedEvent(robj, self, robj.getId()))
        if obj:
            id = obj.id
            if id not in self._objects:
                raise ObjectNotFound(
                    "object %s not found on %s"
                    % (obj.getPrimaryId(), self.getPrimaryId())
                )
            del self._objects[id]
        else:
            self._objects = OOBTree()
            self.__primary_parent__._p_changed = True
        if not suppress_events:
            for robj in objs:
                notify(ObjectRemovedEvent(robj, self, robj.getId()))

    def _remoteRemove(self, obj=None):
        """remove an object from the far side of this relationship
        if no object is passed in remove all objects"""
        if obj:
            if obj.id not in self._objects:
                raise ObjectNotFound(
                    "object %s not found on %s"
                    % (obj.getPrimaryId(), self.getPrimaryId())
                )
            objs = [obj]
        else:
            objs = self.objectValuesAll()
        remoteName = self.remoteName()
        for obj in objs:
            rel = getattr(obj, remoteName)
            try:
                rel._remove(self.__primary_parent__)
            except ObjectNotFound:
                message = log_tb(sys.exc_info())
                log.error(
                    'Remote remove failed. Run "zenchkrels -r -x1". %s',
                    message,
                )
                continue

    def _getOb(self, id, default=zenmarker):
        """look up in our local store and wrap in our aq_chain"""
        if id in self._objects:
            return self._objects[id].__of__(self)
        elif default == zenmarker:
            raise AttributeError("Unable to find %s" % id)
        return default

    security.declareProtected("View", "objectIds")

    def objectIds(self, spec=None):
        """only return contained objects"""
        if spec:
            if isinstance(spec, basestring):
                spec = [spec]
            return [
                obj.id
                for obj in self._objects.values()
                if obj.meta_type in spec
            ]
        return [k for k in self._objects.keys()]

    objectIdsAll = objectIds

    security.declareProtected("View", "objectValues")

    def objectValues(self, spec=None):
        """override to only return owned objects for many to many rel"""
        if spec:
            if isinstance(spec, basestring):
                spec = [spec]
            return [
                ob.__of__(self)
                for ob in self._objects.values()
                if ob.meta_type in spec
            ]
        return self._safeOfObjects()

    security.declareProtected("View", "objectValuesAll")
    objectValuesAll = objectValues

    def objectValuesGen(self):
        """Generator that returns all related objects."""
        for obj in self._objects.values():
            try:
                yield obj.__of__(self)
            except Exception:
                # If the object does not have an `__of__` method, don't
                # trust that it has an `getPrimaryId` method.  So,
                # use `getPrimaryId` if it exists, otherwise, use the
                # type of the object itself.
                if hasattr(obj, "getPrimaryId"):
                    key = "primary-id"
                    value = obj.getPrimaryId()
                else:
                    # Getting the type of an object that's been wrapped
                    # in an aquisition wrapper isn't helpful, so unwrap
                    # it first, but don't trust that `aq_base` will
                    # succeed.
                    key = "type"
                    try:
                        value = type(aq_base(obj))
                    except Exception:
                        value = type(obj)
                log.exception("failed to wrap object  %s=%s", key, value)

    def objectItems(self, spec=None):
        """over ride to only return owned objects for many to many rel"""
        if spec:
            if isinstance(spec, basestring):
                spec = [spec]
            return [
                (key, value.__of__(self))
                for (key, value) in self._objects.items()
                if value.meta_type in spec
            ]
        return [
            (key, value.__of__(self)) for (key, value) in self._objects.items()
        ]

    objectItemsAll = objectItems

    # FIXME - need to make this work
    #    def all_meta_types(self, interfaces=None):
    #        mts = []
    #        for mt in ToManyRelationshipBase.all_meta_types(self, interfaces):
    #            if (mt.has_key('instance') and mt['instance']):
    #                for cl in self.sub_classes:
    #                    if checkClass(mt['instance'], cl):
    #                        mts.append(mt)
    #        return mts

    def _getCopy(self, container):
        """
        make new relation add copies of contained objs
        and refs if the relation is a many to many
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        rel = rel.__of__(container)
        norelcopy = getattr(self, "zNoRelationshipCopy", [])
        if self.id in norelcopy:
            return rel
        for oobj in self.objectValuesAll():
            cobj = oobj._getCopy(rel)
            rel._setObject(cobj.id, cobj)
        return rel

    def checkValidId(self, id):
        """
        Is this a valid id for this container?
        """
        try:
            checkValidId(self, id)
        except Exception:
            raise
        else:
            return True

    def exportXml(self, ofile, ignorerels=[]):
        """Return an xml representation of a ToManyContRelationship
        <tomanycont id='interfaces'>
            <object id='hme0'
                module='Products.Confmon.IpInterface' class='IpInterface'>
                <property></property> etc....
            </object>
        </tomanycont>
        """
        if self.countObjects() == 0:
            return
        ofile.write("<tomanycont id='%s'>\n" % self.id)
        for obj in self.objectValues():
            obj.exportXml(ofile, ignorerels)
        ofile.write("</tomanycont>\n")

    def checkRelation(self, repair=False):
        """Check to make sure that relationship bidirectionality is ok."""
        if len(self._objects):
            log.debug("checking relation: %s", self.id)
        else:
            return

        # look for objects that don't point back to us
        # or who should no longer exist in the database
        remoteName = self.remoteName()
        parentObject = self.getPrimaryParent()
        for obj in self._objects.values():
            if not hasattr(obj, remoteName):
                path = parentObject.getPrimaryUrlPath()
                if repair:
                    log.warn(
                        "Deleting %s object '%s' relation '%s' "
                        "(missing remote relation '%s')",
                        path,
                        obj,
                        self.id,
                        remoteName,
                    )
                    self._remove(obj, True)
                    continue
                else:
                    msg = (
                        "%s object '%s' relation '%s' missing remote "
                        "relation '%s'" % (path, obj, self.id, remoteName)
                    )
                    raise AttributeError(msg)

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


InitializeClass(ToManyContRelationship)


class ToManyContSublocations(object):
    """
    Adapter so the event dispatching can propagate to children.
    """

    def __init__(self, container):
        self.container = container

    def sublocations(self):
        return (ob for ob in self.container.objectValuesAll())
