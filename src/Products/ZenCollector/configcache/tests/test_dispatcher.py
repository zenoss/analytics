##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from unittest import TestCase

from mock import call, patch

from ..dispatcher import DeviceConfigTaskDispatcher, build_device_config


PATH = {"src": "Products.ZenCollector.configcache.dispatcher"}


class DeviceConfigTaskDispatcherTest(TestCase):
    """Test the DeviceConfigTaskDispatcher object."""

    def setUp(t):
        t.class_a = type(
            "a", (object,), {"__module__": "some.path.one", "__name__": "a"}
        )
        t.class_a_name = ".".join((t.class_a.__module__, t.class_a.__name__))
        t.class_b = type(
            "b", (object,), {"__module__": "some.path.two", "__name__": "b"}
        )
        t.class_b_name = ".".join((t.class_b.__module__, t.class_b.__name__))

        t.bctd = DeviceConfigTaskDispatcher((t.class_a, t.class_b))

    @patch.object(build_device_config, "apply_async")
    def test_dispatch_all(t, _apply_async):
        timeout = 100.0
        soft = 100.0
        hard = 110.0
        submitted = 111.0
        monitor = "local"
        device = "linux"
        t.bctd.dispatch_all(monitor, device, timeout, submitted)

        _apply_async.assert_has_calls(
            (
                call(
                    args=(monitor, device, t.class_a_name),
                    kwargs={"submitted": submitted},
                    soft_time_limit=soft,
                    time_limit=hard,
                ),
                call(
                    args=(monitor, device, t.class_b_name),
                    kwargs={"submitted": submitted},
                    soft_time_limit=soft,
                    time_limit=hard,
                ),
            )
        )

    @patch.object(build_device_config, "apply_async")
    def test_dispatch(t, _apply_async):
        timeout = 100.0
        soft = 100.0
        hard = 110.0
        submitted = 111.0
        monitor = "local"
        device = "linux"
        svcname = t.class_a.__module__
        t.bctd.dispatch(svcname, monitor, device, timeout, submitted)

        _apply_async.assert_called_once_with(
            args=(monitor, device, t.class_a_name),
            kwargs={"submitted": submitted},
            soft_time_limit=soft,
            time_limit=hard,
        )

    def test_dispatch_unknown_service(t):
        timeout = 100.0
        monitor = "local"
        device = "linux"
        submitted = 1111.0

        with t.assertRaises(ValueError):
            t.bctd.dispatch("unknown", monitor, device, timeout, submitted)
