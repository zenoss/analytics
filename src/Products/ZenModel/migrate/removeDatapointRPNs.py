##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Remove RPN formulas from datapoint objects (they now reside in the GraphDataPoint
objects)

'''

import Migrate
from Products.ZenModel.RRDTemplate import YieldAllRRDTemplates
import logging
log = logging.getLogger("zen.migrate")

class RemoveDataPointRPNs(Migrate.Step):
    version = Migrate.Version(2, 2, 4)

    def cutover(self, dmd):
        ''' Find all the non-empty RPNs and empty them
        '''
        templates=YieldAllRRDTemplates( dmd.Devices )
        for template in templates:
            for datasource in template.datasources.objectValues():
                for datapoint in datasource.datapoints.objectValues():
                    if len( datapoint.rpn ) > 0:
                        log.debug( "Resetting rpn for %s.%s.%s from %s" % \
                                (template.id, datasource.id, \
                                 datapoint.id,datapoint.rpn) )
                        datapoint.rpn=''

RemoveDataPointRPNs()
