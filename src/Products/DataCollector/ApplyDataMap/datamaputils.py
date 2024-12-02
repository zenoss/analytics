##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import sys

from zope.event import notify

from Products.DataCollector.plugins.DataMaps import MultiArgs
from Products.Zuul.catalog.events import IndexingEvent

log = logging.getLogger("zen.ApplyDataMap.datamaputils")

MISSINGNO = object()


def isSameData(x, y):
    """
    A more comprehensive check to see if existing model data is the same as
    newly modeled data. The primary focus is comparing unsorted lists of
    dictionaries.
    """
    if isinstance(x, (tuple, list)) and isinstance(y, (tuple, list)):
        if (
            x
            and y
            and all(isinstance(i, dict) for i in x)
            and all(isinstance(i, dict) for i in y)
        ):
            x = set(tuple(sorted(d.items())) for d in x)
            y = set(tuple(sorted(d.items())) for d in y)
        else:
            return sorted(x) == sorted(y)

    return x == y


def _check_the_locks(datamap, device):
    if datamap._directive:
        if datamap._directive in (
            "update",
            "rebuild",
            "remove",
        ) and _locked_from_updates(device):
            datamap._directive = "update_locked"
        elif datamap._directive in (
            "rebuild",
            "remove",
        ) and _locked_from_deletion(device):
            datamap._directive = "delete_locked"


def _locked_from_updates(obj):
    try:
        if obj.isLockedFromUpdates():
            return True
    except AttributeError:
        log.warn("_locked_from_updates: object is not lockable")
    return False


def _locked_from_deletion(obj):
    try:
        if obj.isLockedFromDeletion():
            return True
    except AttributeError:
        log.warn("_locked_from_deletion: object is not lockable")
    return False


def _evaluate_legacy_directive(datamap):
    """Translate legacy directives"""
    for attr, directive in directive_map.items():
        flag = getattr(datamap, attr, None)
        if flag is None:
            continue

        # .-----------------------------------------------.
        # |  _add  | Device Exists | Device Doesn't Exist |
        # |--------+---------------+----------------------|
        # | True   | Update device | Add device           |
        # | False  | Update device | Ignore datamap       |
        # `-----------------------------------------------'
        # Note: if there are no differences between the device
        # and the datamap, then applyDataMap should return False
        # to indicate no changes.

        if directive == "add" and flag is False:
            datamap._directive = "update"
        else:
            datamap._directive = directive if flag else "nochange"

        delattr(datamap, attr)

    return datamap


directive_map = {
    "_add": "add",
    "remove": "remove",
    "_remove": "remove",
    "_update": "update",
    "_rebuild": "rebuild",
    "_nochange": "nochange",
}


def _objectmap_to_device_diff(object_map, obj):
    """given an ObjectMap and Object
    returns a dict of attribute: decoded value
    from the ObjectMap that do not match the Object
    """
    diff = (
        _attribute_diff(obj, attr, value)
        for attr, value in object_map.iteritems()
    )
    diff = filter(None, diff)
    return {k: v for k, v in diff}


def _attribute_diff(obj, attr, value):
    """Return the attribute, and decoded value if they differ"""
    value_prime = _get_attr_value(obj, attr)
    value = _sanitize_value(value, obj)

    if not isSameData(value, value_prime):
        return (attr, value)
    else:
        return None


def _get_attr_value(obj, attr):
    if attr.startswith("set"):
        try:
            getter = getattr(obj, "get" + attr[3:])
            value = getter()
        except AttributeError:
            log.warn(
                "getter method not found: object=%s, attribute=%s",
                obj.id,
                attr,
            )
            return MISSINGNO
    else:
        value = getattr(obj, attr, MISSINGNO)

    return _sanitize_value(value, obj)


def _sanitize_value(value, obj):
    if isinstance(value, basestring):
        try:
            return _decode_value(value, obj)
        except UnicodeDecodeError:
            # We don't know what to do with this, so don't set the value
            log.exception(
                "unable to decode value  value=%s obj=%s",
                value,
                obj,
            )
            raise

    if isinstance(value, MultiArgs):
        value = value.args

    return value


def _decode_value(value, obj):
    #   This looks confusing, and it is. The scenario is:
    #   A collector gathers some data as a raw byte stream,
    #   but really it has a specific encoding specified by
    #   the zCollectorDecoding zProperty. Say, latin-1 or
    #   utf-16, etc. We need to decode that byte stream to get
    #   back a UnicodeString object. But, this version of Zope
    #   doesn't like UnicodeString objects for a variety of
    #   fields, such as object ids, so we then need to convert
    #   that UnicodeString back into a regular string of bytes,
    #   and for that we use the system default encoding, which
    #   is now utf-8.

    try:
        codec = obj.zCollectorDecoding
        if not codec:
            codec = sys.getdefaultencoding()
    except AttributeError:
        codec = sys.getdefaultencoding()

    try:
        value = value.decode(codec)
    except UnicodeDecodeError as ex:
        value = value.decode(codec, errors="ignore")
        log.warn(
            "Unable to decode string using codec '%s'.  "
            "Please set zCollectorDecoding to the correct codec. "
            "Using a modified string to avoid errors.  "
            "object=%r modified-value='%s' error=%s",
            codec,
            obj,
            value,
            ex,
        )

    return value.encode(sys.getdefaultencoding())


def _update_object(obj, diff):
    """Given an object map, with a _diff containing sanitized attributes
    update the object
    """
    log.debug("_update_object: obj=%s, diff=%s", obj, diff)

    if not diff:
        return False

    changed = False

    for attrname, value in diff.items():
        attr = getattr(obj, attrname, MISSINGNO)
        if attr is MISSINGNO:
            continue
        elif callable(attr):
            changed = _update_callable_attribute(attr, value)
        else:
            if attr != value:
                setattr(obj, attrname, value)
                changed = True

    return changed


def _update_callable_attribute(attr, value):
    try:
        try:
            attr(*value) if isinstance(value, tuple) else attr(value)
        except (TypeError, ValueError):
            # This is to handle legacy zenpacks that use the signature
            # pattern:
            #     def func(*args):
            #         (arg1, arg2, ...) = args[0]
            attr(*(value,))
        return True
    except Exception:
        # We log the traceback because we want incorrectly defined
        # datamaps to stand out.
        log.exception(
            "Failed to set '%s.%s' to the value '%s'",
            attr.__module__,
            attr.__name__,
            value,
        )
        return False


def _object_changed(obj):
    try:
        obj.index_object()
    except AttributeError:
        pass

    notify(IndexingEvent(obj))

    obj.setLastChange()
