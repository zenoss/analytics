##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from ..propertymap import DevicePropertyMap
from ..constants import Constants


class TestDevicePropertyMapTTLMakers(BaseTestCase):
    ttl_overrides = {
        "Server/Linux": 16320,
        "Server/Linux/linux0": 68000,
        "Power": 8000,
        "Network": 32000,
    }

    min_ttl_overrides = {
        "Server/Linux/linux0": 300,
    }

    def afterSetUp(t):
        super(TestDevicePropertyMapTTLMakers, t).afterSetUp()

        t.dmd.Devices.createOrganizer("/Server/Linux")
        t.dmd.Devices.createOrganizer("/Server/Cmd")
        t.dmd.Devices.createOrganizer("/Network")
        t.dmd.Devices.createOrganizer("/Power")

        t.dmd.Devices.Server.Linux.setZenProperty(
            Constants.device_time_to_live_id, t.ttl_overrides["Server/Linux"]
        )
        t.dmd.Devices.Power.setZenProperty(
            Constants.device_time_to_live_id, t.ttl_overrides["Power"]
        )
        t.dmd.Devices.Network.setZenProperty(
            Constants.device_time_to_live_id, t.ttl_overrides["Network"]
        )

        t.linux_dev = t.dmd.Devices.Server.Linux.createInstance("linux0")
        t.linux_dev.setZenProperty(
            Constants.device_time_to_live_id,
            t.ttl_overrides["Server/Linux/linux0"],
        )
        t.linux_dev.setZenProperty(
            Constants.device_minimum_time_to_live_id,
            t.min_ttl_overrides["Server/Linux/linux0"],
        )

        t.cmd_dev = t.dmd.Devices.Server.Cmd.createInstance("cmd0")

    def test_make_ttl_map(t):
        ttlmap = DevicePropertyMap.make_ttl_map(t.dmd.Devices)

        pathid = t.dmd.Devices.Server.getPrimaryId()
        expected = Constants.device_time_to_live_value
        actual = ttlmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Server.Linux.getPrimaryId()
        expected = t.ttl_overrides["Server/Linux"]
        actual = ttlmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Server.Cmd.getPrimaryId()
        expected = Constants.device_time_to_live_value
        actual = ttlmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Power.getPrimaryId()
        expected = t.ttl_overrides["Power"]
        actual = ttlmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Network.getPrimaryId()
        expected = t.ttl_overrides["Network"]
        actual = ttlmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.linux_dev.getPrimaryId()
        expected = t.ttl_overrides["Server/Linux/linux0"]
        actual = ttlmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.cmd_dev.getPrimaryId()
        expected = Constants.device_time_to_live_value
        actual = ttlmap.get(pathid)
        t.assertEqual(expected, actual)

    def test_make_min_ttl_map(t):
        minttlmap = DevicePropertyMap.make_minimum_ttl_map(t.dmd.Devices)

        pathid = t.dmd.Devices.Server.getPrimaryId()
        expected = Constants.device_minimum_time_to_live_value
        actual = minttlmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.linux_dev.getPrimaryId()
        expected = t.min_ttl_overrides["Server/Linux/linux0"]
        actual = minttlmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.cmd_dev.getPrimaryId()
        expected = Constants.device_minimum_time_to_live_value
        actual = minttlmap.get(pathid)
        t.assertEqual(expected, actual)

    def test_large_min_ttl_value(t):
        minttl_value = Constants.device_time_to_live_value + 100
        t.cmd_dev.setZenProperty(
            Constants.device_minimum_time_to_live_id, minttl_value
        )

        minttlmap = DevicePropertyMap.make_minimum_ttl_map(t.dmd.Devices)

        pathid = t.cmd_dev.getPrimaryId()
        expected = Constants.device_time_to_live_value + 100
        actual = minttlmap.get(pathid)
        t.assertEqual(expected, actual)


class TestDevicePropertyMapPendingTimeout(BaseTestCase):
    pending_overrides = {
        "Server/Linux": 500,
        "Server/Linux/linux0": 600,
        "Power": 800,
        "Network": 850,
    }

    def afterSetUp(t):
        super(TestDevicePropertyMapPendingTimeout, t).afterSetUp()

        t.dmd.Devices.createOrganizer("/Server/Linux")
        t.dmd.Devices.createOrganizer("/Server/Cmd")
        t.dmd.Devices.createOrganizer("/Network")
        t.dmd.Devices.createOrganizer("/Power")

        t.dmd.Devices.Server.Linux.setZenProperty(
            Constants.device_pending_timeout_id,
            t.pending_overrides["Server/Linux"],
        )
        t.dmd.Devices.Power.setZenProperty(
            Constants.device_pending_timeout_id, t.pending_overrides["Power"]
        )
        t.dmd.Devices.Network.setZenProperty(
            Constants.device_pending_timeout_id, t.pending_overrides["Network"]
        )

        t.linux_dev = t.dmd.Devices.Server.Linux.createInstance("linux0")
        t.linux_dev.setZenProperty(
            Constants.device_pending_timeout_id,
            t.pending_overrides["Server/Linux/linux0"],
        )

        t.cmd_dev = t.dmd.Devices.Server.Cmd.createInstance("cmd0")

    def test_make_pending_timeout_map(t):
        pendingmap = DevicePropertyMap.make_pending_timeout_map(t.dmd.Devices)

        pathid = t.dmd.Devices.Server.getPrimaryId()
        expected = Constants.device_pending_timeout_value
        actual = pendingmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Server.Linux.getPrimaryId()
        expected = t.pending_overrides["Server/Linux"]
        actual = pendingmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Server.Cmd.getPrimaryId()
        expected = Constants.device_pending_timeout_value
        actual = pendingmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Power.getPrimaryId()
        expected = t.pending_overrides["Power"]
        actual = pendingmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Network.getPrimaryId()
        expected = t.pending_overrides["Network"]
        actual = pendingmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.linux_dev.getPrimaryId()
        expected = t.pending_overrides["Server/Linux/linux0"]
        actual = pendingmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.cmd_dev.getPrimaryId()
        expected = Constants.device_pending_timeout_value
        actual = pendingmap.get(pathid)
        t.assertEqual(expected, actual)


class TestDevicePropertyMapBuildTimeout(BaseTestCase):
    build_overrides = {
        "Server/Linux": 500,
        "Server/Linux/linux0": 600,
        "Power": 800,
        "Network": 850,
    }

    def afterSetUp(t):
        super(TestDevicePropertyMapBuildTimeout, t).afterSetUp()

        t.dmd.Devices.createOrganizer("/Server/Linux")
        t.dmd.Devices.createOrganizer("/Server/Cmd")
        t.dmd.Devices.createOrganizer("/Network")
        t.dmd.Devices.createOrganizer("/Power")

        t.dmd.Devices.Server.Linux.setZenProperty(
            Constants.device_build_timeout_id,
            t.build_overrides["Server/Linux"],
        )
        t.dmd.Devices.Power.setZenProperty(
            Constants.device_build_timeout_id, t.build_overrides["Power"]
        )
        t.dmd.Devices.Network.setZenProperty(
            Constants.device_build_timeout_id, t.build_overrides["Network"]
        )

        t.linux_dev = t.dmd.Devices.Server.Linux.createInstance("linux0")
        t.linux_dev.setZenProperty(
            Constants.device_build_timeout_id,
            t.build_overrides["Server/Linux/linux0"],
        )

        t.cmd_dev = t.dmd.Devices.Server.Cmd.createInstance("cmd0")

    def test_make_build_timeout_map(t):
        buildmap = DevicePropertyMap.make_build_timeout_map(t.dmd.Devices)

        pathid = t.dmd.Devices.Server.getPrimaryId()
        expected = Constants.device_build_timeout_value
        actual = buildmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Server.Linux.getPrimaryId()
        expected = t.build_overrides["Server/Linux"]
        actual = buildmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Server.Cmd.getPrimaryId()
        expected = Constants.device_build_timeout_value
        actual = buildmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Power.getPrimaryId()
        expected = t.build_overrides["Power"]
        actual = buildmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.dmd.Devices.Network.getPrimaryId()
        expected = t.build_overrides["Network"]
        actual = buildmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.linux_dev.getPrimaryId()
        expected = t.build_overrides["Server/Linux/linux0"]
        actual = buildmap.get(pathid)
        t.assertEqual(expected, actual)

        pathid = t.cmd_dev.getPrimaryId()
        expected = Constants.device_build_timeout_value
        actual = buildmap.get(pathid)
        t.assertEqual(expected, actual)
