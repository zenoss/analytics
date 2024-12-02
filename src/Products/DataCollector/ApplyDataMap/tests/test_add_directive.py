##############################################################################
#
# Copyright (C) Zenoss, Inc. 2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import copy

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from ..applydatamap import ApplyDataMap, ObjectMap

PATH = {"src": "Products.DataCollector.ApplyDataMap.applydatamap"}


class TestImplicitAdd(BaseTestCase):
    """Test ApplyDataMap directives."""

    def afterSetUp(t):
        super(TestImplicitAdd, t).afterSetUp()
        t.om = ObjectMap(
            plugin_name="my-plugin",
            modname="Products.ZenModel.IpInterface",
            data={
                "compname": "os",
                "relname": "interfaces",
                "id": "eth0",
                "speed": 1e3,
            },
        )
        t.adm = ApplyDataMap(t)
        t.device = t.dmd.Devices.createInstance("test-device")

    def afterTearDown(t):
        t.dmd.Devices.removeDevices(("test-device",))
        del t.device
        del t.adm
        super(TestImplicitAdd, t).afterTearDown()

    def test_implicit_update(t):
        result = t.device.applyDataMap(t.om)
        t.assertTrue(result)

    def test_implicit_update_twice_with_same_data(t):
        t.device.applyDataMap(t.om)
        result = t.device.applyDataMap(t.om)
        t.assertFalse(result)


class TestExplicitAdd(BaseTestCase):
    def afterSetUp(t):
        super(TestExplicitAdd, t).afterSetUp()
        t.om1 = ObjectMap(
            plugin_name="my-plugin",
            modname="Products.ZenModel.IpInterface",
            data={
                "compname": "os",
                "relname": "interfaces",
                "id": "eth0",
                "speed": 1e3,
            },
        )
        t.om2 = copy.copy(t.om1)
        t.adm = ApplyDataMap(t)
        t.device = t.dmd.Devices.createInstance("test-device")
        t.device.applyDataMap(t.om1)

    def afterTearDown(t):
        t.dmd.Devices.removeDevices(("test-device",))
        del t.device
        del t.adm
        del t.om2
        del t.om1
        super(TestExplicitAdd, t).afterTearDown()

    def test_implicit_update_with_actual_change(t):
        t.om2.speed = 2e3
        result = t.device.applyDataMap(t.om2)
        t.assertTrue(result)

    def test_explicit_add_true_with_existing_device_no_changes(t):
        t.om2._add = True
        result = t.device.applyDataMap(t.om2)
        t.assertFalse(result)

    def test_explicit_add_false_with_existing_device_no_changes(t):
        t.device.applyDataMap(t.om1)
        result = t.device.applyDataMap(
            ObjectMap(
                plugin_name="my-plugin",
                modname="Products.ZenModel.IpInterface",
                data={
                    "compname": "os",
                    "relname": "interfaces",
                    "id": "eth0",
                    "speed": 1e3,
                    "_add": False,
                },
            )
        )
        t.assertFalse(result)

    def test_explicit_add_false_with_existing_device_with_changes(t):
        t.device.applyDataMap(t.om1)
        result = t.device.applyDataMap(
            ObjectMap(
                plugin_name="my-plugin",
                modname="Products.ZenModel.IpInterface",
                data={
                    "compname": "os",
                    "relname": "interfaces",
                    "id": "eth0",
                    "interfaceName": "xyz",
                    "speed": 2e3,
                    "_add": False,
                },
            )
        )
        t.assertTrue(result)


class TestAddSequence(BaseTestCase):
    """Test ApplyDataMap directives."""

    def afterSetUp(t):
        super(TestAddSequence, t).afterSetUp()
        t.adm = ApplyDataMap(t)
        t.device = t.dmd.Devices.createInstance("test-device")

    def afterTearDown(t):
        t.dmd.Devices.removeDevices(("test-device",))
        del t.device
        del t.adm
        super(TestAddSequence, t).afterTearDown()

    def test_sequence(t):
        om1 = ObjectMap(
            plugin_name="my-plugin",
            modname="Products.ZenModel.IpInterface",
            data={
                "compname": "os",
                "relname": "interfaces",
                "id": "eth0",
                "speed": 1e3,
            },
        )

        result = t.device.applyDataMap(om1)
        t.assertTrue(result)

        result = t.device.applyDataMap(om1)
        t.assertFalse(result)

        result = t.device.applyDataMap(
            ObjectMap(
                plugin_name="my-plugin",
                modname="Products.ZenModel.IpInterface",
                data={
                    "compname": "os",
                    "relname": "interfaces",
                    "id": "eth0",
                    "speed": 2e3,
                },
            )
        )
        t.assertTrue(result)

        result = t.device.applyDataMap(
            ObjectMap(
                plugin_name="my-plugin",
                modname="Products.ZenModel.IpInterface",
                data={
                    "compname": "os",
                    "relname": "interfaces",
                    "id": "eth0",
                    "speed": 2e3,
                    "_add": True,
                },
            )
        )
        t.assertFalse(result)

        result = t.device.applyDataMap(
            ObjectMap(
                plugin_name="my-plugin",
                modname="Products.ZenModel.IpInterface",
                data={
                    "compname": "os",
                    "relname": "interfaces",
                    "id": "eth0",
                    "speed": 2e3,
                    "_add": False,
                },
            )
        )
        t.assertFalse(result)

        result = t.device.applyDataMap(
            ObjectMap(
                plugin_name="my-plugin",
                modname="Products.ZenModel.IpInterface",
                data={
                    "compname": "os",
                    "relname": "interfaces",
                    "id": "eth0",
                    "speed": 3e3,
                    "_add": False,
                },
            )
        )
        t.assertTrue(result)
