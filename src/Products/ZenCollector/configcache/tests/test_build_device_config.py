##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import mock

from unittest import TestCase

from Products.Jobber.tests.utils import RedisLayer
from Products.ZenCollector.services.config import DeviceProxy

from ..cache import DeviceKey, DeviceRecord
from ..cache.storage import DeviceConfigStore
from ..tasks.deviceconfig import buildDeviceConfig

PATH = {
    "zenjobs": "Products.Jobber.zenjobs",
    "task": "Products.ZenCollector.configcache.tasks.deviceconfig",
}


class TestBuildDeviceConfig(TestCase):
    layer = RedisLayer

    def setUp(t):
        t.device_name = "qadevice"
        t.device_uid = "/zport/dmd/Devices/Server/Linux/devices/qadevice"
        t.store = DeviceConfigStore(t.layer.redis)

    def tearDown(t):
        del t.store

    @mock.patch("{task}.time".format(**PATH), autospec=True)
    @mock.patch("{task}.createObject".format(**PATH), autospec=True)
    @mock.patch("{task}.resolve".format(**PATH), autospec=True)
    def test_no_config_built(t, _resolve, _createObject, _time):
        monitor = "localhost"
        clsname = "Products.ZenHub.services.PingService.PingService"
        svcname = clsname.rsplit(".", 1)[0]
        submitted = 123456.34
        svcclass = mock.Mock()
        svc = mock.MagicMock()
        dmd = mock.Mock()
        log = mock.Mock()
        dvc = mock.Mock()
        key = DeviceKey(svcname, monitor, t.device_name)

        _createObject.return_value = t.store
        _resolve.return_value = svcclass
        svcclass.return_value = svc
        svc.remote_getDeviceConfigs.return_value = []
        dmd.Devices.findDeviceByIdExact.return_value = dvc
        dvc.getPrimaryId.return_value = t.device_uid
        _time.return_value = submitted + 10
        dvc.getZ.return_value = 1000

        t.store.set_pending((key, submitted))

        buildDeviceConfig(dmd, log, monitor, t.device_name, clsname, submitted)

        status = t.store.get_status(key)
        t.assertIsNone(status)

    @mock.patch("{task}.createObject".format(**PATH), autospec=True)
    @mock.patch("{task}.resolve".format(**PATH), autospec=True)
    def test_device_not_found(t, _resolve, _createObject):
        monitor = "localhost"
        clsname = "Products.ZenHub.services.PingService.PingService"
        svcname = clsname.rsplit(".", 1)[0]
        submitted = 123456.34
        svcclass = mock.Mock()
        svc = mock.MagicMock()
        dmd = mock.Mock()
        log = mock.Mock()
        key = DeviceKey(svcname, monitor, t.device_name)

        _createObject.return_value = t.store
        _resolve.return_value = svcclass
        svcclass.return_value = svc
        dmd.Devices.findDeviceByIdExact.return_value = None

        t.store.set_pending((key, submitted))

        buildDeviceConfig(dmd, log, monitor, t.device_name, clsname, submitted)

        status = t.store.get_status(key)
        t.assertIsNone(status)

    @mock.patch("{task}.createObject".format(**PATH), autospec=True)
    @mock.patch("{task}.resolve".format(**PATH), autospec=True)
    def test_device_reidentified(t, _resolve, _createObject):
        # A 're-identified' device will no longer be found in ZODB under its
        # old ID, but a config keyed for the old ID will still exist.
        monitor = "localhost"
        clsname = "Products.ZenHub.services.PingService.PingService"
        svcname = clsname.rsplit(".", 1)[0]
        proxy = DeviceProxy()
        submitted = 123456.34
        record = DeviceRecord.make(
            svcname,
            monitor,
            t.device_name,
            t.device_uid,
            submitted - 300,
            proxy,
        )
        key = record.key
        t.store.add(record)

        svcclass = mock.Mock()
        svc = mock.MagicMock()
        dmd = mock.Mock()
        log = mock.Mock()

        _createObject.return_value = t.store
        _resolve.return_value = svcclass
        svcclass.return_value = svc
        dmd.Devices.findDeviceByIdExact.return_value = None

        t.store.set_pending((key, submitted))

        buildDeviceConfig(dmd, log, monitor, t.device_name, clsname, submitted)

        status = t.store.get_status(key)
        t.assertIsNone(status)
