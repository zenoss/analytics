##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate
from Products.ZenEvents.EventClass import manage_addEventClass


class AddMissedRunsEventClass(Migrate.Step):
    version = Migrate.Version(109, 0, 0)

    def cutover(self, dmd):
        if 'MissedRuns' not in [i.id for i in dmd.Events.Perf.children()]:
            manage_addEventClass(dmd.Events.Perf, 'MissedRuns')


AddMissedRunsEventClass()

