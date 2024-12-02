##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """Set the default values for E-mail notifications"""

import logging
from Products.ZenUtils.Utils import unused
from Products.ZenModel.migrate import Migrate


log = logging.getLogger('zen.migrate')

class setDefaultsOnEmailNotifications(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        log.info("Setting default values for E-mail notifications.")
        for notif in dmd.NotificationSubscriptions.objectValues():
            if notif.action == "email" and "host" not in notif.content:
                notif._p_changed = True
                notif.content["host"] = dmd.smtpHost
                notif.content["port"] = dmd.smtpPort
                notif.content["user"] = dmd.smtpUser
                notif.content["password"] = dmd.smtpPass
                notif.content["useTls"] = dmd.smtpUseTLS
                notif.content["email_from"] = dmd.getEmailFrom()

setDefaultsOnEmailNotifications()
