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
    framework = None                    # quiet pyflakes
    execfile(os.path.join(sys.path[0], 'framework.py'))

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.RRDDataPoint import getDataPointsByAliases    
from Products.ZenModel.RRDDataPointAlias import RRDDataPointAlias
from Products.ZenModel.tests.RRDTestUtils import *


class TestRRDDataPoint(ZenModelBaseTest):

    def testAddAndRemoveAlias(self):
        aliasName, aliasFormula = 'alias1', 'formula1'
        t = createTemplate( self.dmd, 't1' )
        ds0 = t.datasources()[0]
        dp0 = ds0.datapoints()[0]
        dp0.addAlias( aliasName, aliasFormula )
        self.assert_( len( dp0.aliases() ) == 1 )
        alias = dp0.aliases()[0]
        self.assert_( alias.id == aliasName )
        self.assert_( alias.formula == aliasFormula )
        dp0.removeAlias( aliasName )
        self.assert_( len( dp0.aliases() ) == 0 )
        
    def testHasAlias(self):
        aliasName, aliasFormula = 'alias2', 'formula2'
        t = createTemplate( self.dmd, 't2' )
        ds0 = t.datasources()[0]
        dp0 = ds0.datapoints()[0]
        self.assert_( not dp0.hasAlias( aliasName ) )
        dp0.addAlias( aliasName, aliasFormula )
        self.assert_( dp0.hasAlias( aliasName ) )
        self.assert_( not dp0.hasAlias( 'badAliasName' ) )
        dp0.removeAlias( aliasName )
        self.assert_( not dp0.hasAlias( aliasName ) )
        
    def testGetAliasNames(self):
        template = createTemplate( self.dmd, 't3' )
        aliasMap = {
                   ('alias0_1', 'form0_1'):('ds2', 'dp1'),
                   ( 'alias0_2', 'form0_2' ) : ('ds2', 'dp1'),
                   ( 'alias0_3', 'form0_3' ) : ('ds2', 'dp1'  )
                   }
        aliasNames = set( af[0] for af in aliasMap.keys() )
        addAliases( template, aliasMap )

        dp = template.datasources.ds2.datapoints.dp1
        self.assert_( len( dp.aliases() ) == 3 )
        vAliasNames = dp.getAliasNames()
        vAliasNames = set( vAliasNames )
        
        self.assert_( aliasNames == vAliasNames )
        
        
        

    def testGetDatapointsByAliases_NoMatch(self):
        #Templates with no aliases
        template = createTemplate( self.dmd, 'template1' )
        addAliases( template, 
                         {
                          ('alias1_1', 'form1_1'):('ds1', 'dp1'),
                          ( 'alias1_2', 'form1_2' ) : ('ds2', 'dp1'),
                          ( 'alias1_3', 'form1_3' ) : ('ds2', 'dp1'  )
                          } )
        
        dps = getDataPointsByAliases( self.dmd, ['badalias1','badalias2'] )
        self.assert_( len( list( dps ) ) == 0 )
        removeTemplate( self.dmd, 'template1')
        
    def testGetDatapointsByAliases_OneAliasPerDatapoint(self):
        #Templates with dps with one alias
        template = createTemplate( self.dmd, 'template2' )
        aliasMap = {
                    ('alias2_1', 'form2_1') : ('ds1', 'dp1'),
                    ('alias2_2', 'form2_2') : ('ds2', 'dp1')
                    }
        addAliases( template, aliasMap )
        searchAliases = ['alias2_1','alias2_2']
        gen = getDataPointsByAliases( self.dmd, searchAliases )
        aliasDatapointMap = dict( gen )
        self.assert_( len( aliasDatapointMap.values() ) == 2)
        for foundAlias, datapoint in aliasDatapointMap.iteritems():
            self.assert_( foundAlias.id in searchAliases )
            assertAliasDatapointInMap( self, foundAlias, datapoint, aliasMap )

        removeTemplate( self.dmd, 'template2' )
        
    def testGetDatapointsByAliases_MultipleAliasesPerDatapoint(self):
        #Templates with dps with multiple aliases
        #import pydevd;pydevd.settrace()
        template = createTemplate( self.dmd, 'template3' )
        aliasMap = {
                    ('alias3_1', 'form3_1') : ('ds1', 'dp1'),
                    ('alias3_2', 'form3_2') : ('ds2', 'dp1'),
                    ('alias3_3', 'form3_3') : ('ds2', 'dp1')
                    }
        addAliases( template, aliasMap )
        
        searchAliases = ['alias3_1','alias3_2']
        gen = getDataPointsByAliases( self.dmd, searchAliases )

        aliasDatapointMap = dict( gen )
        self.assert_( len( aliasDatapointMap.values() ) == 2)
        for foundAlias, datapoint in aliasDatapointMap.iteritems():
            self.assert_( foundAlias.id in searchAliases )
            assertAliasDatapointInMap( self, foundAlias, datapoint, aliasMap )

        removeTemplate( self.dmd, 'template3' )

        
    def testGetDatapointByAliases_MatchDatapointName(self):        
        template = createTemplate( self.dmd, 'template4' )
        aliasMap = {
                    ('alias4_1', 'form4_1') : ('ds1', 'dp1'),
                    ('alias4_2', 'form4_2') : ('ds2', 'dp1'),
                    ('alias4_3', 'form4_3') : ('ds2', 'dp1')
                    }
        addAliases( template, aliasMap )
        
        gen = getDataPointsByAliases( self.dmd, ['dp3'] )
        
        aliasDps = list( gen )
        self.assert_(len( aliasDps ) == 2)
        for alias, dp in aliasDps:
            self.assert_( alias is None )
            self.assert_( dp.id == 'dp3' )
            self.assert_( dp.datasource().id in ['ds1','ds3'] )
              
        removeTemplate( self.dmd, 'template4' )
        
        #Empty alias list
    def testGetDatapointByAliases_EmptyAliases(self):
        template = createTemplate( self.dmd, 'template5' )
        addAliases( template, 
                         {
                          ('alias5_1', 'form5_1'):('ds1', 'dp1'),
                          ( 'alias5_2', 'form5_2' ) : ('ds2', 'dp1'),
                          ( 'alias5_3', 'form5_2' ) : ('ds2', 'dp1'  )
                          } )
        
        dps = getDataPointsByAliases( self.dmd, [] )
        self.assert_( len( list( dps ) ) == 0 )
        removeTemplate( self.dmd, 'template5')

        
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRRDDataPoint))
    return suite

if __name__=="__main__":
    framework()
