##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import os
import servicemigration as sm
from Products.ZenUtils.path import zenPath

log = logging.getLogger("zen.migrate")
sm.require("1.1.5")

class updateOpenTSDBOriginalConfig(Migrate.Step):
    """
    Overwrite Original OpenTSDB config to match the lastest.
    This is needed for the systems that were originaly upgraded from 5.0.5 and lower. 
    """
    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        tsdbs = filter(
            lambda s: "opentsdb" in
                      ctx.getServicePath(s), ctx.services
        )
        log.info(
            "Found {} services with 'opentsdb' in their service path."
            .format(len(tsdbs))
        )

        tsdbs = filter(
                       lambda s: "/opt/zenoss/etc/opentsdb/opentsdb.conf"
                                 in [i.name for i in s.originalConfigs], tsdbs
        )
        log.info(
            "Of those, {} services use /opt/zenoss/etc/opentsdb/opentsdb.conf."
            .format(len(tsdbs))
        )

        commit = False

        filename = 'Products/ZenModel/migrate/data/opentsdb.conf'
        with open(zenPath(filename)) as configFile:
            try:
                configCnt = configFile.read()
            except Exception as e:
                log.error("Error reading {0} file: {1}".format(filename, e))
                return

        for tsdb in tsdbs:
            original_configs = filter(
                lambda f: f.name == "/opt/zenoss/etc/opentsdb/opentsdb.conf",
                          tsdb.originalConfigs
            )
            log.info(
                "Found {} original config files named '/opt/zenoss/etc/opentsdb/opentsdb.conf'."
                .format(len(original_configs))
            )
            for config in original_configs:
                if config.content != configCnt:
                    config.content = configCnt
                    log.info("Updated original config")
                    commit = True
        if commit:
            ctx.commit()

updateOpenTSDBOriginalConfig()
