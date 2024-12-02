##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


import logging
log = logging.getLogger("zen.migrate")


class DeleteNotificationSchedulesReport(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        USER_REPORTS_CATEGORY = 'User Reports'
        NOTIFICATION_SCHEDULES_REPORT = 'Notification Schedules'

        userReports = getattr(dmd.Reports, USER_REPORTS_CATEGORY, {})
        if NOTIFICATION_SCHEDULES_REPORT in userReports:
            del userReports[NOTIFICATION_SCHEDULES_REPORT]


DeleteNotificationSchedulesReport()
