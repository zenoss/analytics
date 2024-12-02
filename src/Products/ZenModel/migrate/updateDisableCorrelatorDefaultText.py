##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
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

disableCorrelator_matcher = re.compile(
    r"#\s*\n"
    r"#\s*Disable the correlator.*\n"
    r"(?:#\s*disable-correlator.*\n?)?",
    re.MULTILINE
)

disableCorrelator_update = (
    "#\n"
    "# Disable the ping down event correlator., default: False\n"
    "#disable-correlator False\n"
)


def replaceConfig(matcher, replacement, content):
    """Returns a tuple containing the edited config and any data captured
    by the matcher.
    """
    result = matcher.search(content)
    if not result:
        return (False, content)
    start, end = result.span()
    return (True, content[:start] + replacement + content[end:])


class UpdateDisableCorrelatorDefaultText(Migrate.Step):

    version = Migrate.Version(200, 4, 1)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        services = [s for s in ctx.services if s.name == "zenping"]
        if not services:
            log.warning("No zenping services found, skipping")
            return

        for service in services:
            configFile = next((
                cf for cf in service.configFiles
                if cf.name == "/opt/zenoss/etc/zenping.conf"
            ), None)
            if configFile is None:
                log.warn("No entry in 'ConfigFiles' for zenping.conf")
            else:
                updated, result = replaceConfig(
                    disableCorrelator_matcher,
                    disableCorrelator_update,
                    configFile.content,
                )
                if updated:
                    log.info(
                        "Updated disable-correlator text in "
                        "'ConfigFiles' for zenping.conf"
                    )
                    configFile.content = result
                else:
                    log.info(
                        "Did not update disable-correlator text in "
                        "'ConfigFiles' for zenping.conf"
                    )

            configFile = next((
                cf for cf in service.originalConfigs
                if cf.name == "/opt/zenoss/etc/zenping.conf"
            ), None)
            if configFile is None:
                log.warn("No entry in 'OriginalConfigs' for zenping.conf")
            else:
                updated, result = replaceConfig(
                    disableCorrelator_matcher,
                    disableCorrelator_update,
                    configFile.content,
                )
                if updated:
                    log.info(
                        "Updated disable-correlator text in "
                        "'OriginalConfigs' for zenping.conf"
                    )
                    configFile.content = result
                else:
                    log.info(
                        "Did not update disable-correlator text in "
                        "'OriginalConfigs' for zenping.conf"
                    )

        ctx.commit()


UpdateDisableCorrelatorDefaultText()
