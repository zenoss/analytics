##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase
from mock import Mock, create_autospec, patch

from Products.ZenModel.Device import Device

from ..incrementalupdate import (
    IncrementalDataMap,
    InvalidIncrementalDataMapError,
    log,
    NotFound,
    ObjectMap,
    _class_changed,
)
from .utils import BaseTestCase

# Given a parent device, path to a sub-device or component
# and optional relationship on the sub-device or component
# Apply the given ObjectMap to the target device
# where the target is parent/path/relationship/id

PATH = {"src": "Products.DataCollector.ApplyDataMap.incrementalupdate"}


class Test_incrementalupdate(TestCase):
    def test_log_name(t):
        t.assertEqual(log.name, "zen.IncrementalDataMap")


def setup_mock_environment(t):
    """Create mocks and test attributes
    that describe the ZODB object relationships
    """
    t.target_id = "target_id"
    t.target = Mock(
        name="target",
        spec_set=[
            "id",
            "a1",
            "isLockedFromUpdates",
            "isLockedFromDeletion",
            "setLastChange",
        ],
        id=t.target_id,
        a1="attribute 1",
        isLockedFromUpdates=Mock(return_value=False),
        isLockedFromDeletion=Mock(return_value=False),
    )
    # get the target from the relationship
    t.relationship = Mock(
        name="relationship",
        spec_set=[
            t.target.id,
            "_getOb",
            "hasobject",
            "_setObject",
            "objectItemsAll",
        ],
    )
    setattr(t.relationship, t.target.id, t.target)
    t.relationship._getOb.return_value = t.target
    t.relname = "relationship_name"
    # get the relationship on the parent
    t.parent = Mock(
        name="parent", spec_set=["id", t.relname, "removeRelation"]
    )
    setattr(t.parent, t.relname, t.relationship)
    t.compname = "parent/{}/{}".format(t.relname, t.target_id)
    # find the parent by its path from the base device
    t.base = Mock(Device, dmd=Mock())
    t.base.getObjByPath.return_value = t.parent
    # using special attributes specified on the ObjectMap
    t.object_map = ObjectMap(
        {
            "id": t.target.id,
            "relname": t.relname,
            "compname": t.compname,
            "a1": "attribute 1",
        }
    )

    t.idm = IncrementalDataMap(t.base, t.object_map)


class TestIncrementalDataMapAPI(BaseTestCase):
    def setUp(t):
        super(TestIncrementalDataMapAPI, t).setUp()
        setup_mock_environment(t)

        patches = [
            "_class_changed",
        ]

        for target in patches:
            patcher = patch("{src}.{}".format(target, **PATH), autospec=True)
            setattr(t, target, patcher.start())
            t.addCleanup(patcher.stop)

        t._class_changed.return_value = False

    def test_update(t):
        """Update attributes on the target device"""
        object_map = ObjectMap(
            {
                "id": t.target_id,
                "a1": "attribute_1_updated",
                "parentId": "parent id",
                "relname": t.relname,
                "compname": t.compname,
                "modname": "module.ClassName",
                "classname": "ClassName",
                "_flag": "not part of the model",
            }
        )

        # Create a new incremental data map
        idm = IncrementalDataMap(t.base, object_map)

        # Attributes available on the IncrementalDataMap
        t.assertEqual(idm.id, object_map.id)
        t.assertEqual(idm.path, object_map.compname)
        t.assertEqual(idm.relname, object_map.relname)
        t.assertEqual(idm.directive, "update")

        # Apply the map to the target
        idm.apply()
        # valid attributes are set
        t.assertEqual(t.target.a1, "attribute_1_updated")
        # underscore attributes are not set
        t.assertFalse(hasattr(t.target, "_flag"))

    def test_update_with_only_compname(t):
        """Update attributes on the target device
        given only the compname (path) from the base device to the target
        """
        object_map = ObjectMap(
            {
                "compname": t.compname,
                "modname": "module.ClassName",
                "a1": "attribute_1_updated",
            }
        )

        idm = IncrementalDataMap(t.base, object_map)

        t.assertEqual(idm.path, t.compname)
        t.assertEqual(idm.relname, t.relname)
        t.assertEqual(idm.target, t.target)

        idm.apply()
        # valid attributes are set
        t.assertEqual(t.target.a1, "attribute_1_updated")

    def test_update_base_device(t):
        """update the target device directly"""
        base = Mock(
            name="base target",
            spec_set=[
                "id",
                "a1",
                "isLockedFromUpdates",
                "isLockedFromDeletion",
                "setLastChange",
                "dmd",
            ],
            id=t.target_id,
            a1="attribute 1",
            isLockedFromUpdates=Mock(return_value=False),
            isLockedFromDeletion=Mock(return_value=False),
            dmd=Mock(name="dmd"),
        )

        object_map = ObjectMap(
            {
                "a1": "attribute_1_updated",
            }
        )

        idm = IncrementalDataMap(base, object_map)

        t.assertEqual(idm.path, "")
        t.assertEqual(idm.relname, None)
        t.assertEqual(idm.target, base)

        idm.apply()

        t.assertEqual(base.a1, "attribute_1_updated")


class TestIncrementalDataMapImpl(BaseTestCase):
    def setUp(t):
        super(TestIncrementalDataMapImpl, t).setUp()
        setup_mock_environment(t)

    def test___repr__(t):
        ret = str(t.idm)
        t.assertIsInstance(ret, str)
        t.assertEqual(
            ret, "<%s %s>" % (t.idm.__class__.__name__, t.idm.__dict__)
        )

    def test___init__(t):
        object_map = ObjectMap({"id": "target_id"})
        IncrementalDataMap("parent device", object_map)

    def test___init__raises_exception_for_invalid_object_map(t):
        with t.assertRaises(InvalidIncrementalDataMapError):
            IncrementalDataMap("parent device", "not object_map")

    def test___init__blank_map_is_valid(t):
        object_map = ObjectMap({})
        IncrementalDataMap("parent device", object_map)

    def test___init__captures_object_map_directive(t):
        object_map = ObjectMap({"id": "target_id", "_directive": "update"})
        idm = IncrementalDataMap("parent device", object_map)
        t.assertEqual(idm._directive, "update")

    def test___init__handles_legacy_directives(t):
        object_map = ObjectMap({"id": "target_id", "remove": True})
        idm = IncrementalDataMap("parent device", object_map)
        t.assertEqual(idm._directive, "remove")

    def test__process_objectmap(t):
        object_map = ObjectMap(
            {
                "id": "target_id",
                "remove": True,
                "a1": "attribute_1",
                "a2": "attribute_2",
                "parentId": "parent id",
                "relname": "relationship_name",
                "compname": "component/path",
                "modname": "module.name",
                "classname": "ClassName",
                "_flag": "not part of the model",
            }
        )

        # Executed in __init__
        idm = IncrementalDataMap(t.base, object_map)

        t.assertDictEqual(
            idm._object_map, {"a1": "attribute_1", "a2": "attribute_2"}
        )
        t.assertEqual(idm._target_id, object_map.id)
        t.assertEqual(idm.id, object_map.id)
        t.assertEqual(idm._directive, "remove")
        t.assertEqual(idm._parent_id, object_map.parentId)
        t.assertEqual(idm.path, object_map.compname)
        t.assertEqual(idm.relname, object_map.relname)

    def test_classname_given(t):
        module_name = "module.name"
        classname = "classname"
        object_map = ObjectMap(
            {
                "id": "target_id",
                "_directive": "nochange",
                "modname": module_name,
                "classname": classname,
            }
        )
        idm = IncrementalDataMap(t.base, object_map)
        t.assertEqual(idm.modname, module_name)
        t.assertEqual(idm.classname, classname)

    def test_classname_from_modname(t):
        module_name = "module.name.classname"
        object_map = ObjectMap(
            {
                "id": "target_id",
                "modname": module_name,
                "_directive": "nochange",
            }
        )
        idm = IncrementalDataMap(t.base, object_map)
        t.assertEqual(idm.modname, module_name)
        t.assertEqual(idm.classname, "classname")

    def test_parent_is_from_path(t):
        base = Device(id="base_id")
        getObjByPath = create_autospec(base.getObjByPath)
        base.getObjByPath = getObjByPath
        object_map = ObjectMap({"id": "os_id", "compname": "os"})

        idm = IncrementalDataMap(base, object_map)

        t.assertEqual(idm.path, "os")
        t.assertEqual(idm.parent, base.getObjByPath.return_value)
        getObjByPath.assert_called_with(idm.path)

    def test_parent_is_NotFound(t):
        base = Device(id="base_id")
        base.getObjByPath = Mock(side_effect=NotFound())
        object_map = ObjectMap({"id": "os_id", "compname": "os"})

        idm = IncrementalDataMap(base, object_map)

        t.assertEqual(idm.parent, base)

    def test_target_is_base(t):
        """target is the parent if component and relname are undefined"""
        base = Device(id="parent_id")
        object_map = ObjectMap({"id": base.id})
        idm = IncrementalDataMap(base, object_map)

        t.assertEqual(idm.target, base)

    def test_target_is_parent(t):
        """The target may be the parent device"""
        parent = Device(id="parent_id")
        object_map = ObjectMap({"id": parent.id})

        idm = IncrementalDataMap(parent, object_map)

        t.assertEqual(idm.target, parent)

    def test_target_is_component(t):
        """the target may be a component on the parent"""
        parent = Device(id="parent_id")
        object_map = ObjectMap({"id": "os_id", "compname": "os"})

        idm = IncrementalDataMap(parent, object_map)

        t.assertEqual(idm.target, parent.os)

    def test_target_is_component_without_id(t):
        """the target may be a component on the parent"""
        parent = Device(id="parent_id")
        object_map = ObjectMap({"compname": "os"})

        idm = IncrementalDataMap(parent, object_map)

        t.assertEqual(idm.target, parent.os)

    def test_target_is_relation(t):
        """the target may be in a relationship on the parent"""
        target = Mock(name="target", spec_set=["id"], id="target_obj")
        relname = "relationship_name"
        parent = Device(id="parent_id")
        relationship = Mock(name="relationship", spec_set=[relname, "_getOb"])
        setattr(parent, relname, relationship)
        relationship._getOb.return_value = target
        object_map = ObjectMap({"id": target.id, "relname": relname})

        idm = IncrementalDataMap(parent, object_map)

        t.assertEqual(idm.target, target)
        relationship._getOb.assert_called_with(target.id)

    def test_target_is_component_relationship(t):
        """the target may be in a relationship on a component/path
        found on the parent
        the compname may be a long path of nested components
        provided getObjByPath can find it
        """
        t.assertEqual(t.idm.target, t.target)

        t.relationship._getOb.assert_called_with(t.target.id)
        t.base.getObjByPath.assert_called_with(t.compname)

    def test__relname(t):
        t.assertEqual(t.idm._relname, t.relname)

    def test__relname_from_path(t):
        """when relname is not given, infer it from the path"""
        delattr(t.object_map, "relname")
        idm = IncrementalDataMap(t.base, t.object_map)
        t.assertEqual(idm._relname, t.relname)

    def test_relationship(t):
        t.assertEqual(t.idm.relationship, t.relationship)

    def test_relationship_requires_relname(t):
        """relname is required
        it may be given, or derived from compnane
        """
        delattr(t.object_map, "relname")
        delattr(t.object_map, "compname")
        idm = IncrementalDataMap(t.base, t.object_map)
        with t.assertRaises(InvalidIncrementalDataMapError):
            t.assertEqual(idm.relationship, t.relationship)

    def test_directive_add(t):
        """add the target if it does not exist"""
        t.relationship._getOb.side_effect = AttributeError("Unable to find id")
        t.object_map.modname = "module_name"  # required attribute
        idm = IncrementalDataMap(t.base, t.object_map)
        t.assertEqual(idm.target, None)
        t.assertEqual(idm.directive, "add")

    def test_directive_add_requires_modname(t):
        t.object_map.modname = None
        t.object_map._directive = "add"

        with t.assertRaises(InvalidIncrementalDataMapError):
            t.idm.directive

    def test_directive_add_requires_relname(t):
        t.object_map.modname = "module_name"
        delattr(t.object_map, "relname")
        delattr(t.object_map, "compname")
        idm = IncrementalDataMap(t.base, t.object_map)
        with t.assertRaises(InvalidIncrementalDataMapError):
            idm.directive = "add"

    def test_directive_remove(t):
        """remove the target if specified by the object_map"""
        t.object_map._directive = "remove"
        idm = IncrementalDataMap(t.base, t.object_map)
        t.assertEqual(idm.directive, "remove")

    def test_directive_rebuild(t):
        """rebuild the target, if class name changed"""
        t.object_map.classname = "NewClass"
        idm = IncrementalDataMap(t.base, t.object_map)
        t.assertEqual(idm.directive, "rebuild")

    def test_directive_delete_locked(t):
        """do not delete locked targets"""
        t.object_map._directive = "remove"
        t.target.isLockedFromDeletion.return_value = True

        idm = IncrementalDataMap(t.base, t.object_map)

        t.assertEqual(idm.directive, "delete_locked")

    def test_directive_update(t):
        """update the target if it exists"""
        t.object_map.a1 = "new value"
        idm = IncrementalDataMap(t.base, t.object_map)
        t.assertEqual(idm.directive, "update")

    def test_directive_update_locked(t):
        """do not update locked targets"""
        t.target.isLockedFromUpdates.return_value = True
        t.idm.directive = "update"
        t.assertEqual(t.idm.directive, "update_locked")

    def test_directive_nochange(t):
        """do not update if no changes need be made"""
        t.idm.target = Mock(
            name="target",
            spec_set=["id", "a1"],
            id="target_id",
            a1="attribute 1",
        )
        t.idm._object_map["a1"] = t.idm.target.a1

        t.assertEqual(t.idm._diff, {})
        t.assertEqual(t.idm.directive, "nochange")

    def test__directive(t):
        """_directive is exposed for ADMReporter"""
        t.idm.directive = "update"
        t.assertEqual(t.idm._directive, "update")

    def test__valid_id(t):
        t.object_map.id = t.target.id
        ret = t.idm._valid_id()
        t.assertEqual(ret, True)

    def test__valid_id_mismatch(t):
        t.object_map.id = "mismatch"
        idm = IncrementalDataMap(t.base, t.object_map)
        t.assertEqual(idm._valid_id(), False)

    def test__valid_id_not_specified_in_objectmap(t):
        delattr(t.object_map, "id")
        delattr(t.object_map, "compname")
        idm = IncrementalDataMap(t.base, t.object_map)
        t.assertEqual(idm._valid_id(), True)

    def test__diff(t):
        t.target = Mock(
            name="target",
            spec_set=["id", "a1", "a2", "a3"],
            id="target_id",
            a1="attribute 1",
            a2="attribute 2",
            a3="attribute 3",
        )
        t.object_map.a1 = "new attribute 1"
        t.object_map.a3 = "new attribute 3"

        idm = IncrementalDataMap(t.base, t.object_map)

        t.assertEqual(
            idm._diff, {"a1": "new attribute 1", "a3": "new attribute 3"}
        )

    def test__diff_nochange(t):
        t.idm.target = Mock(
            name="target",
            spec_set=["id", "a1"],
            id="target_id",
            a1="attribute 1",
        )
        t.idm._object_map["a1"] = t.idm.target.a1

        t.assertEqual(t.idm._diff, {})

    def test_apply_add(t):
        t.idm._add = create_autospec(t.idm._add)
        t.idm.modname = "module_name"
        t.idm.directive = "add"

        t.idm.apply()

        t.idm._add.assert_called_with()

    def test_apply_update(t):
        """Execute the appropriate method to apply the required change"""
        t.idm._update = create_autospec(t.idm._update)
        t.idm.directive = "update"
        t.idm.apply()
        t.idm._update.assert_called_with()

    def test_apply_remove(t):
        t.idm._remove = create_autospec(t.idm._remove)
        t.idm.directive = "remove"
        t.idm.apply()
        t.idm._remove.assert_called_with()

    def test_apply_nochange(t):
        t.idm._nochange = create_autospec(t.idm._nochange)
        t.idm.directive = "nochange"
        t.idm.apply()
        t.idm._nochange.assert_called_with()

    def test_apply_rebuild(t):
        t.idm._rebuild = create_autospec(t.idm._rebuild)
        t.idm.directive = "rebuild"
        t.idm.apply()
        t.idm._rebuild.assert_called_with()

    def test_apply_update_locked(t):
        t.idm._nochange = create_autospec(t.idm._nochange)
        t.idm.directive = "update_locked"
        t.idm.apply()
        t.idm._nochange.assert_called_with()

    def test_apply_delete_locked(t):
        t.idm._nochange = create_autospec(t.idm._nochange)
        t.idm.directive = "delete_locked"
        t.idm.apply()
        t.idm._nochange.assert_called_with()

    def test__add(t):
        """creates, updates, and adds the new object to the relationship.
        Requires modname.
        """
        t.idm._create_target = create_autospec(t.idm._create_target)
        t.idm._create_target.return_value = t.target
        t.relationship.hasobject.return_value = False
        t.relationship.objectItemsAll.return_value = ()
        t.idm.modname = "module.name"

        t.idm._add()

        t.assertTrue(t.idm.changed)
        t.idm._create_target.assert_called_with()
        t.idm.relationship._setObject.assert_called_with(
            t.idm.target.id, t.idm.target
        )
        t.idm.target.setLastChange.assert_called_with()

    def test__add_target_to_relationship(t):
        t.relationship.hasobject.return_value = False
        t.idm._add_target_to_relationship()
        t.relationship._setObject.assert_called_with(t.target.id, t.target)

    def test__add_target_to_relationship_is_idempotent(t):
        t.relationship.hasobject.return_value = True
        t.idm._add_target_to_relationship()
        t.relationship._setObject.assert_not_called()

    @patch("{src}.DatamapUpdateEvent".format(**PATH), autospec=True)
    @patch("{src}.notify".format(**PATH), autospec=True)
    @patch("{src}._update_object".format(**PATH), autospec=True)
    def test__update(t, _update_object, notify, DatamapUpdateEvent):
        """Update the target object"""
        _update_object.return_value = True
        t.idm._update()

        _update_object.assert_called_with(t.idm.target, t.idm._diff)
        DatamapUpdateEvent.assert_called_with(
            t.base.dmd, t.object_map, t.target
        )
        notify.assert_called_with(DatamapUpdateEvent.return_value)
        t.assertIs(True, t.idm.changed)

    def test__remove(t):
        """Remove the target from the relationshp"""
        t.idm._remove()
        t.parent.removeRelation.assert_called_with(t.idm.relname, t.idm.target)
        t.assertIs(True, t.idm.changed)

    def test__remove_witout_target(t):
        """changed is false, if remove is called without a target"""
        t.idm.target = None
        t.idm._remove()
        t.assertIs(False, t.idm.changed)

    def test__remove_without_relname(t):
        """changed is false, if remove is called without relname"""
        t.idm.relname = None
        t.idm._remove()
        t.assertIs(False, t.idm.changed)

    def test__remove_handles_attribute_error(t):
        t.parent.removeRelation.side_effect = AttributeError()
        t.idm._remove()
        t.assertIs(False, t.idm.changed)

    def test__nochange(t):
        """Make no changes"""
        t.idm._nochange()
        t.assertIs(False, t.idm.changed)

    def test_iteritems(t):
        attrs = {k: v for k, v in t.idm.iteritems()}
        map_attrs = {k: v for k, v in t.idm._object_map.iteritems()}
        t.assertEqual(attrs, map_attrs)

    @patch("{src}.import_module".format(**PATH), autospec=True)
    def test__create_target(t, import_module):
        module = Mock(name="module")
        import_module.return_value = module
        t.idm.modname = "module.path"
        t.idm.classname = "ConstructorName"

        t.idm._create_target()

        import_module.assert_called_with(t.idm.modname)
        module.ConstructorName.assert_called_with(t.idm._target_id)
        t.assertEqual(t.idm._target, module.ConstructorName.return_value)

    def test__rebuild(t):
        t.idm._remove = create_autospec(t.idm._remove)
        t.idm._add = create_autospec(t.idm._add)

        t.idm._rebuild()

        t.idm._remove.assert_called_with()
        t.idm._add.assert_called_with()
        t.assertEqual(t.idm.changed, True)

    def test_do_not_update_target_id(t):
        """Modeling should never change the id of a device. (ZEN-14518)
        in this scenario the given base device is the target
        and the ObjectMap's ID does not match the devices.
        """
        target = Mock(
            name="target",
            spec_set=[
                "id",
                "a1",
                "isLockedFromUpdates",
                "isLockedFromDeletion",
                "setLastChange",
                "getObjByPath",
            ],
            id="target_id",
            a1="attribute 1",
            isLockedFromUpdates=Mock(return_value=False),
            isLockedFromDeletion=Mock(return_value=False),
            getObjByPath=Mock(side_effect=NotFound()),
        )
        object_map = ObjectMap(
            {
                "id": "different_id",
                "a1": "attr changed",
            }
        )
        idm = IncrementalDataMap(target, object_map)

        idm.apply()

        t.assertEqual(idm.directive, "nochange")
        t.assertEqual(target.id, "target_id")
        t.assertEqual(idm.changed, False)

    def test_target_class_change(t):
        """changing the target's class triggers a rebuild of the target"""
        t.object_map.modname = "new.module"
        t.object_map.classname = "NewClass"
        idm = IncrementalDataMap(t.base, t.object_map)
        idm._rebuild = create_autospec(idm._rebuild)

        idm.apply()

        idm._rebuild.assert_called_with()


class Test__class_changed(TestCase):
    def setUp(t):
        t.obj = Device("oid")
        t.modname = "Products.ZenModel.Device"
        t.classname = "Device"

    def test_unchanged(t):
        ret = _class_changed(t.modname, t.classname, t.obj)
        t.assertEqual(ret, False)

    def test_class_changed(t):
        t.classname = "NewDevice"
        ret = _class_changed(t.modname, t.classname, t.obj)
        t.assertEqual(ret, True)

    def test_class_is_nullstr(t):
        t.classname = ""
        ret = _class_changed(t.modname, t.classname, t.obj)
        t.assertEqual(ret, False)

    @patch("{src}.inspect".format(**PATH), autospec=True)
    def test_handles_exception_getting_obj_class(t, inspect):
        inspect.getmodule.side_effect = Exception()
        ret = _class_changed(t.modname, t.classname, t.obj)
        t.assertEqual(ret, True)

    def test_module_changed(t):
        t.modname = "Products.ZenModel.NewDevice"
        ret = _class_changed(t.modname, t.classname, t.obj)
        t.assertEqual(ret, True)
