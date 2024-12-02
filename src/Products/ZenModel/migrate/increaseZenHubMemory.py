##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = '''
Increase zenhub RAMComminment
'''

import logging
import Migrate
import re
import servicemigration as sm
log = logging.getLogger("zen.migrate")


class IncreaseZenHubMemory(Migrate.Step):
    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zenhub_services = filter(lambda cf: cf.name == 'zenhub', ctx.services)
        commited = False

        for service in zenhub_services:
            # override ramCommitment only if it has the prior default value.
            # We don't want to change any settings the customer may have set.
            if service.ramCommitment == u'1G':
                log.info("Changing RamCommitment to 2G")
                service.ramCommitment = u'2G'
                commited = True

        if commited:
            log.info("Commiting changes")
            ctx.commit()


IncreaseZenHubMemory()
