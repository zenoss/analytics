##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
add --disable-ping-perspective option to daemons configuration files
"""

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class AddDisablePingPerspectiveOption(Migrate.Step):

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        servicenames = ["zentrap",
                        "zencommand",
                        "zenping",
                        "zenprocess",
                        "zenperfsnmp",
                        "zensyslog",
                        "zenpop3",
                        "zenstatus",
                        "zenmail"]
        update_string = """# Disable ping perspective, default: True
#disable-ping-perspective True
#

"""

        log.info("Updating daemons configuration files with --disable-ping-perspective option.")

        services = filter(lambda s: s.name in servicenames, ctx.services)
        log.info("Found %i services to update." % len(services))
        for serv in services:
            configfiles = serv.originalConfigs + serv.configFiles
            current_config = "/opt/zenoss/etc/%s.conf" % serv.name
            for configfile in filter(lambda f: f.name == current_config, configfiles):
                if '#disable-ping-perspective' in configfile.content:
                    found_at = configfile.content.find('#disable-ping-perspective')
                    log.info("disable-ping-perspective option found at character %i; not adding another." % found_at)
                    continue
                log.info("Appending disable-ping-perspective option to %s for service '%s'."
                         % (current_config, serv.name))
                configfile.content += update_string
                commit = True

        if commit:
            ctx.commit()


AddDisablePingPerspectiveOption()
