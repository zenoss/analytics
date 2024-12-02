##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re

import Migrate

import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.1.11")

prioritize_entry = re.compile(
    r"#\s*\n"
    r"#\s*Run higher priority jobs before lower.*\n"
    r"#\s*priority ones, default: False.*\n"
    r"#\s*prioritize False.*\n",
    re.MULTILINE
)

anyworker_entry = re.compile(
    r"#\s*\n"
    r"#\s*Allow any priority job to run on any.*\n"
    r"#\s*worker, default: False.*\n"
    r"#\s*anyworker False.*\n",
    re.MULTILINE
)


def deleteConfig(matcher, config):
    """Returns a tuple containing the edited config and any data captured
    by the matcher.
    """
    result = matcher.search(config)
    if not result:
        return config
    start, end = result.span()
    return config[:start] + config[end:]


class RemoveOldPriorityZenHubOptions(Migrate.Step):
    """Modify the zenhub service' config file to remove the prioritize
    and anyworker configuration options.
    """

    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        services = [s for s in ctx.services if s.name == "zenhub"]
        if not services:
            log.info("No zenhub services found, skipping.")
            return

        for service in services:
            if not self._updateConfigs(service.originalConfigs):
                log.warn("No entry in 'OriginalConfigs' for zenhub.conf")
            if not self._updateConfigs(service.configFiles):
                log.warn("No entry in 'ConfigFiles' for zenhub.conf")

            # Retrieve the zenhub's parent service
            monitor = ctx.getServiceParent(service)
            log.info("Migrated '%s' hub", monitor.name)

        ctx.commit()
        log.info(
            "Migrated %s hub%s",
            len(services), "s" if len(services) != 1 else ""
        )

    def _updateConfigs(self, configFiles):
        configFile = next((
            cf for cf in configFiles
            if cf.name == "/opt/zenoss/etc/zenhub.conf"
        ), None)
        if configFile is None:
            return False

        content = configFile.content
        content = deleteConfig(anyworker_entry, content)
        content = deleteConfig(prioritize_entry, content)
        configFile.content = content

        return True


RemoveOldPriorityZenHubOptions()
