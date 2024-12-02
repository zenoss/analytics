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

insert_point = re.compile(
    r"#\s*\n"
    r"#\s*Maximum number of remote calls before.*\n"
    r"#\s*restarting worker, .*\n",
    re.MULTILINE
)

config_text = (
    "#\n"
    "# ZenHub response timeout interval (in seconds)\n"
    "# default: 30\n"
    "#hub-response-timeout 30\n"
)
_filename = "zenhubworker.conf"
_sections = (
    ("configFiles", "ConfigFiles"),
    ("originalConfigs", "OriginalConfigs"),
)

_Result = type("_Result", (object,), {"MISSING": 1, "SKIP": 2, "OK": 3})()


class AddHubResponseTimeoutConfig(Migrate.Step):
    """Add hub-response-timeout config to zenhubworker.conf files."""

    version = Migrate.Version(200, 5, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        workers = [
            svc for svc in ctx.services
            if svc.name.startswith("zenhubworker")
        ]
        for worker in workers:
            for attr, name in _sections:
                configs = getattr(worker, attr, [])
                result = self._updateConfig(configs)
                if result == _Result.MISSING:
                    log.warn(
                        "No entry in '%s' for %s in service '%s'",
                        name, _filename, worker.name,
                    )
                elif result == _Result.SKIP:
                    log.info(
                        "%s in '%s' for service '%s' already updated",
                        _filename, name, worker.name,
                    )
                elif result == _Result.OK:
                    log.info(
                        "Updated %s in '%s' for service '%s'",
                        _filename, name, worker.name,
                    )
        ctx.commit()

    def _updateConfig(self, configFiles):
        configFile = next((
            cf for cf in configFiles
            if cf.name == "/opt/zenoss/etc/zenhubworker.conf"
        ), None)
        if configFile is None:
            return _Result.MISSING

        content = configFile.content
        if config_text in content:
            return _Result.SKIP

        result = insert_point.search(content)

        # If the desired insert point not found, append to the end
        if not result:
            configFile.content = content + "\n" + config_text
            return _Result.OK

        start, _ = result.span()
        configFile.content = content[:start] + config_text + content[start:]
        return _Result.OK


AddHubResponseTimeoutConfig()
