##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import unittest

from mock import patch

from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class DaemonStatsTest(BaseTestCase):
    """Test the DaemonStats"""

    @patch("Products.ZenUtils.DaemonStats.cc_config", autospec=True)
    def testDaemonsTagsServiceId(self, _cc):
        _cc.service_id = "ID"
        _cc.tenant_id = "foo"
        _cc.instance_id = "bar"
        daemon_stats = DaemonStats()

        daemon_stats.config("name", "monitor", None, None, None)
        self.assertEqual(
            {
                "daemon": "name",
                "instance": "bar",
                "internal": True,
                "monitor": "monitor",
                "metricType": "type",
                "serviceId": "ID",
                "tenantId": "foo",
            },
            daemon_stats._tags("type"),
        )

    @patch("Products.ZenUtils.DaemonStats.cc_config", autospec=True)
    def testDaemonsDoesNotTagServiceId(self, _cc):
        _cc.is_serviced = False
        _cc.service_id = ""
        daemon_stats = DaemonStats()

        daemon_stats.config("name", "monitor", None, None, None)
        self.assertEqual(
            {
                "daemon": "name",
                "internal": True,
                "monitor": "monitor",
                "metricType": "type",
            },
            daemon_stats._tags("type"),
        )


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(DaemonStatsTest),))


if __name__ == "__main__":
    unittest.main(defaultTest="test_suite")
