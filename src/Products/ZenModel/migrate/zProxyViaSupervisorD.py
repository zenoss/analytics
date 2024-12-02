
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm

sm.require("1.1.8")

zproxy_supervisord_conf = '''\
[supervisord]
nodaemon=true
logfile = /opt/zenoss/log/zproxy_supervisord.log

[unix_http_server]
file=/tmp/supervisor.sock

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock ; use a unix:// URL  for a unix socket

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:redis]
command=redis-server /etc/redis.conf
autorestart=true
autostart=true
startsecs=5
priority=1

[program:zproxy]
command=/opt/zenoss/zproxy/sbin/zproxy start
directory=/opt/zenoss
autorestart=true
autostart=true
startsecs=5
priority=1

[program:zproxy_metrics]
command=/usr/bin/python /opt/zenoss/bin/metrics/zenossStatsView.py
autorestart=true
autostart=true
startsecs=5

; logging
redirect_stderr=true
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=10
stdout_logfile=/opt/zenoss/log/%(program_name)s.log
'''


class ZProxyViaSupervisorD(Migrate.Step):
    """Run zproxy via supervisord."""

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zproxy = ctx.getTopService()
        commit = False
        if zproxy.startup.startswith('redis-server'):
            zproxy.startup = "/bin/supervisord -n -c /etc/zproxy/zproxy_supervisor.conf"

            zsc = sm.ConfigFile(
                name='/etc/zproxy/zproxy_supervisor.conf',
                filename='/etc/zproxy/zproxy_supervisor.conf',
                owner='zenoss:zenoss',
                permissions='644',
                content=zproxy_supervisord_conf)
            zproxy.configFiles.append(zsc)
            zproxy.originalConfigs.append(zsc)

            commit = True

        if commit:
            ctx.commit()

ZProxyViaSupervisorD()
