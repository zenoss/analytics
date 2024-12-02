##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""Add /App/Zenoss event class"""

import Migrate

class EventsAppZenoss(Migrate.Step):
    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        dmd.Events.createOrganizer("/App/Zenoss")

EventsAppZenoss()
