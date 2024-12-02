##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import dateutil.tz as tz

__doc__ = '''
This migration script add and sets the timezone field for existing maintenance windows.
It takes the timezone of container
'''

import Migrate

from Products.ZenUtils import Time

log = logging.getLogger("zen.migrate")


class AddTzToMaintWindows(Migrate.Step):
    version = Migrate.Version(200, 5, 1)

    def cutover(self, dmd):
        container_tz = Time.getLocalTimezone()
        tzInstance = tz.gettz(container_tz)
        for brain in dmd.maintenanceWindowSearch():
            try:
                m = brain.getObject()
            except Exception:
                continue
            m.timezone = container_tz
            m.tzInstance = tzInstance

AddTzToMaintWindows()
