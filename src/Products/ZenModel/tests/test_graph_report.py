##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenModel import GraphReport as graph_report
from Products.ZenTestCase import BaseTestCase as test_base


class TestGraphReport(test_base.BaseTestCase):

    def test_component_not_belong_to_device(self):
        # FIXME: Use mock library here
        orig = graph_report.getObjByPath

        class getObjByPathMock(object):
            def __init__(self):
                self.calls = []

            def getObjByPath(self, dev, cPath):
                self.calls.append((dev.getId(), cPath))

        get_obj_mock = getObjByPathMock()
        graph_report.getObjByPath = get_obj_mock.getObjByPath
        self.addCleanup(setattr, graph_report, 'getObjByPath', orig)

        graph = graph_report.GraphReport('test_id')
        graph.dmd = self.dmd

        self.dmd.Devices.createInstance('test_dev_a')
        self.dmd.Devices.createInstance('test_dev_b')

        graph.manage_addGraphElement(
            deviceIds=['test_dev_a', 'test_dev_b'],
            componentPaths=['/test_dev_a/eth0', '/test_dev_b/eth0'])

        self.assertIn(('test_dev_a', '/test_dev_a/eth0'), get_obj_mock.calls)
        self.assertIn(('test_dev_b', '/test_dev_b/eth0'), get_obj_mock.calls)
        self.assertNotIn(('test_dev_a', '/test_dev_b/eth0'), get_obj_mock.calls)
        self.assertNotIn(('test_dev_b', '/test_dev_a/eth0'), get_obj_mock.calls)
