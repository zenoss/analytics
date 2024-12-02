##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016-2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from itertools import chain
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class UpdateZodbConfigFiles(Migrate.Step):
    """
    Update zodb config files to be dinamically generated from global.conf.
    - For Zope service, we need to add 2 new config files:
            -> "/opt/zenoss/etc/zodb_db_main.conf"
            -> "/opt/zenoss/etc/zodb_db_session.conf"
    - For Zauth, we need to update the above files to be built from global.conf
    """

    version = Migrate.Version(108, 0, 0)

    ZODB_MAIN_CFG_CONTENT = """
    <mysql>
        host    {{getContext . "global.conf.zodb-host"}}
        port    {{getContext . "global.conf.zodb-port"}}
        user    {{getContext . "global.conf.zodb-user"}}
        passwd  {{getContext . "global.conf.zodb-password"}}
        db      {{getContext . "global.conf.zodb-db"}}
    </mysql>
    """

    ZODB_SESSION_CFG_CONTENT = """
    <mysql>
        host    {{getContext . "global.conf.zodb-host"}}
        port    {{getContext . "global.conf.zodb-port"}}
        user    {{getContext . "global.conf.zodb-user"}}
        passwd  {{getContext . "global.conf.zodb-password"}}
        db      zodb_session
    </mysql>
    """

    ZODB_MAIN_CFG_FILE = sm.configfile.ConfigFile(name="/opt/zenoss/etc/zodb_db_main.conf",
                                                  filename="/opt/zenoss/etc/zodb_db_main.conf",
                                                  owner="zenoss:zenoss",
                                                  permissions="0664",
                                                  content = ZODB_MAIN_CFG_CONTENT)

    ZODB_SESSION_CFG_FILE = sm.configfile.ConfigFile(name="/opt/zenoss/etc/zodb_db_session.conf",
                                                     filename="/opt/zenoss/etc/zodb_db_session.conf",
                                                     owner="zenoss:zenoss",
                                                     permissions="0664",
                                                     content = ZODB_SESSION_CFG_CONTENT)

    def _migrate_zope_service(self, zope):
        changed = False
        def append_if_not_found(config):
            filenames = [x.name for x in config]
            if "/opt/zenoss/etc/zodb_db_main.conf" not in filenames:
                config.append(self.ZODB_MAIN_CFG_FILE)
                changed = True
            if "/opt/zenoss/etc/zodb_db_session.conf" not in filenames:
                config.append(self.ZODB_SESSION_CFG_FILE)
                changed = True
            config.sort(key=lambda x: x.name)

        for x in (zope.originalConfigs, zope.configFiles):
            append_if_not_found(x)
        return changed

    def _migrate_zauth_service(self, zauth):
        changed = False
        for cfg in chain(zauth.originalConfigs, zauth.configFiles):
            if cfg.name == "/opt/zenoss/etc/zodb_db_main.conf" and "global.conf" not in cfg.content:
                cfg.content = self.ZODB_MAIN_CFG_CONTENT
                changed = True
            elif cfg.name == "/opt/zenoss/etc/zodb_db_session.conf" and "global.conf" not in cfg.content:
                cfg.content = self.ZODB_SESSION_CFG_CONTENT
                changed = True
        return changed

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zope = filter(lambda x: x.name=="Zope", ctx.services)[0]
        zauth = filter(lambda x: x.name=="Zauth", ctx.services)

        zope_changed = self._migrate_zope_service(zope)
        zauth_changed = self._migrate_zauth_service(zauth[0]) if zauth else False

        if zope_changed or zauth_changed:
            log.info("Zodb config files updated to be dynamically generated.")
            ctx.commit()

UpdateZodbConfigFiles()
