
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
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from servicemigration.endpoint import Endpoint
from servicemigration import HealthCheck
import re

sm.require("1.1.11")

ZOPES = {
  'Zauth': '/opt/zenoss/etc/zope.conf',
  'zenapi': '/opt/zenoss/etc/zenapi.conf',
  'zendebug': '/opt/zenoss/etc/zendebug.conf',
  'zenreports': '/opt/zenoss/etc/zenreports.conf',
  'Zope': '/opt/zenoss/etc/zope.conf',
}

ZOPE_SESSION_PATTERN = re.compile('session.url([ ]*) 127.0.0.1:11211')

MEMCACHED_SESSION_ENDPOINT = Endpoint(
        name="memcached-session",
        purpose="import",
        application="memcached-session",
        portnumber=11212,
        protocol="tcp"
)

MEMCACHED_SESSION_HEALTHCHECK = HealthCheck(
            name="memcached_session_answering",
            interval=10.0,
            script="/opt/zenoss/bin/healthchecks/memcached_session_answering"
)


class AddMemcachedForSessions(Migrate.Step):
    """
    Update memcache healthcheck, and add the service to Core
    """

    version = Migrate.Version(200, 2, 0)
    changed = False

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        self.addMemcachedSssionsService(ctx)
        self.updateZopes(ctx)

        if self.changed:
            ctx.commit()

    def updateZopes(self, ctx):

        for zope in ZOPES.keys():
            services = filter(lambda s: s.name == zope, ctx.services)
            for service in services:
                currentEndpoints = [endpoint.name for endpoint in service.endpoints]
                if "memcached-session" not in currentEndpoints:
                    service.endpoints.append(MEMCACHED_SESSION_ENDPOINT)
                    for config in service.originalConfigs:
                        if ZOPES.get(service.name):
                            log.info("Updating original config %s for %s service", config.name, service.name)
                            config.content = ZOPE_SESSION_PATTERN.sub('session.url\\1 127.0.0.1:11212', config.content)
                            self.changed = True

                    for config in service.configFiles:
                        if ZOPES.get(service.name):
                            log.info("Updating current config %s for %s service", config.name, service.name)
                            config.content = ZOPE_SESSION_PATTERN.sub('session.url\\1 127.0.0.1:11212', config.content)
                            self.changed = True


                if not filter(lambda c: c.name == 'memcached_session_answering', service.healthChecks):
                    service.healthChecks.append(MEMCACHED_SESSION_HEALTHCHECK)
                    self.changed = True


    def addMemcachedSssionsService(self, ctx):
        memcached = filter(lambda s: s.name == "memcached-session", ctx.services)
        log.info("Found %i services named 'memcached'." % len(memcached))
        if not memcached:
            log.info("Creating new memcached-session service.")
            imageID = os.environ['SERVICED_SERVICE_IMAGE']
            new_memcached = memcached_sessions_service(imageID)
            infrastructure = ctx.findServices('^[^/]+/Infrastructure$')[0]
            ctx.deployService(json.dumps(new_memcached), infrastructure)
            self.changed = True


def memcached_sessions_service(imageID):
    return {
        "CPUCommitment": 1,
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenmemcached",
        "ConfigFiles": {
            "/etc/sysconfig/memcached": {
                "Filename": "/etc/sysconfig/memcached",
                "Owner": "root:root",
                "Permissions": "0644",
                "Content": 'PORT="11211"\nUSER="nobody"\
                \nMAXCONN="1024"\nCACHESIZE="{{percentScale .RAMCommitment 0.9 | bytesToMB}}"\
                \n{{ $size := (getContext . "global.conf.zodb-cache-max-object-size") }}\
                \nOPTIONS="-v -R 4096 -I {{if $size}} {{$size}} {{else}} 1048576 {{end}}"'
            }
        },
        "Description": "Dedicated memcached instance for zope sessions",
        "Endpoints": [
            {
                "Application": "memcached-session",
                "Name": "memcached-session",
                "ApplicationTemplate": "memcached-session",
                "PortNumber": 11211,
                "Protocol": "tcp",
                "Purpose": "export"
            }
        ],
        "HealthChecks": {
            "answering": {
                "Interval": 5.0,
                "Script": "{ echo stats; sleep 1; } | nc 127.0.0.1 11211 | grep -q uptime"
            }
        },
        "ImageID": imageID,
        "Instances": {
            "Min": 1
        },
        "Launch": "auto",
        "Name": "memcached-session",
        "RAMCommitment": "1G",
        "Tags": [
            "daemon"
        ]
    }

AddMemcachedForSessions()
