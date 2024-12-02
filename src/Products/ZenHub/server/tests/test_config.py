##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from mock import Mock
from unittest import TestCase

from ..config import ModuleObjectConfig


class ModuleObjectConfigTest(TestCase):
    """Test ModuleObjectConfig class."""

    def setUp(self):
        self.source = Mock()
        self.config = ModuleObjectConfig(self.source)

    def test_legacy_metric_priority_map(self):
        self.assertIs(
            self.source.legacy_metric_priority_map,
            self.config.legacy_metric_priority_map,
        )

    def test_priorities(self):
        self.assertIs(self.source.priorities, self.config.priorities)

    def test_pools(self):
        self.assertIs(self.source.pools, self.config.pools)

    def test_executors(self):
        self.assertIs(self.source.executors, self.config.executors)

    def test_routes(self):
        self.assertIs(self.source.routes, self.config.routes)

    def test_modeling_pause_timeout(self):
        self.assertIs(
            self.source.modeling_pause_timeout,
            self.config.modeling_pause_timeout,
        )

    def test_task_max_retries(self):
        self.assertIs(
            self.source.task_max_retries,
            self.config.task_max_retries,
        )

    def test_pbport(self):
        self.assertIs(self.source.pbport, self.config.pbport)

    def test_xmlrpcport(self):
        self.assertIs(self.source.xmlrpcport, self.config.xmlrpcport)
