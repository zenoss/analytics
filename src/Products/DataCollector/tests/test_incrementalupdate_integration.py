##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import transaction

from Products.DataCollector.ApplyDataMap import (
    ApplyDataMap,
    IncrementalDataMap,
)
from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class applyDataMapTests(BaseTestCase):
    def afterSetUp(self):
        """Preparation invoked before each test is run."""
        super(applyDataMapTests, self).afterSetUp()
        self.service = ApplyDataMap()
        self.deviceclass = self.dmd.Devices.createOrganizer("/Test")
        self.device = self.deviceclass.createInstance("test-device")
        self.device.setPerformanceMonitor("localhost")
        self.device.setManageIp("192.0.2.77")
        self.device.index_object()
        transaction.commit()

    def test_updateDevice(self):
        """Test updating device properties."""
        DATA = {"rackSlot": "near-the-top"}
        changed = self.service.applyDataMap(self.device, ObjectMap(DATA))
        self.assertTrue(changed, "update Device failed")
        self.assertEqual("near-the-top", self.device.rackSlot)

        changed = self.service.applyDataMap(self.device, ObjectMap(DATA))
        self.assertFalse(changed, "updateDevice not idempotent")

    def test_updateDeviceHW(self):
        """Test updating device.hw properties."""
        DATA = {
            "compname": "hw",
            "totalMemory": 45097156608,
        }
        changed = self.service.applyDataMap(self.device, ObjectMap(DATA))
        self.assertTrue(changed, "device.hw not changed by first ObjectMap")
        self.assertEqual(45097156608, self.device.hw.totalMemory)

        changed = self.service.applyDataMap(self.device, ObjectMap(DATA))
        self.assertFalse(changed, "update is not idempotent")

    def test_updateComponent_implicit(self):
        """Test updating a component with implicit _add and _remove."""
        # Test implicit add directive
        DATA = {
            "id": "eth0",
            "compname": "os",
            "relname": "interfaces",
            "modname": "Products.ZenModel.IpInterface",
            "speed": 10e9,
        }
        changed = self.service.applyDataMap(self.device, ObjectMap(DATA))
        self.assertTrue(changed, "update failed")

        self.assertEqual(
            1,
            self.device.os.interfaces.countObjects(),
            "wrong number of interfaces created by ObjectMap",
        )

        self.assertEqual(
            10e9,
            self.device.os.interfaces.eth0.speed,
            "eth0.speed not updated by ObjectMap",
        )

        # Test implicit nochange directive
        changed = self.service.applyDataMap(self.device, ObjectMap(DATA))
        self.assertFalse(changed, "update is not idempotent")

    def test_updateComponent_addFalse(self):
        """Test updating a component with _add set to False."""
        DATA = {
            "id": "eth0",
            "compname": "os",
            "relname": "interfaces",
            "modname": "Products.ZenModel.IpInterface",
            "speed": 10e9,
            "_add": False,
        }

        idm = IncrementalDataMap(self.device, ObjectMap(DATA))
        idm._target = self.device  # absolutely incorrect but sufficient here

        changed = self.service.applyDataMap(self.device, idm)
        self.assertFalse(changed, "_add = False resulted in change")

        self.assertEqual(
            0,
            self.device.os.interfaces.countObjects(),
            "ObjectMap with _add = False created a component",
        )

    def test_updatedComponent_removeTrue(self):
        """Test updating a component with _remove or remove set to True."""

        for remove_key in ("_remove", "remove"):
            DATA = {
                "id": "eth0",
                "compname": "os",
                "relname": "interfaces",
                remove_key: True,
            }

            class Parent(object):
                def removeRelation(self, relname, target):
                    raise AttributeError("the interface does not exist")

            idm = IncrementalDataMap(self.device, ObjectMap(DATA))
            idm._target = (
                self.device
            )  # absolutely incorrect but sufficient here
            idm._parent = Parent()

            changed = self.service.applyDataMap(self.device, idm)
            self.assertFalse(changed, "update is not idempotent")

            self.service.applyDataMap(
                self.device,
                ObjectMap(
                    {
                        "id": "eth0",
                        "compname": "os",
                        "relname": "interfaces",
                        "modname": "Products.ZenModel.IpInterface",
                        "speed": 10e9,
                    }
                ),
            )
            self.assertEqual(
                1,
                self.device.os.interfaces.countObjects(),
                "failed to add object",
            )

            changed = self.service.applyDataMap(self.device, ObjectMap(DATA))
            self.assertTrue(changed, "remove object failed")

            self.assertEqual(
                0,
                self.device.os.interfaces.countObjects(),
                "failed to remove component",
            )

    def base_relmap(self):
        return RelationshipMap(
            compname="os",
            relname="interfaces",
            modname="Products.ZenModel.IpInterface",
            objmaps=[
                ObjectMap({"id": "eth0"}),
                ObjectMap({"id": "eth1"}),
            ],
        )

    def test_updateRelationship(self):
        """Test relationship creation."""
        changed = self.service.applyDataMap(self.device, self.base_relmap())
        self.assertTrue(changed, "relationship creation failed")
        self.assertEqual(
            2,
            self.device.os.interfaces.countObjects(),
            "wrong number of interfaces created by first RelationshipMap",
        )

    def test_updateRelationship_is_idempotent(self):
        changed = self.service.applyDataMap(self.device, self.base_relmap())
        self.assertTrue(changed)
        self.assertEqual(2, self.device.os.interfaces.countObjects())

        changed = self.service.applyDataMap(self.device, self.base_relmap())
        self.assertFalse(changed, "RelationshipMap is not idempotent")

    def test_updateRelationship_remove_object(self):
        changed = self.service.applyDataMap(self.device, self.base_relmap())
        self.assertTrue(changed)
        self.assertEqual(2, self.device.os.interfaces.countObjects())

        rm = self.base_relmap()
        rm.maps = rm.maps[:1]

        changed = self.service.applyDataMap(self.device, rm)

        self.assertTrue(changed, "remove related item failed")
        self.assertEquals(
            1,
            self.device.os.interfaces.countObjects(),
            "wrong number of interfaces after trimmed RelationshipMap",
        )

    def test_updateRelationship_remove_all_objects(self):
        changed = self.service.applyDataMap(self.device, self.base_relmap())
        self.assertTrue(changed)
        self.assertEqual(2, self.device.os.interfaces.countObjects())
        rm = self.base_relmap()
        rm.maps = []

        changed = self.service.applyDataMap(self.device, rm)

        self.assertTrue(changed, "failed to remove related objects")
        self.assertEquals(
            0,
            self.device.os.interfaces.countObjects(),
            "wrong number of interfaces after empty RelationshipMap",
        )
