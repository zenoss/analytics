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


class UpdateOpenTsdbCreateTables(Migrate.Step):
    """
    Update the startup command for opentsdb/writer to set the CREATE_TABLES
    environment variable just for instance 0 of the service.
    See ZEN-22929
    """

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Find the services to edit.  
        # For "lite" services, there is a single opentsdb service; edit that
        # service.  For "full" services, the opentsdb service is an organizer
        # with reader and writer subservices; edit the writer service.
        opentsdbs = [i for i in ctx.services if i.name == 'opentsdb' ]
        writers = [i for i in ctx.services if i.name == 'writer' and 
                ctx.getServiceParent(i) in opentsdbs]
        services = writers if writers else opentsdbs

        changed = False

        # Wrap the original command in a shell which sets the CREATE_TABLES 
        # variable for instance 0 of the service.
        go_template = "{{ if eq .InstanceID 0 }} export CREATE_TABLES=1;{{ end }} %s"
        command_template = '/bin/sh -c "%s"' % go_template
        for service in services:
            if 'CREATE_TABLES' not in service.startup:
                before = service.startup
                service.startup = command_template % service.startup
                after = service.startup
                log.info('Modified startup command for %s: "%s" -> "%s"',
                        ctx.getServicePath(service), before, after)
                changed = True
            else:
                log.info('Startup command already migrated for %s: "%s"',
                        ctx.getServicePath(service), service.startup)

        if changed:
            ctx.commit()

UpdateOpenTsdbCreateTables()
