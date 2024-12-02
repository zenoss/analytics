##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class UpdateHBaseLogPath(Migrate.Step):
    """
    Update the log file path for HBase/HMaster and HBase/RegionServer services.
    Path changes from /var/log/hbase to /opt/hbase/logs.
    See ZEN-23724
    """

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        def updateService(serviceName, logName):
            retval = False
            services = filter(lambda s: s.name == serviceName, ctx.services)
            for service in services: # Should only be one
                for logConfig in service.logConfigs:
                    if (logConfig.logType == 'hbase' and
                            logConfig.path == '/var/log/hbase/' + logName):
                        logConfig.path = '/opt/hbase/logs/' + logName
                        retval = True
            return retval

        changed = False
        changed |= updateService('HMaster', 'hbase-master.log')
        changed |= updateService('RegionServer', 'hbase-regionserver.log')

        if changed:
            ctx.commit()

UpdateHBaseLogPath()
