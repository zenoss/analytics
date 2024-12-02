##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from base64 import b64encode

from mock import Mock, sentinel, patch

from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.ZenModel.Device import Device

from ..datamaputils import (
    isSameData,
    log,
    MISSINGNO,
    MultiArgs,
    _check_the_locks,
    _locked_from_updates,
    _locked_from_deletion,
    _evaluate_legacy_directive,
    _objectmap_to_device_diff,
    _attribute_diff,
    _sanitize_value,
    _get_attr_value,
    _update_object,
    _update_callable_attribute,
)
from .utils import BaseTestCase

log.setLevel("DEBUG")

PATH = {"src": "Products.DataCollector.ApplyDataMap.datamaputils"}


class TestisSameData(BaseTestCase):
    def test_isSameData(t):
        ret = isSameData("a", "a")
        t.assertTrue(ret)

    # compare unsorted lists of dictionaries
    def test_unsorted_lists_of_dicts_match(t):
        a = [{"a": 1, "b": 2}, {"c": 3}, {"d": 4}]
        b = [{"d": 4}, {"c": 3}, {"b": 2, "a": 1}]
        t.assertTrue(isSameData(a, b))

    def test_unsorted_lists_of_dicts_differ(t):
        a = [{"a": 1, "b": 2}, {"c": 3}, {"d": 4}]
        c = [{"d": 4}]
        t.assertFalse(isSameData(a, c))

    def test_unsorted_tuple_of_dicts_match(t):
        a = ({"a": 1, "b": 2}, {"c": 3}, {"d": 4})
        b = ({"d": 4}, {"c": 3}, {"b": 2, "a": 1})
        t.assertTrue(isSameData(a, b))

    def test_unsorted_tuple_of_dicts_differ(t):
        a = ({"a": 1, "b": 2}, {"c": 3}, {"d": 4})
        c = ({"d": 4},)
        t.assertFalse(isSameData(a, c))

    def test_tuples_match(t):
        a = (("a", 1, "b", 2), ("c", 3), ("d", 4))
        b = (("d", 4), ("c", 3), ("a", 1, "b", 2))
        t.assertTrue(isSameData(a, b))

    def test_tuples_differ(t):
        a = (("a", 1, "b", 2), ("c", 3), ("d", 4))
        b = (("d", 4), ("c", 3), ("x", 10, "y", 20))
        t.assertFalse(isSameData(a, b))

    def test_type_mismatch(t):
        a, c = 555, ("x", "y")
        t.assertFalse(isSameData(a, c))


class GetSetObject:
    def __init__(self):
        self.Attr = sentinel.original

    def setAttr(self, value):
        self.Attr = value

    def getAttr(self):
        return self.Attr


class TestCheckTheLocks(BaseTestCase):
    def setUp(t):
        super(TestCheckTheLocks, t).setUp()
        t.datamap = Mock(name="datamap")
        t.device = Mock(name="device")
        t.device.isLockedFromUpdates.return_value = False
        t.device.isLockedFromDeletion.return_value = False

    def test_update_update_locked(t):
        t.datamap._directive = "update"
        t.device.isLockedFromUpdates.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, "update_locked")

    def test_update_update_unlocked(t):
        t.datamap._directive = "update"
        t.device.isLockedFromUpdates.return_value = False
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, "update")

    def test_rebuild_update_locked(t):
        t.datamap._directive = "rebuild"
        t.device.isLockedFromUpdates.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, "update_locked")

    def test_remove_update_locked(t):
        t.datamap._directive = "remove"
        t.device.isLockedFromUpdates.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, "update_locked")

    def test_rebuild_delete_locked(t):
        t.datamap._directive = "remove"
        t.device.isLockedFromDeletion.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, "delete_locked")

    def test_rebuild_delete_unlocked(t):
        t.datamap._directive = "remove"
        t.device.isLockedFromDeletion.return_value = False
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, "remove")

    def test_remove_delete_locked(t):
        t.datamap._directive = "rebuild"
        t.device.isLockedFromDeletion.return_value = True
        _check_the_locks(t.datamap, t.device)
        t.assertEqual(t.datamap._directive, "delete_locked")


class TestLockedFromUpdates(BaseTestCase):
    def test_locked(t):
        obj = Mock(spec=["isLockedFromUpdates"])
        obj.isLockedFromUpdates.return_value = True
        ret = _locked_from_updates(obj)
        t.assertEqual(ret, True)

    def test_unlocked(t):
        obj = Mock(spec=["isLockedFromUpdates"])
        obj.isLockedFromUpdates.return_value = False
        ret = _locked_from_updates(obj)
        t.assertEqual(ret, False)

    def test_not_lockable(t):
        """if isLockedFromUpdates is not defined, it cannot be locked"""
        obj = Mock(spec=[])
        ret = _locked_from_updates(obj)
        t.assertEqual(ret, False)


class TestLockedFromDeletion(BaseTestCase):
    def test_locked(t):
        obj = Mock(spec=["isLockedFromDeletion"])
        obj.isLockedFromDeletion.return_value = True
        ret = _locked_from_deletion(obj)
        t.assertEqual(ret, True)

    def test_unlocked(t):
        obj = Mock(spec=["isLockedFromDeletion"])
        obj.isLockedFromDeletion.return_value = False
        ret = _locked_from_deletion(obj)
        t.assertEqual(ret, False)

    def test_not_lockable(t):
        """if isLockedFromDeletion is not defined, it cannot be locked"""
        obj = Mock(spec=[])
        ret = _locked_from_deletion(obj)
        t.assertEqual(ret, False)


class TestEvaluateLegacyDirective(BaseTestCase):
    def setUp(t):
        super(TestEvaluateLegacyDirective, t).setUp()
        t.object_map = ObjectMap()

    def test_legacy__add_false_flag(t):
        t.object_map._add = False
        ret = _evaluate_legacy_directive(t.object_map)
        t.assertEqual(ret._directive, "update")
        t.assertEqual(t.object_map._directive, "update")

    def test_legacy__add_flag(t):
        t.object_map._add = True
        ret = _evaluate_legacy_directive(t.object_map)
        t.assertEqual(ret._directive, "add")
        t.assertEqual(t.object_map._directive, "add")

    def test_legacy_remove_flag(t):
        t.object_map.remove = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, "remove")

    def test_legacy__remove_flag(t):
        t.object_map._remove = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, "remove")

    def test_legacy__update_flag(t):
        t.object_map._update = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, "update")

    def test_legacy__rebuild_flag(t):
        t.object_map._rebuild = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, "rebuild")

    def test_legacy__nochange_flag(t):
        t.object_map._nochange = True
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, "nochange")

    def test_legacy_false_nochange(t):
        t.object_map._update = False
        _evaluate_legacy_directive(t.object_map)
        t.assertEqual(t.object_map._directive, "nochange")


class TestObjectMapToDeviceDiff(BaseTestCase):
    def test_no_change(t):
        """Unchanged objects return an empty dict"""
        object_map = ObjectMap(
            data={
                "id": "objectid",
                "_underbar_are_ignored": True,
                "attr_a": "attribute a",
                "attr_b": sentinel.attr_b,
            }
        )
        device = Device(object_map.id)
        device.attr_a = "attribute a"
        device.attr_b = sentinel.attr_b
        device.missing_from_object_map = "not_checked_by_diff"

        ret = _objectmap_to_device_diff(object_map, device)
        t.assertEqual(ret, {})
        t.assertFalse(ret)

    def test_changed(t):
        """changed objects
        return a dict of the attribute name and sanitized value
        Including any new values added by the map
        """
        object_map = ObjectMap(
            data={
                "id": "objectid",
                "attr_a": "new value",
                "attr_b": sentinel.attr_b,
                "attr_c": sentinel.new_attr_c,
            }
        )
        device = Device(object_map.id)
        device.attr_a = "attribute a"
        device.attr_b = sentinel.attr_b

        ret = _objectmap_to_device_diff(object_map, device)

        t.assertEqual(
            ret, {"attr_a": "new value", "attr_c": sentinel.new_attr_c}
        )
        t.assertTrue(ret)

    def test_object_missing_attr(t):
        pass

    def test_callable_attribute_changed(t):
        obj = GetSetObject()
        object_map = ObjectMap(data={"setAttr": sentinel.new})
        ret = _objectmap_to_device_diff(object_map, obj)
        t.assertEqual(ret, {"setAttr": sentinel.new})

    def test_callable_attribute_unchanged(t):
        obj = GetSetObject()
        object_map = ObjectMap(data={"setAttr": sentinel.original})
        ret = _objectmap_to_device_diff(object_map, obj)
        t.assertEqual(ret, {})

    def test_multiargs_attribute_changed(t):
        value = MultiArgs(sentinel.a, ["a", "b"], {"a": 1})
        obj = ObjectMap(data={"id": "objectid", "attr_a": value})
        obj = Device("objectid")
        obj.attr_a = MultiArgs(sentinel.a, ["a", "b"], {"a": 1})
        new_value = MultiArgs(sentinel.a, ["a", "b"], {"a": 1, "b": 2})
        object_map = ObjectMap(data={"id": "objectid", "attr_a": new_value})

        ret = _objectmap_to_device_diff(object_map, obj)
        t.assertEqual(ret, {"attr_a": new_value.args})

    def test_multiargs_attribute_unchanged(t):
        value = MultiArgs(sentinel.a, ["a", "b"], {"a": 1})
        obj = Device("objectid")
        obj.attr_a = value
        object_map = ObjectMap(data={"id": "objectid", "attr_a": value})

        ret = _objectmap_to_device_diff(object_map, obj)
        t.assertEqual(ret, {})

    def test_encoding(t):
        enc_maps = {
            "ascii": ObjectMap(
                {"a": "abcdefg", "b": "hijklmn", "c": "opqrstu"}
            ),
            "utf-8": ObjectMap(
                {
                    "a": u"\xe0".encode("utf-8"),
                    "b": u"\xe0".encode("utf-8"),
                    "c": u"\xe0".encode("utf-8"),
                }
            ),
            "latin-1": ObjectMap(
                {
                    "a": u"\xe0".encode("latin-1"),
                    "b": u"\xe0".encode("latin-1"),
                    "c": u"\xe0".encode("latin-1"),
                }
            ),
            "utf-16": ObjectMap(
                {
                    "a": u"\xff\xfeabcdef".encode("utf-16"),
                    "b": u"\xff\xfexyzwow".encode("utf-16"),
                    # (water, z, G clef), UTF-16 encoded,
                    # little-endian with BOM
                    "c": r"\xff\xfe\x34\x6c\x7a\x00\x34\xd8\x13\xdd",
                }
            ),
        }

        for enc, objectmap in enc_maps.items():
            obj = Device("oid")
            obj.a, obj.b, obj.c = None, None, None
            obj.zCollectorDecoding = enc
            diff = _objectmap_to_device_diff(objectmap, obj)
            for key, val in diff.items():
                t.assertEqual(val, getattr(objectmap, key).decode(enc))


class TestAttributeDiff(BaseTestCase):
    def test_changed(t):
        obj = Mock(name="object")
        obj.attr = sentinel.original
        ret = _attribute_diff(obj, "attr", sentinel.new)
        t.assertEqual(ret, ("attr", sentinel.new))
        t.assertTrue(ret)

    def test_unchanged(t):
        obj = Mock(name="object")
        obj.attr = sentinel.original
        ret = _attribute_diff(obj, "attr", sentinel.original)
        t.assertEqual(ret, None)

    def test_callable_changed(t):
        obj = GetSetObject()
        ret = _attribute_diff(obj, "setAttr", sentinel.new)
        t.assertEqual(ret, ("setAttr", sentinel.new))

    def test_callable_unchanged(t):
        obj = GetSetObject()
        ret = _attribute_diff(obj, "setAttr", sentinel.original)
        t.assertEqual(ret, None)

    def test_multiargs_changed(t):
        obj = Device("objectid")
        value = MultiArgs(sentinel.a, ["a", "b"], {"a": 1})
        obj.attr_a = value
        new_value = MultiArgs(sentinel.a)
        ret = _attribute_diff(obj, "attr_a", new_value)
        t.assertTupleEqual(ret, ("attr_a", new_value.args))

    def test_multiargs_unchanged(t):
        obj = Device("objectid")
        value = MultiArgs(sentinel.a, ["a", "b"], {"a": 1})
        obj.attr_a = value
        ret = _attribute_diff(obj, "attr_a", value)
        t.assertEqual(ret, None)


class TestGetAttrValue(BaseTestCase):
    def test_set_methods(t):
        """given an attribute that starts with 'set'
        returns the value from the attribute's 'get' method
        """
        obj = GetSetObject()
        obj.setAttr(sentinel.attribute)

        value = _get_attr_value(obj, "Attr")

        t.assertEqual(value, sentinel.attribute)

    def test_naked_attribute(t):
        """non set values are returned from the attribute"""
        obj = sentinel.object
        obj.attribute = sentinel.attribute

        value = _get_attr_value(obj, "attribute")

        t.assertEqual(value, sentinel.attribute)

    def test_missing_attribute(t):
        """missing attributes return MISSINGNO sentinel value"""
        obj = sentinel.object
        ret = _get_attr_value(obj, "undefined")
        t.assertEqual(ret, MISSINGNO)

    def test_missing_getter_method(t):
        obj = GetSetObject()
        obj.id = "testobj"  # for logging
        ret = _get_attr_value(obj, "setUndefined")
        t.assertEqual(ret, MISSINGNO)


class TestSanitizeValue(BaseTestCase):
    def test_handles_strings(t):
        value = "some_string"
        ret = _sanitize_value(value, sentinel.obj)
        t.assertEqual(ret, value)

    def test_decodes_strings(t):
        original_str = "some_string"
        value = b64encode(original_str)
        obj = Mock(zCollectorDecoding="base64")
        ret = _sanitize_value(value, obj)
        t.assertEqual(ret, original_str)

    def test_decodes_strings_with_no_decoder(t):
        original_str = "some_string"
        obj = Mock(zCollectorDecoding="")
        ret = _sanitize_value(original_str, obj)
        t.assertEqual(ret, original_str.encode("utf-8"))

    def test_decodes_strings_with_non_unicode(t):
        original_str = "David Mu\xf1oz"
        obj = Mock(zCollectorDecoding="utf-8")
        ret = _sanitize_value(original_str, obj)
        t.assertEqual(ret, "David Muoz".encode("utf-8"))

    def test_handles_MultiArgs(t):
        args = (sentinel.a, "some_string", {"a": 1})
        value = MultiArgs(*args)
        ret = _sanitize_value(value, sentinel.obj)
        t.assertEqual(ret, args)

    @patch("{src}._decode_value".format(**PATH), autspec=True)
    def test_raises_UnicodeDecodeError(t, _decode_value):
        _decode_value.side_effect = UnicodeDecodeError("", "", 0, 0, "")
        value = "some string"
        with t.assertRaises(UnicodeDecodeError):
            _sanitize_value(value, sentinel.obj)


class TestDecodeValue(BaseTestCase):
    def test_decodes_strings(t):
        original_str = "some_string"
        value = b64encode(original_str)
        obj = Mock(zCollectorDecoding="base64")

        ret = _sanitize_value(value, obj)

        t.assertEqual(ret, original_str)


class TestUpdateObject(BaseTestCase):
    def test_update(t):
        obj = Device("deviceid")
        obj.attr = sentinel.a
        diff = {"attr": "sanitized sentinel.b"}

        ret = _update_object(obj, diff)

        t.assertEqual(obj.attr, "sanitized sentinel.b")
        t.assertTrue(ret)

    @patch("{src}._update_callable_attribute".format(**PATH), autospec=True)
    def test_callable_attributes(t, _update_callable_attribute):
        obj = GetSetObject()
        obj.id = "object_id"
        obj.Attr = None
        obj.setLastChange = Mock()
        diff = {"setAttr": "sanitized sentinel.value"}

        obj.setAttr("x")
        t.assertEqual(obj.Attr, "x")

        changed = _update_object(obj, diff)

        _update_callable_attribute.assert_called_with(
            obj.setAttr, "sanitized sentinel.value"
        )
        t.assertTrue(changed)

    def test_ignores_undefined_attributes(t):
        """does not add attributes that do not exist on the target"""
        obj = Device("deviceid")
        obj.attr = sentinel.a
        new_attr = "undefined"
        diff = {"attr": "sanitized sentinel.b", new_attr: "new attr"}

        ret = _update_object(obj, diff)

        t.assertEqual(obj.attr, "sanitized sentinel.b")
        t.assertFalse(hasattr(obj, new_attr))
        t.assertTrue(ret)


class TestUpdateCallableAttribute(BaseTestCase):
    def test_uses_set_method_to_update(t):
        obj = Mock(name="object", spec_set=["setAttr"])
        value = (
            ("a", "b"),
            "args",
            ["list", "x"],
            {"a", "dict"},
        )
        _update_callable_attribute(obj.setAttr, value)
        obj.setAttr.assert_called_with(*value)
        obj.setAttr.assert_called_with(
            ("a", "b"), "args", ["list", "x"], {"a", "dict"}
        )

    def test_updates_multiargs_attributes(t):
        obj = Mock(name="object", spec_set=["setAttr"])
        value = (sentinel.a, sentinel.b, sentinel.c)
        _update_callable_attribute(obj.setAttr, value)
        obj.setAttr.assert_called_with(sentinel.a, sentinel.b, sentinel.c)

    @patch("{src}.log".format(**PATH), autospec=True)
    def test_handles_exceptions(t, log):
        obj = Mock(name="object", spec_set=["setAttr"])

        def setAttr(*args):
            raise Exception()

        obj.setAttr = setAttr
        value = (
            ("a", "b"),
            "args",
            ["list", "x"],
            {"a", "dict"},
        )

        _update_callable_attribute(obj.setAttr, value)

        log.exception.assert_called_with(
            "Failed to set '%s.%s' to the value '%s'",
            obj.setAttr.__module__,
            obj.setAttr.__name__,
            value,
        )

    def test_retry_for_manual_signature_unpacking(t):
        """some callable attributes use a manual signature unpacking pattern
        ValueError: need more than 1 value to unpack
        """
        value = ("a", "b")
        container = Mock()

        def callable(*args):
            arg1, arg2 = args[0]
            container.arg1 = arg1
            container.arg2 = arg2

        _update_callable_attribute(callable, value)

        t.assertEqual(container.arg1, "a")
        t.assertEqual(container.arg2, "b")

    def test_retry_for_manual_signature_unpacking_nosplat(t):
        """A variant of signature unpacking, without *args
        TypeError: callable() takes exactly 1 argument (2 given)
        """
        value = ("a", "b")
        container = Mock()

        def callable(args):
            arg1, arg2 = args
            container.arg1 = arg1
            container.arg2 = arg2

        _update_callable_attribute(callable, value)

        t.assertEqual(container.arg1, "a")
        t.assertEqual(container.arg2, "b")
