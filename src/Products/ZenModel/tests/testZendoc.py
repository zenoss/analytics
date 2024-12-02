##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import random
import zope.component
from Products.ZenModel.interfaces import IZenDocProvider
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.tests.RRDTestUtils import createTemplate
from Products.ZenModel.ZenModelBase import ZenModelBase
from Products.ZenModel.RRDDataSource import SimpleRRDDataSource
from Products.ZenModel.RRDDataPoint import RRDDataPoint


class TestZenModelClass(ZenModelBase):
    pass

class StringWriter(object):
    
    def __init__(self):
        self._string = ''
    
    def write(self, out):
        self._string += out

    def toString(self):
        return self._string

class TestZendoc(ZenModelBaseTest):

    def testRegistration(self):
        testObject = TestZenModelClass()
        adapter = zope.component.queryAdapter( testObject, IZenDocProvider )
        self.assert_( adapter is not None )

    def testReadWriteZendoc(self):
        TEST_ZENDOC_STRING = "test_zendoc_string_%s" % str( random.random() )
        targetObj = TestZenModelClass()
        adapter = zope.component.queryAdapter( targetObj, IZenDocProvider )
        self.assert_(adapter is not None)
        self.assertEqual( '', adapter.getZendoc(), "Events zendoc not empty" )
        adapter.setZendoc( TEST_ZENDOC_STRING )
        adapter2 = zope.component.queryAdapter( targetObj, IZenDocProvider )
        self.assertEqual( TEST_ZENDOC_STRING, adapter2.getZendoc(),
                          'Read zendoc value different from written value' )

    def testSingleDatapointDataSourceZendoc(self):
        # If this is a single datapoint datasource, the zendoc should
        # be held on the single datapoint
        rndm = str( random.random() )
        TEST_ZENDOC_STRING = "test_zendoc_string_%s" % rndm
        template = createTemplate( self.dmd, 'test_template_%s' % rndm,
                                   {'ds1':[]} )
        targetDS = template.datasources()[0]
        targetDP = targetDS.datapoints()[0]
        dsAdapter = zope.component.queryAdapter( targetDS, IZenDocProvider )
        dpAdapter = zope.component.queryAdapter( targetDP, IZenDocProvider )
        self.assert_(dsAdapter is not None)
        self.assert_(dpAdapter is not None)
        self.assertEqual( '', dsAdapter.getZendoc(), "Initial zendoc not empty" )
        self.assertEqual( '', dpAdapter.getZendoc(), "Initial zendoc not empty" )
        dsAdapter.setZendoc( TEST_ZENDOC_STRING )

        dpAdapter2 = zope.component.queryAdapter( targetDP, IZenDocProvider )
        self.assertEqual( TEST_ZENDOC_STRING, dpAdapter2.getZendoc(),
                          'Sole datapoint zendoc different ' +
                          'from value written to datasource' )
        dsAdapter2 = zope.component.queryAdapter( targetDS, IZenDocProvider )
        self.assertEqual( TEST_ZENDOC_STRING, dsAdapter2.getZendoc(),
                          'Sole datapoint zendoc different ' +
                          'from value written to datasource' )

    def testMulipleDatapointDataSourceZendoc(self):
        # If there are multiple datapoints, the zendoc should be on
        # the datasourcestr( random.random() )
        rndm = str( random.random() )
        TEST_ZENDOC_STRING = "test_zendoc_string_%s" % rndm
        template = createTemplate( self.dmd, 'test_template_%s' % rndm,
                                   {'ds1':['dp1','dp2']} )
        targetDS = template.datasources()[0]
        dsAdapter = zope.component.queryAdapter( targetDS, IZenDocProvider )
        self.assert_(dsAdapter is not None)
        self.assertEqual( '', dsAdapter.getZendoc(), "Initial zendoc not empty" )
        for targetDP in targetDS.datapoints():
            dpAdapter = zope.component.queryAdapter( targetDP, IZenDocProvider )
            self.assert_(dpAdapter is not None)
            self.assertEqual( '', dpAdapter.getZendoc(), "Initial zendoc not empty" )

        dsAdapter.setZendoc( TEST_ZENDOC_STRING )

        for targetDP in targetDS.datapoints():
            dpAdapter = zope.component.queryAdapter( targetDP, IZenDocProvider )
            self.assertEqual( '', dpAdapter.getZendoc(),
                              'Multiple datapoint zendoc should not be set' )
        dsAdapter2 = zope.component.queryAdapter( targetDS, IZenDocProvider )
        self.assertEqual( TEST_ZENDOC_STRING, dsAdapter2.getZendoc(),
                          'Multiple datapoint datasource has incorrect' +
                          ' zendoc' )

    def testExport(self):
        rndm = str( random.random() )
        TEST_ZENDOC_STRING = "test_zendoc_string_%s" % rndm
        template = createTemplate( self.dmd, 'test_template_%s' % rndm )
        adapter = zope.component.queryAdapter( template, IZenDocProvider )
        adapter.setZendoc( TEST_ZENDOC_STRING )
        writer = StringWriter()
        adapter.exportZendoc(writer)
        xml = writer.toString()
        self.assertEqual( "<property id='zendoc' type='string'>\n%s\n</property>\n"
                          % TEST_ZENDOC_STRING, xml )

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZendoc))
    return suite

if __name__=="__main__":
    framework()
