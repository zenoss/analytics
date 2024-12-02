##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import unittest
import json
from Products import Zuul
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.ThresholdGraphPoint import ThresholdGraphPoint
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenModel.GraphDefinition import GraphDefinition
from zenoss.protocols.services import JsonRestServiceClient

class MockRestServiceClient(JsonRestServiceClient):

    def _executeRequest(self, request):
        return 200, '[2]'

class MetricFacadeTest(BaseTestCase):

    def afterSetUp(self):
        super(MetricFacadeTest, self).afterSetUp()
        self.facade = Zuul.getFacade('metric', self.dmd)
        self.facade._client = MockRestServiceClient('http://localhost:8888')

    def testTagBuilder(self):
        dev = self.dmd.Devices.createInstance('device1')
        self.assertTrue(dev.getResourceKey())
        tags = self.facade._buildTagsFromContextAndMetric(dev, 'pepe')
        self.assertIn('key', tags)
        self.assertIn(dev.getResourceKey(), tags['key'])

    def testMetricBuilder(self):
        dev = self.dmd.Devices.createInstance('device1')
        templateFac = Zuul.getFacade('template', self.dmd)
        template = templateFac.addTemplate('test', '/zport/dmd/Devices')._object
        templateFac.addDataSource(template.getPrimaryId(), 'test', 'SNMP')
        metric = template.datasources()[0].datapoints()[0]
        cf = "avg"
        metric = self.facade._buildMetric(dev, metric, cf)
        self.assertEquals(metric[0]['metric'], "device1/test_test")
        self.assertEquals(metric[0]['aggregator'], 'avg')

    def testRequestBuilder(self):
        metric = ["laLoadInt1_laLoadInt1"]
        dev = self.dmd.Devices.createInstance('device1')
        request = self.facade._buildRequest([dev], metric, None, None, "LAST", "1m-avg")
        self.assertEquals(request['returnset'], 'LAST')

    def testMetricServiceGraphDefinitionProjections(self):
        device = self.dmd.Devices.createInstance('test')
        template = RRDTemplate('test')
        self.dmd.Devices.rrdTemplates._setObject('test', template)
        template = self.dmd.Devices.rrdTemplates.test
        template.graphDefs._setObject('test', GraphDefinition('test'))
        graph = template.graphDefs()[0]
        info = Zuul.infos.metricserver.MetricServiceGraphDefinition(graph, device)
        graph.graphPoints._setObject('test', ThresholdGraphPoint('test'))
        self.assertEquals([], info.projections)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(MetricFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
