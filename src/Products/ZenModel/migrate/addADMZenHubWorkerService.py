##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import logging
import os
import re
import sys

import Migrate

import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.1.11")

_configkeys = (
    "call-limit",
    "zodb-cachesize",
    "zodb-cache-max-object-size",
    "zodb-commit-lock-timeout",
)
_search_template = r"^\s*{key}\s+(\d+).*\n?"
_ConfigMatchers = {
    k: re.compile(_search_template.format(key=k), re.MULTILINE)
    for k in _configkeys
}
_command_matcher = re.compile(r"\".+\"")


def _append_queue(cmd, queue):
    match = _command_matcher.search(cmd)
    if match is None:
        log.error("zenhubworker command is non-standard")
        return cmd
    bgn, end = match.span()
    return cmd[:end - 1] + (" %s" % queue) + cmd[end - 1:]


class AddADMZenHubWorkerService(Migrate.Step):
    """Update the Zenoss CC app with a second zenhubworker service."""

    version = Migrate.Version(200, 4, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Make sure the zenhubworker service hasn't already been deployed
        count = sum((
            1 for s in ctx.services
            if s.name in ("zenhubworker (default)", "zenhubworker (adm)")
        ), 0)
        if count == 2:
            log.info(
                "ADM zenhubworker already deployed.  Skipping this step.",
            )
            return

        # Locate the 'hub' service organizers/folders.
        hubs = [
            ctx.getServiceParent(s)
            for s in ctx.services
            if s.name == "zenhub"
        ]
        hubs_migrated = 0
        for hub in hubs:
            try:
                default_worker = next(
                    s for s in ctx.getServiceChildren(hub)
                    if s.name == "zenhubworker"
                )
                newConfigs = self._getNonDefaultConfigs(default_worker)

                self._updateDefaultWorker(default_worker)
                log.info(
                    "Updated original zenhubworker as default  hub=%s",
                    hub.name,
                )

                self._deployADMZenHubWorkerService(
                    ctx, parent=hub, configs=newConfigs,
                )
                log.info(
                    "Deployed new ADM zenhubworker service  hub=%s",
                    hub.name,
                )
                log.info("Migrated '%s' hub", hub.name)
            except StopIteration:
                log.error(
                    "Hub '%s' is missing its 'zenhubworker' service. "
                    "Nothing to migrate so moving on to the next hub.",
                    hub.name,
                )
            else:
                hubs_migrated += 1

        ctx.commit()
        log.info(
            "Migrated %s of %s hub%s",
            hubs_migrated, len(hubs), "s" if len(hubs) != 1 else "",
        )

    def _getNonDefaultConfigs(self, worker):
        conf = next((
            c for c in worker.configFiles
            if c.name.endswith("/zenhubworker.conf")
        ), None)
        result = {}
        if conf is None:
            return result
        for key, matcher in _ConfigMatchers.items():
            match = matcher.search(conf.content)
            if match is not None:
                result[key] = match.groups()[0]
        return result

    def _updateDefaultWorker(self, worker):
        worker.startup = _append_queue(worker.startup, "default")
        worker.name += " (default)"

    def _deployADMZenHubWorkerService(self, ctx, parent, configs):
        # Load zenhubworker config
        srcConfigPath = os.path.join(
            os.path.dirname(sys.modules[__name__].__file__),
            "data/zenhubworker.conf",
        )
        with open(srcConfigPath, 'r') as f:
            configContent = f.readlines()

        # Append the user defined call limit value, but only if a value
        # was previously specified in the default worker's config.
        for name in (n for n in _configkeys if n in configs):
            value = configs[name]
            configContent.append("%s %s\n" % (name, value))

        configContent = ''.join(configContent)

        # Load zenhubworker service template
        templatePath = os.path.join(
            os.path.dirname(sys.modules[__name__].__file__),
            "data/zenhubworker.json",
        )
        with open(templatePath, 'r') as f:
            template = json.loads(f.read())

        # Load the config file into the template
        configFileName = "/opt/zenoss/etc/zenhubworker.conf"
        zproxy = ctx.getTopService()
        template["ImageID"] = zproxy.imageID
        template["ConfigFiles"][configFileName]["Content"] = configContent

        # Set the default instance count
        template["Instances"]["Default"] = 1

        # Update fields to show this worker uses the 'adm' zenhub queue.
        template["Command"] = _append_queue(template["Command"], "adm")
        template["Name"] += " (adm)"

        ctx.deployService(json.dumps(template), parent)


AddADMZenHubWorkerService()
