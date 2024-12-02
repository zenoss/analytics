##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
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
sm.require("1.0.0")


class AddMemcachedService(Migrate.Step):
    """
    Update memcache healthcheck, and add the service to Core
    """

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # If the service lacks memcached, add it now.
        memcached = filter(lambda s: s.name == "memcached", ctx.services)
        log.info("Found %i services named 'memcached'." % len(memcached))
        if not memcached:
            log.info("No memcached found; creating new service.")
            new_memcached = default_memcached_service()
            infrastructure = ctx.findServices('^[^/]+/Infrastructure$')[0]
            ctx.deployService(json.dumps(new_memcached), infrastructure)
            ctx.commit()


def default_memcached_service():
    return {
        "CPUCommitment": 1,
        "Command": "/bin/memcached -u nobody -v -m {{percentScale .RAMCommitment 0.9 | bytesToMB}}",
        "ConfigFiles": {
            "/etc/sysconfig/memcached": {
                "Filename": "/etc/sysconfig/memcached",
                "Owner": "root:root",
                "Permissions": "0644",
                "Content": 'PORT="11211"\nUSER="memcached"\nMAXCONN="1024"\nCACHESIZE="{{.RAMCommitment}}"\nOPTIONS=""\n'
            }
        },
        "Description": "Free & open source, high-performance, distributed memory object caching system",
        "Endpoints": [
            {
                "Application": "memcached",
                "ApplicationTemplate": "memcached",
                "Name": "memcached",
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
        "ImageID": os.environ['SERVICED_SERVICE_IMAGE'],
        "Instances": {
            "Min": 1
        },
        "Launch": "auto",
        "Name": "memcached",
        "RAMCommitment": "1G",
        "Tags": [
            "daemon"
        ]
    }

AddMemcachedService()
