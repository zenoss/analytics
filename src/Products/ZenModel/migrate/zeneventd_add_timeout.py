##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
__doc__ = """
Set process-event-timeout for zeneventd
"""

import logging

import Migrate
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.0.0")


class ZeneventdAddTimeout(Migrate.Step):
    '''
    add process-event-timeout to zeneventd.conf
    '''

    version = Migrate.Version(6, 2, 0)

    timeout_opt = [
        '# Timeout(in seconds) for processing each event.',
        '#  The timeout may be extended for a transforms using,',
        '#  signal.alarm(<timeout seconds>) in the transform.',
        '#  default: 0 (disabled)',
        '#process-event-timeout 0',
        '#',
    ]

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping")
            return

        commit = False
        services = filter(lambda s: s.name == 'zeneventd', ctx.services)
        log.info("Found %i services to update.", len(services))
        for service in services:
            configfiles = service.originalConfigs + service.configFiles
            for config_file in filter(
                lambda f: f.name == '/opt/zenoss/etc/zeneventd.conf',
                configfiles
            ):
                if self.timeout_opt[0] not in config_file.content:
                    log.info("adding on for %s and %s",
                             config_file.name, service.name)
                    config_file.content += '\n'.join(self.timeout_opt)
                    commit = True

        if commit:
            ctx.commit()


ZeneventdAddTimeout()
