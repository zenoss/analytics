##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from mock import Mock, create_autospec, patch, sentinel, MagicMock, call

from Products.ZenModel.Device import Device

from ..applydatamap import (
    ApplyDataMap,
    CLASSIFIER_CLASS,
    IncrementalDataMap,
    NotFound,
    ObjectMap,
    RelationshipMap,
    ZenModelRM,
    _clone_datamap,
    _create_object,
    _get_object_by_pid,
    _get_objmap_target,
    _get_relationship_ids,
    _get_relationshipmap_diff,
    _get_relmap_target,
    _process_relationshipmap,
    _remove_relationship,
    _validate_datamap,
    _validate_device_class,
)
from .utils import BaseTestCase

PATH = {"src": "Products.DataCollector.ApplyDataMap.applydatamap"}


class ApplyDataMapTests(BaseTestCase):
    def setUp(t):
        super(ApplyDataMapTests, t).setUp()

        patches = [
            "notify",
            "_get_relmap_target",
            "ADMReporter",
            "DatamapAddEvent",
        ]

        for target in patches:
            patcher = patch("{src}.{}".format(target, **PATH), autospec=True)
            setattr(t, target, patcher.start())
            t.addCleanup(patcher.stop)

        t.datacollector = Mock(name="datacollector", dmd=Mock(name="dmd"))
        t.adm = ApplyDataMap(t.datacollector)

    def _device_and_objmap(self, map_spec=[], dev_spec=[]):
        relname = "relationship"
        relationship = Mock(name=relname, spec_set=["_getOb"])
        map_spec += ["_relname", "id"]
        object_map = ObjectMap({"id": "device_id", "_relname": relname})
        dev_spec += ["id", "meta_type", object_map._relname]
        device = Mock(
            name="device",
            spec_set=dev_spec,
            id=object_map.id,
            meta_type="Device",
        )
        setattr(device, object_map._relname, relationship)

        self._get_relmap_target.return_value = device
        return device, object_map

    def _device_and_relmap(self):
        device = Mock(Device, name="device")
        device.isLockedFromUpdates.return_value = False
        self._get_relmap_target.return_value = device
        relmap = MagicMock(RelationshipMap)

        self._get_relmap_target.return_value = device
        return device, relmap

    def test___init__(t):
        t.assertEqual(t.adm.datacollector, t.datacollector)
        t.assertEqual(t.adm.num_obj_changed, 0)
        t.assertEqual(t.adm._dmd, t.datacollector.dmd)

    def test___init__without_datacollector(t):
        adm = ApplyDataMap()
        t.assertEqual(adm._dmd, None)
        t.assertEqual(adm.datacollector, None)

    def test_setDeviceClass(t):
        device = Mock(
            name="device",
            spec_set=["getDeviceClassPath", "changeDeviceClass"],
        )
        device.getDeviceClassPath.return_value = CLASSIFIER_CLASS
        newclass = "NewClass"

        t.adm.setDeviceClass(device, deviceClass=newclass)

        device.changeDeviceClass.assert_called_with(newclass)

    def test_setDeviceClass_mismatch(t):
        device = Mock(
            name="device",
            spec_set=["getDeviceClassPath", "changeDeviceClass"],
        )
        device.getDeviceClassPath.return_value = "NOT_CLASSIFIER_CLASS"

        t.adm.setDeviceClass(device, deviceClass="NewClass")

        device.changeDeviceClass.assert_not_called()

    def test_applyDataMap_false_if_target_not_found(t):
        datamap = Mock(RelationshipMap, relname="not_found")
        t._get_relmap_target.return_value = None

        ret = t.adm.applyDataMap(sentinel.device, datamap)
        t.assertEqual(ret, False)

    @patch("{src}._locked_from_updates".format(**PATH), autospec=True)
    def test_applyDataMap_false_if_target_locked(t, _locked_from_updates):
        t._get_relmap_target.return_value = sentinel.device
        _locked_from_updates.return_value = True
        ret = t.adm.applyDataMap(sentinel.device, sentinel.datamap)
        t.assertEqual(ret, False)

    @patch("{src}._process_relationshipmap".format(**PATH), autospec=True)
    @patch("{src}.transact".format(**PATH), autospec=True)
    def test_applyDataMap_RelationshipMap(
        t,
        transact,
        _process_relationshipmap,
    ):
        device, relmap = t._device_and_relmap()
        _process_relationshipmap.return_value = relmap
        _get_relmap_target.return_value = device
        # make transact return the argument passed to it
        transact.side_effect = lambda x: x
        t.adm._apply_relationshipmap = create_autospec(
            t.adm._apply_relationshipmap
        )
        t.adm._report_changes = create_autospec(t.adm._report_changes)

        ret = t.adm.applyDataMap(device, relmap)

        t.DatamapAddEvent.assert_called_with(t.adm._dmd, relmap, device)
        t.notify.assert_called_with(t.DatamapAddEvent.return_value)
        transact.assert_called_with(t.adm._apply_relationshipmap)
        _process_relationshipmap.assert_called_with(relmap, device)
        t.adm._apply_relationshipmap.assert_called_with(relmap, device)
        t.adm._report_changes.assert_called_with(relmap, device)
        t.assertEqual(ret, t.adm._report_changes.return_value)

    def test_applyDataMap_RelationshipMap_contains_IncrementalDataMap(t):
        """A relationshipMap may contain IncrementalDataMaps
        in addition to ObjectMaps
        """
        base = Device(id="owner")
        device = Device(id="related_device")
        device.dmd = Mock(name="dmd")
        relmap = RelationshipMap()
        relmap.append(
            IncrementalDataMap(device, ObjectMap({"comments": "ok"}))
        )

        t.adm.applyDataMap(base, relmap)

        t.assertEqual(device.comments, "ok")

    @patch("{src}._validate_datamap".format(**PATH), autospec=True)
    @patch("{src}.transact".format(**PATH), autospec=True)
    def test_applyDataMap_ObjectMap(t, transact, _validate_datamap):
        device, objmap = t._device_and_objmap(dev_spec=["getObjByPath"])
        device.getObjByPath.return_value = device
        # make transact return the argument passed to it
        transact.side_effect = lambda x: x
        _apply_incrementalmap = create_autospec(t.adm._apply_incrementalmap)
        t.adm._apply_incrementalmap = _apply_incrementalmap
        incmap = Mock(IncrementalDataMap)
        _validate_datamap.return_value = incmap
        t.adm._report_changes = create_autospec(t.adm._report_changes)

        ret = t.adm.applyDataMap(device, objmap)

        t.DatamapAddEvent.assert_called_with(t.adm._dmd, objmap, device)
        t.notify.assert_called_with(t.DatamapAddEvent.return_value)
        transact.assert_called_with(t.adm._apply_incrementalmap)
        _apply_incrementalmap.assert_called_with(incmap, device)
        t.adm._report_changes.assert_called_with(incmap, device)
        t.assertEqual(ret, t.adm._report_changes.return_value)

    def test_applyDataMap_ObjectMap_set_lists(t):
        device = Mock(Device(id="test_applyDataMap_ObjectMap_set_lists"))
        device.dmd = Mock(name="dmd")
        device.isLockedFromUpdates.return_value = False
        device.zCollectorDecoding = "utf-8"
        device.getFoo = Mock(return_value=[3, 2, 1])
        device.setFoo = Mock()

        # Set it to the same exact list- setter should not be called.
        t.adm.applyDataMap(
            device, ObjectMap({"id": device.id, "setFoo": [3, 2, 1]})
        )
        device.setFoo.assert_not_called()

        # Set it to the same list contents, but in a different order.
        # Setter should not be called.
        device.setFoo.reset_mock()
        t.adm.applyDataMap(
            device, ObjectMap({"id": device.id, "setFoo": [1, 2, 3]})
        )
        device.setFoo.assert_not_called()

        # Now change the contents.  This should of course call the setter.
        device.setFoo.reset_mock()
        t.adm.applyDataMap(device, ObjectMap({"id": device.id, "setFoo": [1]}))
        device.setFoo.assert_called_once_with([1])

        # One more variation- change form a list to a string.
        # Now change the contents.  This should of course call the setter.
        device.setFoo.reset_mock()
        t.adm.applyDataMap(
            device, ObjectMap({"id": device.id, "setFoo": "foo"})
        )
        device.setFoo.assert_called_once_with("foo")

    @patch("{src}.transact".format(**PATH), autospec=True)
    def test_applyDataMap_IncrementalDataMap(t, transact):
        device, objmap = t._device_and_objmap()
        incremental_dm = Mock(IncrementalDataMap)
        # make transact return the argument passed to it
        transact.side_effect = lambda x: x
        _apply_incrementalmap = create_autospec(t.adm._apply_incrementalmap)
        t.adm._apply_incrementalmap = _apply_incrementalmap
        t.adm._report_changes = create_autospec(t.adm._report_changes)

        ret = t.adm.applyDataMap(device, incremental_dm)

        transact.assert_called_with(_apply_incrementalmap)
        t.adm._apply_incrementalmap.assert_called_with(incremental_dm, device)
        t.adm._report_changes.assert_called_with(incremental_dm, device)
        t.assertEqual(ret, t.adm._report_changes.return_value)

    @patch("{src}._process_relationshipmap".format(**PATH), autospec=True)
    def test_applyDataMap_RelationshipMap_commit_false(
        t, _process_relationshipmap
    ):
        device, relmap = t._device_and_relmap()
        _process_relationshipmap.return_value = relmap
        t.adm._apply_relationshipmap = create_autospec(
            t.adm._apply_relationshipmap
        )
        t.adm._report_changes = create_autospec(t.adm._report_changes)

        ret = t.adm.applyDataMap(device, relmap, commit=False)

        t.DatamapAddEvent.assert_called_with(t.adm._dmd, relmap, device)
        t.notify.assert_called_with(t.DatamapAddEvent.return_value)
        _process_relationshipmap.assert_called_with(relmap, device)
        t.adm._apply_relationshipmap.assert_called_with(relmap, device)
        t.adm._report_changes.assert_called_with(relmap, device)
        t.assertEqual(ret, t.adm._report_changes.return_value)

    @patch("{src}._validate_datamap".format(**PATH), autospec=True)
    @patch("{src}.transact".format(**PATH), autospec=True)
    def test_applyDataMap_ObjectMap_commit_false(
        t, transact, _validate_datamap
    ):
        device, objmap = t._device_and_objmap()
        t.adm._report_changes = create_autospec(t.adm._report_changes)
        incmap = Mock(IncrementalDataMap)
        _validate_datamap.return_value = incmap

        ret = t.adm.applyDataMap(device, objmap, commit=False)

        _validate_datamap.assert_called_with(
            device, objmap, compname="", modname="", parentId="", relname=""
        )
        t.DatamapAddEvent.assert_called_with(t.adm._dmd, objmap, device)
        t.notify.assert_called_with(t.DatamapAddEvent.return_value)
        # not called
        t.assertFalse(transact.call_args_list)
        incmap.apply.assert_called_with()
        t.adm._report_changes.assert_called_with(incmap, device)
        t.assertEqual(ret, t.adm._report_changes.return_value)

    def test__applyDataMap(t):
        """_applyDataMap is an alias for the public API
        because most legacy code calls it directly
        """
        t.assertEqual(t.adm._applyDataMap, t.adm.applyDataMap)

    @patch("{src}._remove_relationship".format(**PATH), autospec=True)
    def test__apply_relationshipmap(t, _remove_relationship):
        # t.adm._apply_incrementalmap = create_autospec(
        #     t.adm._apply_incrementalmap, return_value=True
        # )
        device, relmap = t._device_and_relmap()
        relmap._parent = sentinel.parent
        relmap.maps = [Mock(IncrementalDataMap), Mock(IncrementalDataMap)]
        relmap.__iter__.return_value = relmap.maps
        relmap._diff = {"removed": [sentinel.remove], "locked": []}

        t.adm._apply_relationshipmap(relmap, device)

        _remove_relationship.assert_called_with(
            relmap._parent, relmap.relname, sentinel.remove
        )
        for m in relmap.maps:
            m.apply.assert_called_with()

    @patch("{src}._get_relationshipmap_diff".format(**PATH), autospec=True)
    @patch("{src}._get_relationship_ids".format(**PATH), autospec=True)
    def test__apply_relationshipmap_invalid_map_exception(
        t, _get_relationship_ids, _get_relationshipmap_diff
    ):
        """raises an exception if iterating over the relationship map returns
        an invalid objectmap type
        """
        relmap = MagicMock(name="RelationshipMap", relname="relationship_name")
        relmap.__iter__.return_value = iter([sentinel.invalid])
        device = Mock(name="device")
        device.isLockedFromUpdates.return_value = False

        with t.assertRaises(RuntimeError):
            t.adm._apply_relationshipmap(relmap, device)

    def test__apply_relationshipmap_ZenModelRM(t):
        device, relmap = t._device_and_relmap()
        relmap._diff = {"removed": [], "locked": []}
        object_map = Mock(ZenModelRM, name="object_map_1", id="om1")
        relmap.__iter__.return_value = [object_map]

        t.adm._apply_relationshipmap(relmap, device)

        device.addRelation.assert_called_with(relmap.relname, object_map)

    def test__apply_incrementalmap(t):
        device = sentinel.device
        imap = Mock(IncrementalDataMap)

        t.adm._apply_incrementalmap(imap, device)

        imap.apply.assert_called_with()

    def test_stop(t):
        """legacy method, noop"""
        t.adm.stop()

    @patch("{src}.log".format(**PATH), autospec=True)
    def test__report_changes(t, log):
        t.adm._report_relationshipmap_changes = create_autospec(
            t.adm._report_relationshipmap_changes
        )
        device, relmap = t._device_and_relmap()
        objmaps = [Mock(_directive=dir) for dir in ["add", "update"]]
        relmap.__iter__.return_value = objmaps
        relmap._diff = {}

        ret = t.adm._report_changes(relmap, device)

        log.info.assert_called_with(
            "applied RelationshipMap changes: target=%s.%s, change_counts=%s",
            device.id,
            relmap.relname,
            {
                "nochange": 0,
                "rebuild": 0,
                "delete_locked": 0,
                "update": 1,
                "remove": 0,
                "add": 1,
                "update_locked": 0,
            },
        )
        t.adm._report_relationshipmap_changes.assert_called_with(
            relmap, device
        )
        t.assertEqual(ret, True)

    def test__report_changes_for_relationshipmap_nochange(t):
        t.adm._report_relationshipmap_changes = create_autospec(
            t.adm._report_relationshipmap_changes
        )
        device, relmap = t._device_and_relmap()
        objmaps = [Mock(_directive=dir) for dir in ["nochange", "nochange"]]
        relmap.__iter__.return_value = objmaps
        relmap._diff = {"removed": []}

        ret = t.adm._report_changes(relmap, device)

        t.adm._report_relationshipmap_changes.assert_called_with(
            relmap, device
        )
        t.assertEqual(ret, False)

    def test__report_changes_for_objectmap(t):
        t.adm._report_objectmap_changes = create_autospec(
            t.adm._report_objectmap_changes
        )
        device, objmap = t._device_and_objmap()
        objmap._directive = "update"

        ret = t.adm._report_changes(objmap, device)

        t.adm._report_objectmap_changes.assert_called_with(objmap, device)
        t.assertEqual(ret, True)

    def test__report_changes_for_objectmap_add(t):
        t.adm._report_objectmap_changes = create_autospec(
            t.adm._report_objectmap_changes
        )
        device, objmap = t._device_and_objmap()
        objmap._directive = "add"

        ret = t.adm._report_changes(objmap, device)

        t.adm._report_objectmap_changes.assert_called_with(objmap, device)
        t.assertEqual(ret, True)

    def test__report_changes_no_change(t):
        t.adm._report_objectmap_changes = create_autospec(
            t.adm._report_objectmap_changes
        )
        device, objmap = t._device_and_objmap()
        objmap._directive = "nochange"

        ret = t.adm._report_changes(objmap, device)

        t.adm._report_objectmap_changes.assert_called_with(objmap, device)
        t.assertEqual(ret, False)

    def test__report_changes_for_incrementaldatamap(t):
        t.adm._report_objectmap_changes = create_autospec(
            t.adm._report_objectmap_changes
        )
        incrementaldatamap = Mock(IncrementalDataMap)
        device = sentinel.device

        ret = t.adm._report_changes(incrementaldatamap, device)

        t.adm._report_objectmap_changes.assert_called_with(
            incrementaldatamap, device
        )
        t.assertEqual(ret, incrementaldatamap.changed)

    def test__report_changes_for_unknown(t):
        ret = t.adm._report_changes("unknown type", "device")
        t.assertEqual(ret, False)

    def test__report_relationshipmap_changes(t):
        device, relmap = t._device_and_relmap()
        relmap._diff = {
            "removed": [sentinel.remove],
            "locked": [sentinel.lock],
        }
        relmap.__iter__.return_value = [
            sentinel.objectmap,
        ]

        t.adm._report_relationshipmap_changes(relmap, device)

        t.adm._reporter.report_removed.assert_called_with(
            device, relname=relmap.relname, target=sentinel.remove
        )
        t.adm._reporter.report_delete_locked.assert_called_with(
            device, relname=relmap.relname, target=sentinel.lock
        )

    def test_report_objectmap_changes(t):
        obj, objmap = t._device_and_objmap()
        t.adm._report_objectmap_changes(objmap, obj)
        t.adm._reporter.report_directive.assert_called_with(obj, objmap)

    def test__updateRelationship(t):
        """legacy method, exists so zenpack monkey patches won't fail
        some zenpacks will call this directly
        """
        t.adm.applyDataMap = create_autospec(t.adm.applyDataMap)
        device = Device(id="test_device")
        relmap = RelationshipMap()
        t.adm._updateRelationship(device, relmap)
        t.adm.applyDataMap.assert_called_with(device, relmap)

    def test__removeRelObject(t):
        """legacy method, exists so zenpack monkey patches won't fail"""
        t.adm._removeRelObject("device", "objmap", "relname")

    @patch("{src}.IncrementalDataMap".format(**PATH), autospec=True)
    def test__createRelObject(t, IncrementalDataMap):
        """legacy method, reroute to applyDataMap method"""
        t.adm.applyDataMap = create_autospec(t.adm.applyDataMap)
        device, objectmap = t._device_and_objmap()

        ret = t.adm._createRelObject(device, objectmap, "relname")

        t.assertEqual(objectmap.relname, "relname")
        IncrementalDataMap.assert_called_with(device, objectmap)
        t.adm.applyDataMap.assert_called_with(
            device, IncrementalDataMap.return_value
        )
        t.assertEqual(
            ret,
            (
                t.adm.applyDataMap.return_value,
                IncrementalDataMap.return_value.target,
            ),
        )


##############################################################################
# Preproce, diff and set directives
##############################################################################


class Test_get_relmap_target(BaseTestCase):
    def test__get_relmap_target(t):
        device = Mock(name="device", id=sentinel.pid)
        datamap = Mock(name="datamap", parentId=None, compname=None)
        ret = _get_relmap_target(device, datamap)
        t.assertEqual(ret, device)

    def test__get_relmap_target_pid(t):
        device = Mock(name="device", id=sentinel.pid)
        datamap = Mock(name="datamap", parentId=sentinel.pid)
        ret = _get_relmap_target(device, datamap)
        t.assertEqual(ret, device)

    @patch("{src}._get_object_by_pid".format(**PATH), autospec=True)
    def test__get_relmap_target_pid_mismatch(t, _get_object_by_pid):
        device = Mock(name="device", id=sentinel.id)
        datamap = Mock(name="datamap", parentId=sentinel.pid)

        ret = _get_relmap_target(device, datamap)
        _get_object_by_pid.assert_called_with(device, datamap.parentId)
        t.assertEqual(ret, _get_object_by_pid.return_value)

    def test__get_relmap_target_component(t):
        device = Mock(
            name="device", id=sentinel.id, getObjByPath=lambda x: sentinel.obj
        )
        datamap = Mock(
            name="datamap", parentId=None, compname=sentinel.compname
        )
        device.componentSearch.return_value = []

        ret = _get_relmap_target(device, datamap)
        t.assertEqual(ret, sentinel.obj)

    def test__get_relmap_target_not_found(t):
        """return None if the specified component is not found"""
        device = Mock(name="device", id=sentinel.id)
        device.getObjByPath.side_effect = NotFound(sentinel.compname)
        datamap = Mock(
            name="datamap", parentId=None, compname=sentinel.compname
        )
        device.componentSearch.return_value = []

        ret = _get_relmap_target(device, datamap)
        t.assertEqual(ret, None)

    @patch("{src}._validate_device_class".format(**PATH), autospec=True)
    def test__get_relmap_target_invalid_device(t, _validate_device_class):
        _validate_device_class.return_value = None
        ret = _get_relmap_target(sentinel.device, sentinel.datamap)
        t.assertIs(None, ret)


class Test_validate_device_class(BaseTestCase):
    def test__validate_device_class(t):
        device = Mock(name="device", deviceClass=lambda: "some class")
        ret = _validate_device_class(device)
        t.assertEqual(ret, device)

    def test__validate_device_class_dmd_lookup(t):
        device = Mock(name="device", deviceClass=lambda: None)
        ret = _validate_device_class(device)

        device.dmd.Devices.findDeviceByIdExact.assert_called_with(device.id)
        t.assertEqual(ret, device.dmd.Devices.findDeviceByIdExact.return_value)

    def test__validate_device_class_lost(t):
        device = Mock(name="device", deviceClass=lambda: None)
        device.dmd.Devices.findDeviceByIdExact.return_value = None

        ret = _validate_device_class(device)
        t.assertEqual(ret, None)

    def test__validate_device_class_missing(t):
        device = Mock(
            name="device", deviceClass=Mock(side_effect=AttributeError())
        )
        device.dmd.Devices.findDeviceByIdExact.return_value = None

        ret = _validate_device_class(device)
        t.assertEqual(ret, None)


class Test_get_object_by_pid(BaseTestCase):
    def test_finds_object(t):
        device = Mock(name="device")
        device.componentSearch.return_value = [
            Mock(name="object ref", getObject=lambda: sentinel.obj)
        ]

        ret = _get_object_by_pid(device, sentinel.parent_id)
        device.componentSearch.assert_called_with(id=sentinel.parent_id)
        t.assertEqual(ret, sentinel.obj)

    @patch("{src}.log".format(**PATH), autospec=True)
    def test_too_many_matches(t, log):
        device = Mock(name="device")
        device.componentSearch.return_value = ["a", "b"]

        ret = _get_object_by_pid(device, sentinel.parent_id)
        device.componentSearch.assert_called_with(id=sentinel.parent_id)
        log.warn.assert_called_with(
            "too many matches for parentId: parentId=%s", sentinel.parent_id
        )
        t.assertEqual(ret, None)

    @patch("{src}.log".format(**PATH), autospec=True)
    def test_no_matches(t, log):
        device = Mock(name="device", id=sentinel.id)
        device.componentSearch.return_value = []

        ret = _get_object_by_pid(device, sentinel.parent_id)

        device.componentSearch.assert_called_with(id=sentinel.parent_id)
        log.warn.assert_called_with(
            "Unable to find a matching parentId: parentID=%s",
            sentinel.parent_id,
        )
        t.assertEqual(ret, None)


class Test__validate_datamap(BaseTestCase):
    def test_relationshipmap(t):
        datamap = RelationshipMap()
        ret = _validate_datamap(
            sentinel.device,
            datamap,
            "relname",
            "compname",
            "modname",
            "parentId",
        )
        t.assertEqual(ret, datamap)

    def test_objectmap(t):
        datamap = ObjectMap({"id": sentinel.deviceid})

        ret = _validate_datamap(
            sentinel.device, datamap, None, "compname", "modname", "parentId"
        )

        t.assertIsInstance(ret, IncrementalDataMap)
        t.assertEqual(ret._base, sentinel.device)

    def test_relname_means_relationshipmap(t):
        """Legacy API Asumption:
        given a ObjectMap, and including a relname
        return a relationshipMap
        """
        object_map = ObjectMap({"id": sentinel.deviceid})
        datamap = [object_map]
        ret = _validate_datamap(
            sentinel.device,
            datamap,
            "relname",
            "compname",
            sentinel.modname,
            "parentId",
        )

        t.assertIsInstance(ret, RelationshipMap)
        for objmap in ret:
            t.assertEqual(objmap.modname, sentinel.modname)
            t.assertEqual(objmap.id, sentinel.deviceid)

    def test_build_incrementalmap_from_dict(t):
        device = Device(id=sentinel.deviceid)
        datamap = {"id": sentinel.deviceid}
        ret = _validate_datamap(
            device,
            datamap,
            None,
            sentinel.compname,
            sentinel.modname,
            "parentId",
        )
        t.assertIsInstance(ret, IncrementalDataMap)
        t.assertEqual(ret.id, sentinel.deviceid)
        t.assertEqual(ret.modname, sentinel.modname)
        t.assertEqual(ret.path, sentinel.compname)


class Test_process_relationshipmap(BaseTestCase):
    @patch("{src}._get_relmap_target".format(**PATH), autospec=True)
    def test_missing_relname(t, _get_relmap_target):
        """Returns None if the parent device does not have the specified
        relationship
        """
        parent_device = Mock(
            name="parent_device",
            spec_set=[
                "id",
                "relname",
            ],
            relname="relationshipname",
            id="pid",
        )
        _get_relmap_target.return_value = parent_device
        relmap = Mock(name="relmap")
        relmap.relname = "relationshipname"

        ret = _process_relationshipmap(relmap, parent_device)

        t.assertIsNone(ret, None)

    @patch("{src}._get_relationshipmap_diff".format(**PATH), autospec=True)
    def test_process_relationshipmap(t, _get_relationshipmap_diff):
        device = Mock(name="device")
        relmap = RelationshipMap(
            relname="interfaces",
            modname="Products.ZenModel.IpInterface",
        )
        om1 = ObjectMap({"id": "eth0"})
        om2 = ObjectMap({"id": "eth1"})
        relmap.maps = [
            om1,
            om2,
        ]

        processed = _process_relationshipmap(relmap, device)

        t.assertNotEqual(id(relmap), id(processed))
        t.assertEqual(len(processed.maps), 2)
        t.assertIsNot(relmap.maps[0], processed.maps[0])
        t.assertIsNot(relmap.maps[1], processed.maps[1])
        for omap in processed.maps:
            t.assertEqual(omap.relname, processed.relname)
            t.assertEqual(omap.parent, processed._parent)
        t.assertEqual(processed._diff, _get_relationshipmap_diff.return_value)

    @patch("{src}._get_relationshipmap_diff".format(**PATH), autospec=True)
    def test_handles_duplicate_ids(t, _get_relationshipmap_diff):
        """If a relationshipmap contains objects with duplicate ID's
        those subsequent objects are given id = id_n
        """
        device = Mock(name="device")

        om1 = ObjectMap({"id": "eth0"})
        om2 = ObjectMap({"id": "eth0"})
        om3 = ObjectMap({"id": "eth0"})
        objmaps = [
            om1,
            om2,
            om3,
        ]

        relmap = RelationshipMap(
            relname="interfaces",
            modname="Products.ZenModel.IpInterface",
            objmaps=objmaps,
        )

        processed = _process_relationshipmap(relmap, device)

        t.assertEqual(len(processed.maps), 3)
        t.assertEqual(om1.id, "eth0")
        t.assertEqual(processed.maps[0].id, "eth0")
        t.assertEqual(om2.id, "eth0")
        t.assertEqual(processed.maps[1].id, "eth0_2")
        t.assertEqual(om3.id, "eth0")
        t.assertEqual(processed.maps[2].id, "eth0_3")


class Test__get_relationshipmap_diff(BaseTestCase):
    def setUp(t):
        super(Test__get_relationshipmap_diff, t).setUp()
        current_ids = ["id1", "id2", "id3"]
        relname = "relationship"
        t.object_1 = Mock(id="id1")
        t.object_2 = Mock(id="id2")
        t.relationship = Mock(
            name=relname, spec_set=["objectIdsAll", "_getOb"]
        )
        t.relationship.objectIdsAll.return_value = current_ids
        t.relationship._getOb.side_effect = [t.object_1, t.object_2]
        t.relmap = MagicMock(
            RelationshipMap, name="object_map", relname=relname, id="device_id"
        )
        t.objmaps = [Mock(id="id3"), Mock(id="id4")]
        t.relmap.__iter__.return_value = t.objmaps
        t.device = Mock(
            name="device",
            id=t.relmap.id,
            spec_set=["id", t.relmap.relname, "removeRelation"],
        )
        setattr(t.device, t.relmap.relname, t.relationship)

    def test_remove_from_relationship(t):
        t.object_1.isLockedFromDeletion.return_value = False
        t.object_2.isLockedFromDeletion.return_value = False
        ret = _get_relationshipmap_diff(t.device, t.relmap.relname, t.objmaps)

        t.relationship._getOb.assert_called_with("id1")
        t.assertEqual(ret, {"removed": [t.object_1, t.object_2], "locked": []})

    def test_does_not_remove_locked_devices(t):
        t.object_1.isLockedFromDeletion.return_value = False
        t.object_2.isLockedFromDeletion.return_value = True
        ret = _get_relationshipmap_diff(t.device, t.relmap.relname, t.objmaps)

        t.relationship._getOb.assert_called_with("id1")
        t.assertEqual(ret, {"removed": [t.object_1], "locked": [t.object_2]})


class Test_get_relationship_ids(BaseTestCase):
    def test__get_relationship_ids(t):
        relname = "relationship_name"
        relationship = Mock(name="relatinoship")
        relationship.objectIdsAll.return_value = ["r1", "r2", "r2", "r3"]
        device = Mock(name="Device")
        setattr(device, relname, relationship)

        ret = _get_relationship_ids(device, relname)

        t.assertEqual(ret, set(["r1", "r2", "r3"]))


class Test__get_objmap_target(BaseTestCase):
    def test__get_objmap_target(t):
        device = Mock(name="device")
        relname = "relationship_name"
        relationship = device.relationship_name
        relationship._getOb.return_value = sentinel.object
        object_map = ObjectMap({"id": "object_id", "_relname": relname})

        ret = _get_objmap_target(device, object_map)

        relationship._getOb.assert_called_with(object_map.id)
        t.assertEqual(ret, sentinel.object)

    def test__get_objmap_target_component(t):
        device = Mock(
            name="device", spec_set=["component_name", "id", "getObjByPath"]
        )
        device.getObjByPath.return_value = sentinel.component
        object_map = Mock(
            name="object_map",
            spec_set=["compname", "_relname", "_target"],
            compname="component_name",
            _relname="relationship_name",
        )

        ret = _get_objmap_target(device, object_map)

        device.getObjByPath.assert_called_with("component_name")
        t.assertEqual(ret, sentinel.component)


class Test__clone_datamap(BaseTestCase):
    def test_RelationshipMap(t):
        relname = "rel"
        compname = "comp"
        objmaps = [{"a": 1}, {"b": 2}]
        parentId = "parent"
        plugin_name = "plugin"

        original = RelationshipMap(
            relname=relname,
            compname=compname,
            objmaps=objmaps,
            parentId=parentId,
            plugin_name=plugin_name,
        )
        o_om1 = original.maps[0]
        o_om2 = original.maps[1]

        clone = _clone_datamap(original)

        t.assertIsNot(original, clone)
        t.assertEqual(original.relname, clone.relname)
        t.assertEqual(original.compname, clone.compname)
        t.assertEqual(original.parentId, clone.parentId)
        t.assertEqual(original.plugin_name, clone.plugin_name)

        c_om1 = clone.maps[0]
        t.assertIsNot(o_om1, c_om1)
        t.assertTrue(hasattr(c_om1, "a"))
        t.assertEqual(o_om1.a, c_om1.a)

        c_om2 = clone.maps[1]
        t.assertIsNot(o_om2, c_om2)
        t.assertTrue(hasattr(c_om2, "b"))
        t.assertEqual(o_om2.b, c_om2.b)

    def test_IncrementalDataMap(t):
        classname = "class"
        compname = "comp"
        plugin_name = "plugin"
        device = Device(id="device")
        device.comp = Mock(name="comp")
        device.dmd = Mock(name="dmd")

        om = ObjectMap(
            data={"a": 1},
            compname=compname,
            classname=classname,
            plugin_name=plugin_name,
        )
        original = IncrementalDataMap(device, om)

        clone = _clone_datamap(original)

        t.assertIsNot(original, clone)
        t.assertEqual(original.path, clone.path)
        t.assertEqual(original.modname, clone.modname)
        t.assertEqual(original.classname, clone.classname)
        t.assertEqual(original.parent, clone.parent)
        t.assertEqual(original.relname, clone.relname)
        t.assertEqual(original.target, clone.target)
        t.assertEqual(original.directive, clone.directive)
        t.assertSequenceEqual(
            list(original.iteritems()),
            list(clone.iteritems()),
        )

    def test_ObjectMap(t):
        classname = "class"
        compname = "comp"
        plugin_name = "plugin"
        original = ObjectMap(
            data={"a": 1},
            compname=compname,
            classname=classname,
            plugin_name=plugin_name,
        )

        clone = _clone_datamap(original)

        t.assertIsNot(original, clone)
        t.assertEqual(original.classname, clone.classname)
        t.assertEqual(original.compname, clone.compname)
        t.assertEqual(original.plugin_name, clone.plugin_name)
        t.assertDictEqual(dict(original.items()), dict(clone.items()))

    def test_dict(t):
        original = {"a": 1}
        clone = _clone_datamap(original)

        t.assertIsNot(original, clone)
        t.assertDictEqual(dict(original.items()), dict(clone.items()))


##############################################################################
# Apply Changes
##############################################################################


class Test__remove_relationship(BaseTestCase):
    def test_remove_object_from_devices_relationship(t):
        device = Mock(name="device", spec_set=["removeRelation"])
        ret = _remove_relationship(device, sentinel.relname, sentinel.obj)
        device.removeRelation.assert_called_with(
            sentinel.relname, sentinel.obj
        )
        t.assertEqual(ret, True)

    def test_remove_missing_object(t):
        device = Mock(
            name="device",
            spec_set=["removeRelation"],
            removeRelation=Mock(side_effect=AttributeError()),
        )

        ret = _remove_relationship(device, sentinel.relname, sentinel.obj)

        device.removeRelation.assert_called_with(
            sentinel.relname, sentinel.obj
        )
        t.assertEqual(ret, False)


class Test__create_object(BaseTestCase):
    def setUp(t):
        super(Test__create_object, t).setUp()
        patches = [
            "importClass",
        ]

        for target in patches:
            patcher = patch("{src}.{}".format(target, **PATH), autospec=True)
            setattr(t, target, patcher.start())
            t.addCleanup(patcher.stop)

        t.new_object = sentinel.new_object
        t.constructor = Mock(name="constructor", return_value=t.new_object)
        t.importClass.return_value = t.constructor

    def test__create_object(t):
        objmap = ObjectMap(
            {"id": "deviceid"}, modname="py.module.name", classname="ClassName"
        )

        ret = _create_object(objmap)

        t.importClass.assert_called_with(objmap.modname, objmap.classname)
        t.constructor.assert_called_with(objmap.id)
        t.assertEqual(ret, t.new_object)

    def test_without_id(t):
        objmap = ObjectMap({}, modname="py.module.name", classname="ClassName")

        ret = _create_object(objmap, sentinel.parent_device)

        t.importClass.assert_called_with(objmap.modname, objmap.classname)
        t.constructor.assert_called_with(sentinel.parent_device, objmap)
        t.assertEqual(ret, t.new_object)

    def test_from_parent(t):
        objmap = ObjectMap({}, modname="py.module.name", classname="ClassName")
        objmap._parent = sentinel.parent

        ret = _create_object(objmap)

        t.importClass.assert_called_with(objmap.modname, objmap.classname)
        t.constructor.assert_called_with(sentinel.parent, objmap)
        t.assertEqual(ret, t.new_object)

    def test_failure(t):
        """requires object_map.id or a parent device"""
        objmap = ObjectMap({}, modname="py.module.name", classname="ClassName")
        ret = _create_object(objmap)
        t.assertIsNone(ret)
