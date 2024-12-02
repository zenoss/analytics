##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os.path

import servicemigration as sm

import Migrate

log = logging.getLogger("zen.migrate")
sm.require("1.0.0")


class addOpenTSDBLogbackConfig(Migrate.Step):
    """Set Editable Logback configuration file for OpenTSDB. See ZEN-27916"""

    version = Migrate.Version(116, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        commit = False
        services = filter(
            lambda s: "opentsdb" in ctx.getServicePath(s), ctx.services
        )
        log.info(
            "Found %i services with 'opentsdb' in their service path."
            % len(services)
        )
        services = filter(
            lambda s: "/opt/zenoss/etc/opentsdb/opentsdb.conf"
            in [i.name for i in s.originalConfigs],
            services,
        )
        log.info(
            "Of those, %i services use /opt/zenoss/etc/opentsdb/opentsdb.conf."
            % len(services)
        )
        with open(
            os.path.join(
                os.path.dirname(__file__), "data/opentsdb-logback.xml"
            )
        ) as fcontent:
            try:
                content = fcontent.read()
            except Exception as e:
                log.error(
                    "Error reading logback configuration file: {}".format(e)
                )
                return

        def equal(this, that):
            return (
                this.name == that.name
                and this.filename == that.filename
                and this.owner == that.owner
                and this.permissions == that.permissions
                and this.content == that.content
            )

        for service in services:
            newConfig = sm.ConfigFile(
                name="/opt/opentsdb/src/logback.xml",
                filename="/opt/opentsdb/src/logback.xml",
                owner="root:root",
                permissions="0664",
                content=content,
            )

            # If there's a config with the same name but is different from
            # the new config, overwrite it.
            if all(
                not equal(config, newConfig)
                for config in service.originalConfigs
            ):
                service.originalConfigs.append(newConfig)
                log.info(
                    "Adding a configuration to OriginalConfigs of %s",
                    service.name,
                )
                commit = True

            # Add this config only if there's no config with the same name.
            # If there is such config, honor it.
            if all(
                not equal(config, newConfig) for config in service.configFiles
            ):
                service.configFiles.append(newConfig)
                log.info(
                    "Adding a configuration to ConfigFiles of %s", service.name
                )
                commit = True

        log.info("Configuration added for OpenTSDB services")
        if commit:
            ctx.commit()


addOpenTSDBLogbackConfig()
