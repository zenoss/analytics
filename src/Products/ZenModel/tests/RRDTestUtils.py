##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


TEST_TEMPLATE = 'test_template'
DEFAULT_DSDP_MAP = {'ds1':['dp1', 'dp2', 'dp3'],
                    'ds2':['dp1', 'dp2'],
                    'ds3':['dp3']
                    }

def createTemplate( dmd, templateName=TEST_TEMPLATE,
                    dsDpMap=DEFAULT_DSDP_MAP ):
    dmd.Devices.manage_addRRDTemplate( templateName )
    template = dmd.Devices.rrdTemplates._getOb( templateName )
    dsOption = template.getDataSourceOptions()[0][1]
    for dsName, datapoints in dsDpMap.iteritems():
        datasource = template.manage_addRRDDataSource( dsName, dsOption )
        for dpName in datapoints:
            datasource.manage_addRRDDataPoint( dpName )
    return template

def removeTemplate(dmd, templateName=TEST_TEMPLATE):
    dmd.Devices.manage_deleteRRDTemplates( ( templateName, ) )

def addAliases( template, aliasMap ):
    for key, value in aliasMap.iteritems():
        aliasName, formula = key
        dsName, dpName = value
        addAlias( template, dsName, dpName, aliasName, formula )
    

def addAlias( template, dsName, dpName, aliasName, aliasFormula=None):
    dp = template.datasources._getOb( dsName ).datapoints._getOb( dpName )
    dp.addAlias( aliasName, aliasFormula )

def assertAliasDatapointInMap( test, alias, datapoint, aliasDpMap):        
    aliasPair = ( alias.id, alias.formula )
    test.assert_( aliasPair in aliasDpMap )
    dsDpPair = ( datapoint.datasource().id, datapoint.id )
    test.assert_( aliasDpMap[ aliasPair ] == dsDpPair )
