##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, division, print_function

import logging
import inspect
import six
import sys

from importlib import import_module
from time import time

from zope.event import notify

from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from Products.ZenUtils.Utils import NotFound

from .datamaputils import (
    _check_the_locks,
    _evaluate_legacy_directive,
    _object_changed,
    _objectmap_to_device_diff,
    _update_object,
)
from .events import DatamapUpdateEvent, DatamapAppliedEvent

log = logging.getLogger("zen.IncrementalDataMap")  # pragma: no mutate

_NOTSET = type("NotSet", (object,), {})()


class InvalidIncrementalDataMapError(Exception):
    pass


class IncrementalDataMap(object):

    _target = _NOTSET
    _parent = None
    _relationship = _NOTSET
    __diff = None
    __directive = None
    changed = False
    _logstr = None

    def __init__(self, base, object_map):
        self._base = base
        self.__original_object_map = object_map

        if not isinstance(object_map, ObjectMap):
            raise InvalidIncrementalDataMapError(
                "Expected ObjectMap, recieved: %s" % object_map
            )

        object_map = _evaluate_legacy_directive(object_map)

        self._process_objectmap(object_map)

        self.id = self._target_id

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.__dict__)

    def _process_objectmap(self, object_map):
        self._parent_id = getattr(object_map, "parentId", None)
        self.__target_id = getattr(object_map, "id", _NOTSET)
        self.path = getattr(object_map, "compname", None)
        self.__relname = getattr(object_map, "relname", _NOTSET)
        self.modname = getattr(object_map, "modname", None)
        self.classname = getattr(object_map, "classname", None)

        self._object_map = {
            k: v
            for k, v in object_map.iteritems()
            if k not in ["parentId", "relname", "id"]
        }

    @property
    def logstr(self):
        if not self._logstr:
            self._logstr = "[base={}, parent={}, target={}]".format(
                self._base, self._parent, self._target
            )
        return self._logstr

    def apply(self):
        self.start_time = time()
        self._directive_map[self.directive]()
        self.end_time = time()
        notify(DatamapAppliedEvent(self))

    @property
    def _directive_map(self):
        return {
            "add": self._add,
            "update": self._update,
            "remove": self._remove,
            "nochange": self._nochange,
            "rebuild": self._rebuild,
            "update_locked": self._nochange,
            "delete_locked": self._nochange,
        }

    @property
    def parent(self):
        if not self._parent:
            if self.path:
                # look up the specified component path
                try:
                    self._parent = self._base.getObjByPath(self.path)
                except NotFound:
                    self._parent = self._base
            else:
                # if compname is not specified, use the base device
                self._parent = self._base

        return self._parent

    @property
    def relname(self):
        try:
            if self.__relname is _NOTSET:
                self.__relname = self.path.split("/")[-2]
        except Exception:
            self.__relname = None

        return self.__relname

    @relname.setter
    def relname(self, value):
        self.__relname = value

    @property
    def _relname(self):
        """expose _relname for ADMReporter"""
        return self.relname

    @property
    def relationship(self):
        if self._relationship is _NOTSET:
            try:
                self._relationship = getattr(self.parent, self.relname)
            except TypeError:
                msg = "requires relationship, no relname given or found"
                six.reraise(
                    InvalidIncrementalDataMapError,
                    msg,
                    tb=sys.exc_info()[2],
                )

        return self._relationship

    @property
    def _target_id(self):
        if self.__target_id is _NOTSET:
            try:
                self.__target_id = self.path.split("/")[-1]
            except Exception:
                self.__target_id = None

        return self.__target_id

    @property
    def target(self):
        if self._target is _NOTSET:
            target = self.parent

            if self.relname:
                try:
                    target = self.relationship._getOb(self._target_id)
                except Exception:
                    log.debug(
                        "%s related object NOT FOUND",  # pragma: no mutate
                        self.logstr,
                    )
                    target = None

            self._target = target

        return self._target

    @target.setter
    def target(self, value):
        self._target = value

    @property
    def classname(self):
        if not self._classname:
            self._classname = self.modname.split(".")[-1]

        return self._classname

    @classname.setter
    def classname(self, value):
        self._classname = value

    @property
    def directive(self):
        if not self.__directive:
            legacy_directive = getattr(
                self.__original_object_map, "_directive", None
            )
            if legacy_directive:
                self.directive = legacy_directive
            elif self.target is None:
                self.directive = "add"
            elif _class_changed(self.modname, self.classname, self.target):
                self.directive = "rebuild"
            elif self._diff and self._valid_id():
                self.directive = "update"
            else:
                self.directive = "nochange"

        return self.__directive

    @directive.setter
    def directive(self, value):
        self.__directive = value
        _check_the_locks(self, self.target)

        # validate directive
        if self.__directive == "add":
            if not self.modname:
                raise InvalidIncrementalDataMapError(
                    "adding an object requires modname"  # pragma: no mutate
                )
            assert self.relationship  # relationship is required for add

    @property
    def _directive(self):
        """expose _directive for ADMReporter"""
        return self.directive

    @_directive.setter
    def _directive(self, value):
        self.directive = value

    def _valid_id(self):
        """assert that the ObjectMap's target ID matches the target's ID"""
        if not self._target_id:
            return True

        if self._target_id == self.target.id:
            return True

        log.warning(
            "%s ObjectMap.id does not match target.id, "
            "changes will not be applied",
            self.logstr,
        )
        return False

    @property
    def _diff(self):
        if self.__diff is None:
            self.__diff = _objectmap_to_device_diff(
                self._object_map, self.target
            )

        return self.__diff

    def iteritems(self):
        return self._object_map.iteritems()

    def _add(self):
        """Add the target device to the parent relationship"""
        changed = False
        self._target = next(
            (
                obj
                for objId, obj in self.relationship.objectItemsAll()
                if objId == self._target_id
            ),
            _NOTSET,
        )
        if self._target is _NOTSET:
            changed = True
            self._create_target()
            self._add_target_to_relationship()
            self._target = self.relationship._getOb(self._target_id)

        changed |= _update_object(self._target, self._diff)

        if changed:
            _object_changed(self._target)
            notify(
                DatamapUpdateEvent(
                    self._base.dmd, self.__original_object_map, self._target
                )
            )
        self.changed = changed

    def _update(self):
        """Update the target object using diff"""
        changed = _update_object(self.target, self._diff)

        if changed:
            _object_changed(self.target)
            notify(
                DatamapUpdateEvent(
                    self._base.dmd, self.__original_object_map, self.target
                )
            )

        self.changed = changed

    def _remove(self):
        """Remove the target object from the relationship"""
        if not self.target or not self.relname:
            self.changed = False
            return

        try:
            self.parent.removeRelation(self.relname, self.target)
            self.changed = True
        except AttributeError:
            self.changed = False

    def _create_target(self):
        """create a new zodb object from the object map we were given"""
        mod = import_module(self.modname)
        constructor = getattr(mod, self.classname)
        self._target = constructor(self._target_id)

    def _add_target_to_relationship(self):
        if self.relationship.hasobject(self.target):
            return

        log.debug(
            "%s add related object: "  # pragma: no mutate
            "parent=%s, relationship=%s, obj=%s",  # pragma: no mutate
            self.logstr,
            self.parent.id,
            self.relname,
            self._target_id,
        )
        # either use device.addRelation(relname, object_map)
        # or create the object, then relationship._setObject(obj.id, obj)
        self.relationship._setObject(self._target_id, self.target)

        if not isinstance(self.relationship, ToManyContRelationship):
            from zope.container.contained import ObjectMovedEvent

            notify(
                ObjectMovedEvent(
                    self.target,
                    self.relationship,
                    self.id,
                    self.relationship,
                    self.id,
                )
            )

    def _rebuild(self):
        log.debug(
            "%s _rebuild: parent=%s, "  # pragma: no mutate
            "relationship=%s, target=%s",  # pragma: no mutate
            self.logstr,
            self.parent,
            self.relname,
            self.target,
        )
        self._remove()
        self._add()
        self.changed = True

    def _nochange(self):
        """make no change if the directive is nochange"""
        log.debug(
            "%s object unchanged: "  # pragma: no mutate
            "parent=%s, relationship=%s, obj=%s",  # pragma: no mutate
            self.logstr,
            self.parent.id,
            self.relname,
            self._target_id,
        )


def _class_changed(modname, classname, target):
    """Handle the possibility of objects changing class by recreating them.
    No classname indicates no change
    """
    if not classname:
        return False

    existing_modname, existing_classname = "", ""
    try:
        existing_modname = inspect.getmodule(target).__name__
        existing_classname = target.__class__.__name__
    except Exception:
        pass

    # object class has not changed
    if modname == existing_modname and classname == existing_classname:
        log.debug("_om_class_changed: object map matches")  # pragma: no mutate
        return False

    log.debug(
        "_om_class_changed: object_map class changed"  # pragma: no mutate
    )
    return True
