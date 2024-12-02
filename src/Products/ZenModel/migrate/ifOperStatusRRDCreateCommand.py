##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
import logging
log = logging.getLogger( 'zen.migrate' )

class ifOperStatusRRDCreateCommand(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        try:
            template = dmd.Devices.rrdTemplates._getOb('ethernetCsmacd')
            datapoint = template.datasources.ifOperStatus.datapoints.ifOperStatus
            datapoint.createCmd = "\n".join((
                'RRA:LAST:0.5:1:600',
                'RRA:AVERAGE:0.5:1:600',   # every 5 mins for 2 days
                'RRA:AVERAGE:0.5:6:600',   # every 30 mins for 12 days
                'RRA:AVERAGE:0.5:24:600',  # every 2 hours for 50 days
                'RRA:AVERAGE:0.5:288:600', # every day for 600 days
                'RRA:MAX:0.5:6:600',
                'RRA:MAX:0.5:24:600',
                'RRA:MAX:0.5:288:600',
                ))
            log.warn("""
Changing the definition for ifOperStatus. Please
remove all rrd files with this name: ifOperStatus_ifOperStatus.rrd. \n
You can remove all the rrd files with the following command as the zenoss user:
find $ZENHOME -name "ifOperStatus_ifOperStatus.rrd" -delete""")
        except AttributeError:
            # they don't have the template so ignore it
            pass

ifOperStatusRRDCreateCommand()
