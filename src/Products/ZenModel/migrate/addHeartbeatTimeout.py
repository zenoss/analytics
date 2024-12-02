##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
add --heartbeattimeout option to daemons configuration files
"""

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.1.9")


class AddHeartbeatTimeout(Migrate.Step):

    version = Migrate.Version(115,0,0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        services = ["zenactiond",
                    "zencommand",
                    "zeneventd",
                    "zenhub",
                    "zenjmx",
                    "zenmailtx",
                    "zenmodeler",
                    "zenperfsnmp",
                    "zenping",
                    "zenprocess",
                    "zenpropertymonitor",
                    "zenpython",
                    "zenstatus",
                    "zensyslog",
                    "zentrap",
                    "zenucsevents",
                    "zenvsphere",
                    "zenwebtx"]


        update_string = """# Heartbeat timeout, default: 900 sec.
#heartbeattimeout 900
#
"""

        log.info("Updating daemons configuration files with --heartbeattimeout option.")

        commit = False
        services = filter(lambda s: s.name in services, ctx.services)
        log.info("Found %i services to update." % len(services))
        for serv in services:
            configfiles = serv.originalConfigs + serv.configFiles
            current_config = "/opt/zenoss/etc/%s.conf" % serv.name
            for configfile in filter(lambda f: f.name == current_config, configfiles):
                if '#heartbeattimeout' in configfile.content:
                    found_at = configfile.content.find('#heartbeattimeout')
                    log.debug("#heartbeattimeout option found at character %i." % found_at)
                    continue
                log.info("Appending heartbeattimeout option to %s for service '%s'."
                         % (current_config, serv.name))
                configfile.content += update_string
                commit = True

        if commit:
            ctx.commit()


AddHeartbeatTimeout()
