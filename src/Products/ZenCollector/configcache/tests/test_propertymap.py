##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from unittest import TestCase

from ..propertymap import DevicePropertyMap


class EmptyDevicePropertyMapTest(TestCase):
    """Test an empty DevicePropertyMap object."""

    def setUp(t):
        t.dpm = DevicePropertyMap({}, None)

    def tearDown(t):
        del t.dpm

    def test_get(t):
        t.assertIsNone(t.dpm.get("/zport/dmd/Devices"))

    def test_smallest_value(t):
        t.assertIsNone(t.dpm.smallest_value())


class DevicePropertyMapTest(TestCase):
    """Test a DevicePropertyMap object."""

    mapping = {
        "/zport/dmd/Devices": 10,
        "/zport/dmd/Devices/Server/Linux": 11,
        "/zport/dmd/Devices/Server/SSH/Linux/devices/my-device": 12,
        "/zport/dmd/Devices/vSphere": 13,
        "/zport/dmd/Devices/Network": 14,
    }

    _default = 15

    def setUp(t):
        t.dpm = DevicePropertyMap(t.mapping, t._default)

    def tearDown(t):
        del t.dpm

    def test_minimal_match(t):
        value = t.dpm.get("/zport/dmd/Devices/Server-stuff/devices/dev2")
        t.assertEqual(10, value)

    def test_get_exact_match(t):
        value = t.dpm.get(
            "/zport/dmd/Devices/Server/SSH/Linux/devices/my-device"
        )
        t.assertEqual(12, value)

    def test_get_best_match(t):
        value = t.dpm.get("/zport/dmd/Devices/Server/Linux/devices/dev3")
        t.assertEqual(11, value)

    def test_no_match(t):
        value = t.dpm.get("/Devices")
        t.assertEqual(t._default, value)

    def test_empty_string(t):
        value = t.dpm.get("")
        t.assertEqual(t._default, value)

    def test_smallest_value(t):
        value = t.dpm.smallest_value()
        t.assertEqual(10, value)

    def test_uid_is_None(t):
        value = t.dpm.get(None)
        t.assertEqual(t._default, value)
