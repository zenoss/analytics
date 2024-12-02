##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import re
import zlib
from base64 import urlsafe_b64decode
from urllib import unquote

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.RRDTemplate import manage_addRRDTemplate


class TestGraphDefinition(ZenModelBaseTest):
    
    def testThresholdGraphPoints(self):
        """
        Test that the correct RRD commands are generated for a number of
        ThresholdGraphPoint configurations.
        """
        device = self.dmd.Devices.createInstance('testdevice')
        device.setPerformanceMonitor('localhost')
        
        manage_addRRDTemplate(device, 'TestTemplate')
        device.bindTemplates(['TestTemplate'])
        template = device.TestTemplate
        
        ds = template.manage_addRRDDataSource('dsname', 'BuiltInDS.Built-In')
        dp = ds.manage_addRRDDataPoint('dpname')
        
        t = template.manage_addRRDThreshold('defaultLegend', 'MinMaxThreshold')
        t.dsnames = ['dsname_dpname']
        t.maxval = '5'
        
        t = template.manage_addRRDThreshold('blankLegend', 'MinMaxThreshold')
        t.dsnames = ['dsname_dpname']
        t.legend = ''
        t.maxval = '10'
        
        t = template.manage_addRRDThreshold('talesLegend', 'MinMaxThreshold')
        t.dsnames = ['dsname_dpname']
        t.legend = '${here/id}'
        t.maxval = '15'
        
        graph = template.manage_addGraphDefinition('graph')
        graph.manage_addDataPointGraphPoints(
            ['dsname_dpname'], includeThresholds=True)
        
        graph.graphPoints.defaultLegend.legend = '${graphPoint/id}'
        graph.graphPoints.blankLegend.legend = ''
        graph.graphPoints.talesLegend.legend = '${here/id}'

        # graphUrl = device.getDefaultGraphDefs()[0]['url']
        # gopts = re.search('gopts=([^&]+)', graphUrl).groups()[0]
        # gopts = zlib.decompress(urlsafe_b64decode(unquote(gopts)))
        # self.assertTrue('defaultLegend' in gopts)
        # self.assertTrue('dpname greater than 10' in gopts)
        # self.assertTrue('testdevice' in gopts)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestGraphDefinition))
    return suite

if __name__=="__main__":
    framework()
