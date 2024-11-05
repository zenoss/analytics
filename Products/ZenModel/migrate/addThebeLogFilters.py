##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import os
import servicemigration as sm
from Products.ZenUtils.path import zenPath

log = logging.getLogger("zen.migrate")
sm.require("1.1.10")

class AddThebeLogFilters(Migrate.Step):
    """
    Add LogFilters for issues addressed by ZEN-27982
    """
    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        service = ctx.getTopService()
        log.info("Found top level service: '{0}'".format(service.name))
        if service.name.find("Zenoss") != 0 and service.name.find("UCS-PM") != 0:
            log.info("Top level service name isn't Zenoss or UCS-PM; skipping.")
            return

        filterNames = ["pythondaemon", "supervisord", "z2_access_logs", "zappdaemon", "zeneventserver", "zope"]
        for filterName in filterNames:
            filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
            with open(zenPath(filename)) as filterFile:
                try:
                    filterDef = filterFile.read()
                except Exception as e:
                    log.error("Error reading {0} logfilter file: {1}".format(filename, e))
                    return
                log.info("Updating log filter named {0}".format(filterName))
                ctx.addLogFilter(filterName, filterDef)

        # Note that the logstash.conf will not be properly updated until a later
        # step in the overall upgrade process sets the Version of the toplevel
        # service to 6.0.0
        ctx.commit()

AddThebeLogFilters()
