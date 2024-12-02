##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import ConfigParser
import logging
import io
import Migrate
import servicemigration as sm

from collections import OrderedDict
from itertools import chain

log = logging.getLogger("zen.migrate")
sm.require("1.1.14")


class EditServicesStartUp(Migrate.Step):
    "Edit service command"

    version = Migrate.Version(200, 5, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        updated = []

        command_map = _get_collection_command_map()
        command_map.update(_get_monitor_command_map())
        command_map.update(_misc_command_map)
        updated.append(_update_service_startup(
            _select_services(command_map.keys(), ctx.services), command_map
        ))

        supervisord_svcs = {
            "zminion": "zminion",
            "CentralQuery": "central-query",
            "MetricConsumer": "metric-consumer-app",
            "MetricShipper": "metricshipper",
        }
        updated.append(_update_supervisord_services(
            _select_services(supervisord_svcs.keys(), ctx.services),
            supervisord_svcs,
            "/opt/zenoss/bin/supervisord "
            "-n "
            "-c /opt/zenoss/etc/{}/supervisord.conf"
        ))

        zope_svcs = {
            "Zauth": "zauth",
            "Zope": "zope",
            "zenapi": "zenapi",
            "zenreports": "zenreports",
        }
        updated.append(_update_zope_services(
            _select_services(zope_svcs.keys(), ctx.services),
            zope_svcs,
            "/opt/zenoss/bin/runzope"
        ))

        zauth = next((s for s in ctx.services if s.name == "Zauth"), None)
        if zauth:
            updated.append(_update_zauth_conf(zauth))
        else:
            log.info("Unable to locate 'Zauth' service.")

        if any(updated):
            ctx.commit()


def _get_collection_command_map():
    command_template = (
        "/opt/zenoss/bin/%s "
        "run "
        "-c "
        "--logfileonly "
        "--workers {{.Instances}} "
        "--workerid $CONTROLPLANE_INSTANCE_ID "
        "--monitor {{(parent .).Name}}"
    )
    names = (
        "zencommand", "zenmodeler", "zenperfsnmp",
        "zenping", "zenprocess", "zenstatus",
    )
    return {n: (command_template % n) for n in names}


def _get_monitor_command_map():
    command_template = (
        "/opt/zenoss/bin/%s "
        "run "
        "-c "
        "--logfileonly "
        "--monitor {{(parent .).Name}}"
    )
    names = ("zensyslog", "zentrap", "zenhub")
    return {n: (command_template % n) for n in names}


_misc_command_map = {
    "zenhubworker (adm)": (
        "/opt/zenoss/bin/zenhubworker "
        "run "
        "-c "
        "--logfileonly "
        "--monitor {{(parent .).Name}} "
        "--workerid $CONTROLPLANE_INSTANCE_ID "
        "adm"
    ),
    "zenhubworker (default)": (
        "/opt/zenoss/bin/zenhubworker "
        "run "
        "-c "
        "--logfileonly "
        "--monitor {{(parent .).Name}} "
        "--workerid $CONTROLPLANE_INSTANCE_ID "
        "default"
    ),
    "zenhubiworker": (
        "/opt/zenoss/bin/zenhubiworker "
        "run "
        "-c "
        "--duallog "
        "--hub {{(parent .).Name}} "
        "--workerid $CONTROLPLANE_INSTANCE_ID"
    ),
    "zeneventd": (
        "/usr/bin/nice "
        "-n 10 "
        "/opt/zenoss/bin/zeneventd run -c --logfileonly "
    ),
    "zenactiond": (
        "/opt/zenoss/bin/zenactiond "
        "run "
        "-c "
        "--logfileonly "
        "--workerid $CONTROLPLANE_INSTANCE_ID"
    ),
    "zenjobs": "/opt/zenoss/bin/zenjobs run --logfileonly",
}


def _select_services(names, services):
    return (s for s in services if s.name in names)


def _update_service_startup(services, command_map):
    def update(service, command):
        if service.runAs != "zenoss":
            service.startup = command_map[service.name]
            service.runAs = "zenoss"
            log.info("Service %s updated", service.name)
            return True
        log.info("Service %s already updated", service.name)
        return False

    updated = [
        update(service, command_map[service.name]) for service in services
    ]
    return any(updated)


def _update_supervisord_services(services, svcmap, command):
    def update(service, command):
        if service.runAs != "zenoss":
            service.startup = command
            service.runAs = "zenoss"
            _update_config(service)
            log.info("Service %s updated", service.name)
            return True
        log.info("Service %s already updated", service.name)
        return False

    updated = [
        update(service, command.format(svcmap[service.name]))
        for service in services
    ]
    return any(updated)


def _update_zope_services(services, svcmap, command):
    def update(service, command, env):
        if service.runAs != "zenoss":
            service.startup = command
            service.runAs = "zenoss"
            if env not in service.environment:
                service.environment.append(env)
            log.info("Service %s updated", service.name)
            return True
        log.info("Service %s already updated", service.name)
        return False

    updated = [
        update(
            service,
            command,
            "CONFIG_FILE=/opt/zenoss/etc/{}.conf".format(svcmap[service.name])
        )
        for service in services
    ]
    return any(updated)


_new_supervisord_options = (
    ("directory", "/opt/zenoss"),
    ("redirect_stderr", "true"),
    ("stdout_logfile_maxbytes", "10MB"),
    ("stdout_logfile_backups", "2"),
    ("stdout_logfile", "/opt/zenoss/log/%(program_name)s.log"),
)


def _getConfig(service, name):
    return [
        c for c in chain(service.originalConfigs, service.configFiles)
        if c.name.endswith(name)
    ]


def _tostring(parser):
    fp = io.BytesIO()
    parser.write(fp)
    return fp.getvalue()


def _add_supervisord_options(parser, section):
    if not parser.has_section(section):
        log.info("Skipping section %s: not found", section)
        return
    options = OrderedDict(parser.items(section))
    for k, v in _new_supervisord_options:
        if k not in options:
            parser.set(section, k, v)


def _fix_paths(parser, sections):
    for app in sections:
        section = "program:%s" % (app,)

        if not parser.has_section(section):
            log.info("Skipping section %s: not found", section)
            continue

        command = parser.get(section, "command")
        if not command.startswith("/"):
            parser.set(section, "command", "/opt/zenoss/" + command)

        logfile = parser.get(section, "stdout_logfile")
        if not logfile.startswith("/opt/zenoss"):
            parser.set(section, "stdout_logfile", "/opt/zenoss/" + logfile)


def _update_central_query_conf(svc):
    configs = _getConfig(svc, "central-query_supervisor.conf")
    if not configs:
        log.info(
            "Unable to locate '%s' file of service %s",
            "central-query_supervisor.conf", svc.name
        )
        return

    for config in configs:
        parser = ConfigParser.RawConfigParser()
        parser.readfp(io.BytesIO(str(config.content)))

        original = _tostring(parser).replace(" = ", "=")

        _add_supervisord_options(parser, "program:central-query")
        _fix_paths(parser, ("central-query",))

        updated = _tostring(parser).replace(" = ", "=")

        if original != updated:
            config.content = updated


def _update_metric_consumer_conf(svc):
    configs = _getConfig(
        svc, "metric-consumer-app_supervisor.conf",
    )
    if not configs:
        log.info(
            "Unable to locate '%s' file of service %s",
            "metric-consumer-app_supervisor.conf", svc.name
        )
        return

    for config in configs:
        parser = ConfigParser.RawConfigParser()
        parser.readfp(io.BytesIO(str(config.content)))

        original = _tostring(parser).replace(" = ", "=")

        _add_supervisord_options(parser, "program:metric-consumer-app")
        _fix_paths(parser, ("metric-consumer-app",))

        section = "program:metric-consumer-app"
        if parser.has_section(section):
            if not parser.has_option(section, "stopwaitsecs"):
                parser.set(section, "stopwaitsecs", "30")

        updated = _tostring(parser).replace(" = ", "=")

        if original != updated:
            config.content = updated


_update_handler = {
    "CentralQuery": _update_central_query_conf,
    "MetricConsumer": _update_metric_consumer_conf,
}


def _update_config(svc):
    _update_handler.get(svc.name, lambda x: None)(svc)


def _update_zauth_conf(svc):
    configs = _getConfig(svc, "/opt/zenoss/etc/zauth/zauth-zope.conf")
    if not configs:
        log.info(
            "Unable to locate '%s' file of service %s",
            "zauth-zope.conf", svc.name
        )
        return False

    for config in configs:
        config.filename = "/opt/zenoss/etc/zauth.conf"
        config.name = "/opt/zenoss/etc/zauth.conf"
        log.info(
            "Renamed service '%s' config file to %s", svc.name, config.name
        )

        updated = config.content.replace(
            "%include ../zope.conf", "%include zope.conf",
        ).replace(
            "clienthome var/zauth", "clienthome /opt/zenoss/var/zauth",
        )
        if config.content != updated:
            config.content = updated
            log.info("Updated service '%s' config file", svc.name)
        else:
            log.info("Service '%s' config file already updated", svc.name)
    return True


EditServicesStartUp()
