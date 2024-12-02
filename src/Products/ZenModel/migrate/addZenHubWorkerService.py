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

workers_entry = re.compile(
    r"#\s*\n"
    r"#\s*Number of worker instances to handle.*\n"
    r"#\s*requests, default: .*\n"
    r"(?:#\s*workers.*\n?)?",
    re.MULTILINE
)

worker_priority_entry = re.compile(
    r"#\s*\n"
    r"#\s*Relative process priority for hub workers.*\n"
    r"#\s*\(%default\), default: .*\n"
    r"(?:#\s*hubworker-priority.*\n?)?",
    re.MULTILINE
)

call_limit_entry = re.compile(
    r"#\s*\n"
    r"#\s*Maximum number of remote calls a worker.*\n"
    r"#\s*can run before restarting, default: .*\n"
    r"(?:#\s*worker-call-limit.*\n?)?",
    re.MULTILINE
)

workers_set = re.compile(r"^\s*workers\s+(\d+).*\n?", re.MULTILINE)
priority_set = re.compile(r"^\s*hubworker-priority .*\n?", re.MULTILINE)
call_limit_set = re.compile(
    r"^\s*worker-call-limit\s+(\d+).*\n?", re.MULTILINE
)


class _OptionManager(object):

    def __init__(self, name):
        self.__name = name
        self.__matcher = re.compile(
            r"^\s*%s\s+(.+).*\n?" % (name,), re.MULTILINE
        )

    def extract(self, config):
        result = self.__matcher.search(config)
        return result.groups()[0] if result else None

    def update(self, config, value):
        option = "%s %s\n" % (self.__name, value)
        match = self.__matcher.search(config)
        if not match:
            # No match means not previously defined
            if config.endswith("\n"):
                config = config + "\n" + option
            else:
                config = config + option
        else:
            start, end = match.span()
            config = config[:start] + option + config[end:]
        return config


def deleteConfig(matcher, config):
    """Returns a tuple containing the edited config and any data captured
    by the matcher.
    """
    result = matcher.search(config)
    if not result:
        return config, ()
    start, end = result.span()
    captures = result.groups()
    return (config[:start] + config[end:]), captures


class AddZenHubWorkerService(Migrate.Step):
    """Modify the Control Center service definitions to support
    ZenHub Workers running in their own service.
    """

    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Make sure the zenhubworker service hasn't already been deployed
        count = sum((1 for s in ctx.services if s.name.startswith("zenhubworker")), 0)
        if count > 0:
            log.info("zenhubworker already deployed.  Skipping this step.")
            return

        # Locate ZenHub service definitions
        services = [s for s in ctx.services if s.name == "zenhub"]
        for service in services:

            instances = self._limitZenHubInstances(service)
            self._removeObsoleteHealthchecks(service)
            self._updateOriginalZenHubConfig(service)
            workers, callLimit = self._updateZenHubConfig(service, instances)

            # Retrieve the zenhub's parent service
            monitor = ctx.getServiceParent(service)

            # Worker instance count == sum of workers across zenhub instances
            workers = instances * (workers if workers else 2)
            self._deployZenHubWorkerService(
                ctx, parent=monitor, instances=workers, callLimit=callLimit
            )
            log.info(
                "['%s' hub] Deployed new zenhubworker service", monitor.name
            )
            if workers:
                log.info(
                    "['%s' hub] Configured zenhubworker service with %s "
                    "instances", monitor.name, workers
                )
            if callLimit:
                log.info(
                    "['%s' hub] Configured zenhubworker service to restart "
                    "after %s calls", monitor.name, callLimit
                )
            log.info("Migrated '%s' hub", monitor.name)

        ctx.commit()
        log.info(
            "Migrated %s hub%s",
            len(services), "s" if len(services) != 1 else ""
        )

    def _limitZenHubInstances(self, service):
        # Limit ZenHub service to a single instance.
        instances = service.instances
        service.instances = 1
        service.instanceLimits.minimum = 1
        service.instanceLimits.maximum = 1
        service.instanceLimits.default = 1
        return int(instances)

    def _removeObsoleteHealthchecks(self, service):
        # Remove unncessary health checks
        obsoleteHealthChecks = ("stable_workers", "workers_running")
        service.healthChecks = filter(
            lambda hc: hc.name not in obsoleteHealthChecks,
            service.healthChecks
        )

    def _updateZenHubConfig(self, service, instances):
        configFile = next((
            cf for cf in service.configFiles
            if cf.name == "/opt/zenoss/etc/zenhub.conf"
        ), None)
        if configFile is None:
            log.warn("No entry in 'ConfigFiles' for zenhub.conf")
            return None, None

        content = configFile.content

        content, _ = deleteConfig(workers_entry, content)
        content, _ = deleteConfig(worker_priority_entry, content)
        content, _ = deleteConfig(call_limit_entry, content)
        content, _ = deleteConfig(priority_set, content)

        if instances > 1:
            # Update the invalidationworkers option, only if the number
            # of zenhub instances was greater than 1.
            option = _OptionManager("invalidationworkers")
            iworkers = option.extract(content)
            if iworkers is None:
                iworkers = instances
            else:
                iworkers = int(iworkers) * instances
            content = option.update(content, iworkers)

        # Retrieve and delete workers override, if it existed
        content, groups = deleteConfig(workers_set, content)
        workers = int(groups[0]) if groups else None

        # Retrieve and delete worker-call-limit override, if it existed
        content, groups = deleteConfig(call_limit_set, content)
        callLimit = int(groups[0]) if groups else None

        # Update ConfigFiles
        configFile.content = content

        return (workers, callLimit)

    def _updateOriginalZenHubConfig(self, service):
        configFile = next((
            cf for cf in service.originalConfigs
            if cf.name == "/opt/zenoss/etc/zenhub.conf"
        ), None)
        if configFile is None:
            log.warn("No entry in 'OriginalConfigs' for zenhub.conf")
            return

        content = configFile.content
        content, _ = deleteConfig(workers_entry, content)
        content, _ = deleteConfig(worker_priority_entry, content)
        content, _ = deleteConfig(call_limit_entry, content)
        configFile.content = content

    def _deployZenHubWorkerService(self, ctx, parent, instances, callLimit):
        # Load zenhubworker config
        srcConfigPath = os.path.join(
            os.path.dirname(sys.modules[__name__].__file__),
            "data/zenhubworker.conf"
        )
        with open(srcConfigPath, 'r') as f:
            configContent = f.readlines()

        # Append the user defined call limit value, but only if a value
        # was previously specified in ZenHub's config.
        if callLimit:
            configContent.append("call-limit %s\n" % callLimit)

        configContent = ''.join(configContent)

        # Load zenhubworker service template
        templatePath = os.path.join(
            os.path.dirname(sys.modules[__name__].__file__),
            "data/zenhubworker.json"
        )
        with open(templatePath, 'r') as f:
            template = json.loads(f.read())

        configFileName = "/opt/zenoss/etc/zenhubworker.conf"
        zproxy = ctx.getTopService()
        template["ImageID"] = zproxy.imageID
        template["ConfigFiles"][configFileName]["Content"] = configContent
        if instances:
            template["Instances"]["Default"] = instances

        ctx.deployService(json.dumps(template), parent)


AddZenHubWorkerService()
