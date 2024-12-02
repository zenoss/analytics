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
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.1.0")

_CMD = (
    "/bin/supervisord "
    "-n "
    "-c "
    "/etc/mariadb/mariadb_supervisor.conf"
)

_ConfigContent = """\
[supervisord]
nodaemon=true
logfile = /opt/zenoss/log/{service}_supervisord.log

[unix_http_server]
file=/tmp/supervisor.sock

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock ; use a unix:// URL  for a unix socket

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:mariadb]
command=/usr/bin/mysqld_safe
autorestart=true
autostart=true
startsecs=5
priority=1

[program:{section}_metrics]
command=/usr/bin/python /opt/zenoss/bin/metrics/storagestats.py {service}
autorestart=true
autostart=true
startsecs=5

; logging
redirect_stderr=true
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=10
stdout_logfile=/opt/zenoss/log/%(program_name)s.log
"""


class CollectHBaseAndMariaStorageMetrics(Migrate.Step):
    """
    * Update MariaDB services to use supervisord.
    * Add mariadb's supervisord config file.
    * Update HBase's config file.
    """
    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context. Skipping.")
            return

        top_service = ctx.getTopService()
        log.info("Found top level service: '%s'", top_service.name)

        for name in ("mariadb-model", "mariadb-events", "mariadb"):
            svc = self._getService(ctx, name)
            if svc is None:
                continue
            if top_service.name == "Zenoss.resmgr":
                self._updateMariaDBCommand(svc)
            self._addMariaDBConfig(svc)

        hmaster = self._getService(ctx, "HMaster")
        self._updateHBaseMetricsConfig(
            hmaster, (
                "hbase.sink.file-all.includedMetrics="
                "Log\\\\w*,"
                "\\\\w*RegionServers,"
                "hbase\\.regionserver\\.\\\\w*,"
                "storeFile\\\\w*"
            )
        )
        regionserver = self._getService(ctx, "RegionServer")
        self._updateHBaseMetricsConfig(
            regionserver, (
                "hbase.sink.file-all.includedMetrics="
                "numCallsInGeneralQueue,"
                "numCallsIn\\\\w*Queue,"
                "\\\\w*QueueLength,"
                "\\\\w*Count,"
                "\\\\w+RequestCount,"
                "storeFile\\\\w*"
            )
        )

        ctx.commit()

    def _getService(self, ctx, name):
        return next(
            iter(filter(lambda s: s.name == name, ctx.services)), None
        )

    def _getConfigs(self, ctx, name):
        original_conf = next(
            iter(filter(lambda s: s.name == name, ctx.originalConfigs)), None
        )
        config_file = next(
            iter(filter(lambda s: s.name == name, ctx.configFiles)), None
        )
        return (original_conf, config_file)

    def _updateMariaDBCommand(self, service):
        if service.startup == _CMD:
            log.info("%s startup command already updated", service.name)
            return
        service.startup = _CMD
        log.info("Updated startup command for %s", service.name)

    def _addMariaDBConfig(self, service):
        original, config = self._getConfigs(
            service, "/etc/mariadb/mariadb_supervisor.conf"
        )
        new_config = sm.ConfigFile(
            name="/etc/mariadb/mariadb_supervisor.conf",
            filename="/etc/mariadb/mariadb_supervisor.conf",
            owner="root:root",
            permissions="0664",
            content=_ConfigContent.format(
                service=service.name,
                section=service.name.replace("-", "_")
            )
        )
        if not original:
            service.originalConfigs.append(new_config)
            log.info(
                "Added %s config to service %s originalConfigs",
                new_config.name, service.name
            )
        else:
            log.info(
                "Service %s originalConfigs already has %s",
                service.name, new_config.name
            )
        if not config:
            service.configFiles.append(new_config)
            log.info(
                "Added %s config to service %s configFiles",
                new_config.name, service.name
            )
        else:
            log.info(
                "Service %s configFiles already has %s",
                service.name, new_config.name
            )

    def _updateHBaseMetricsConfig(self, service, configLine):
        cfgName = "/opt/hbase/conf/hadoop-metrics2-hbase.properties"
        original, config = self._getConfigs(service, cfgName)
        for section, cfg in (
                ("OriginalConfigs", original), ("ConfigFiles", config)):
            if cfg is None:
                log.warn(
                    "File %s not found in %s for service %s",
                    cfgName, section, service.name
                )
                continue
            content = cfg.content.split("\n")
            for num, line in enumerate(content):
                if not line.startswith("hbase.sink.file-all.includedMetrics"):
                    continue
                if content[num] == configLine:
                    break
                content[num] = configLine
                metricsPrefixOption = "hbase.sink.file-all.metricsPrefix"
                if not content[num+1].startswith(metricsPrefixOption):
                    content[num+1:num+1] = [
                        "%s=zenoss.hbase." % metricsPrefixOption
                    ]
                break
            else:
                log.info(
                    "Cannot locate option "
                    "'hbase.sink.file-all.includeMetrics' in service "
                    "%s's config, %s.", service.name, cfgName
                )
            cfg.content = "\n".join(content)


CollectHBaseAndMariaStorageMetrics()
