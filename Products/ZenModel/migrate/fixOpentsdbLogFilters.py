
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import logging
log = logging.getLogger("zen.migrate")

from Products.ZenUtils.path import zenPath

import Migrate
import servicemigration as sm
from servicemigration import InstanceLimits

sm.require("1.1.10")


class FixOpentsdbLogFilters(Migrate.Step):
    """Correct the LogFilters for Opentsdb (ZEN-28084)"""

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        top = ctx.getTopService()
        log.info("Found top level service: '{0}'".format(top.name))
        if top.name.find("Zenoss") != 0 and top.name.find("UCS-PM") != 0:
            log.info("Top level service name isn't Zenoss or UCS-PM; skipping.")
            return

        services = filter(lambda s: "opentsdb" in ctx.getServicePath(s), ctx.services)
        log.info("Found %i services with 'opentsdb' in their service path." % len(services))

        changed = False
        filterName = "hbasedaemon"
        for service in services:
            servicePath = ctx.getServicePath(service)
            # First, fix the path and the log filter name
            for logConfig in service.logConfigs:
                if logConfig.path == "/opt/zenoss/log/opentsdb.log":
                    log.info("Updating logfilter for %s in %s", logConfig.path, servicePath)
                    logConfig.path = "/var/log/opentsdb/opentsdb.log"
                    logConfig.filters = [filterName]
                    changed = True
                else:
                    log.info("No updates necesary for the logfilter for %s", servicePath)

            # Second, update the log file config to generate messages in the same format as hbase
            configFiles = service.originalConfigs + service.configFiles
            hbaseLogPattern = "%date{ISO8601} %-5level [%thread] %logger{0}: %msg%n"
            for configFile in filter(lambda f: f.name == '/opt/opentsdb/src/logback.xml', configFiles):
                if "%d{HH:mm:ss.SSS} %-5level [%logger{0}.%M] - %msg%n" in configFile.content:
                    log.info("Updating /opt/opentsdb/src/logback.xml for %s", servicePath)
                    configFile.content = configFile.content.replace("%d{ISO8601} %-5level [%thread] %logger{0}: %msg%n", hbaseLogPattern)
                    configFile.content = configFile.content.replace("%d{HH:mm:ss.SSS} %-5level [%logger{0}.%M] - %msg%n", hbaseLogPattern)
                    configFile.content = configFile.content.replace("%date{ISO8601} [%logger.%M] %msg%n", hbaseLogPattern)
                    changed = True

        filename = 'Products/ZenModel/migrate/data/hbasedaemon-6.0.0.conf'
        with open(zenPath(filename)) as filterFile:
            try:
                filterDef = filterFile.read()
            except Exception as e:
                log.error("Error reading {0} logfilter file: {1}".format(filename, e))
                return
            log.info("Updating log filter named {0}".format(filterName))
            changed = True
            ctx.addLogFilter(filterName, filterDef)

        if changed:
            # Commit our changes.
            ctx.commit()


FixOpentsdbLogFilters()
