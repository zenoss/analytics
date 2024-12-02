##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

def attachCpuAliases( dmd, aliasMap ):
    for template in [ t.getObject() for t in dmd.searchRRDTemplates()]:
        for ds in template.datasources():
            for dp in ds.datapoints():
                if aliasMap.has_key( dp.id ):
                    if not dp.hasAlias( aliasMap[dp.id][0] ):
                        dp.addAlias( *aliasMap[dp.id] )

def handleCpuIdleOnLinuxes( dmd ):
    """
    If there is no ssCpuRawIdle, we want to use ssCpuIdle (as problematic as that
    might be).  ssCpuIdle has problems because there is no standard for the
    time period over which the value is averaged.  ssCpuRawIdle has problems
    because older versions of Net-SNMP started returning zeroes when the value 
    passed a counter max
    """
    for template in [ t.getObject() for t in dmd.searchRRDTemplates()]:
        templateDpMap={}
        for ds in template.datasources():
            dpMap=dict((dp.id,dp) for dp in ds.datapoints())
            templateDpMap.update( dpMap )
        if 'ssCpuIdle' in templateDpMap.keys() and \
            'ssCpuRawIdle' not in templateDpMap.keys():
            dp=templateDpMap['ssCpuIdle']
            if not dp.hasAlias('cpu__pct'):
                templateDpMap['ssCpuIdle'].addAlias( 'cpu__pct', '100,EXC,-' )


def buildDataPointAliasRelations( dmd ):
    for brain in dmd.searchRRDTemplates():
        template = brain.getObject()
        for ds in template.datasources.objectValuesGen():
            for dp in ds.datapoints.objectValuesGen():
                dp.buildRelations()

class addCpuDataPointAliases(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        buildDataPointAliasRelations( dmd )
        attachCpuAliases( dmd, 
          {'cpu5min' : ('cpu__pct',),
           'ssCpuRawIdle' : ('cpu__pct', "__EVAL:str(len(here.hw.cpus())) " + \
                                         "+ ',/,100,EXC,-,0,MAX'"),
           'laLoadInt5' : ('loadAverage5min', '100,/'),
           'cpuPercentProcessorTime' : ('cpu__pct',) }
           )
        handleCpuIdleOnLinuxes( dmd )

            
addCpuDataPointAliases()
