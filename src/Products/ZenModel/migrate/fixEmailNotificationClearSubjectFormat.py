##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """addTriggersAndNotifications suffered from a bug in 4.0.0 through
4.1.1 (ZEN-123). This migrate script fixes the notifications clear subject
format on systems that were upgraded from 3.x to 4.[01].x and now to 4.2"""

import logging
from Products.ZenUtils.Utils import unused
from Products.ZenModel.migrate import Migrate


log = logging.getLogger('zen.migrate')

BAD_STRING = "orEventSummary"

class fixEmailNotificationClearSubjectFormat(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        log.info("Setting default values for E-mail notifications.")
        for notif in dmd.NotificationSubscriptions.objectValues():
            if notif.action == "email":
                for content_key in ("clear_subject_format", "clear_body_format"):
                    if BAD_STRING in notif.content.get(content_key, ""):
                        notif._p_changed = True
                        notif.content[content_key] = notif.content[content_key].replace(BAD_STRING, "summary")

fixEmailNotificationClearSubjectFormat()
