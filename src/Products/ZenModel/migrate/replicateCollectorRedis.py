##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm

sm.require("1.1.9")


class ReplicateCollectorRedis(Migrate.Step):
    """
    Add existence of HBase tables to the Prereqs of OpenTSDB reader.
    See ZEN-24094
    """

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        svcs = filter(lambda s: all(x in s.tags for x in ["collector", "daemon"]), ctx.services)
        daemons = ([svc for svc in svcs
            if not svc.name == 'collectorredis'
            and not svc.name == 'zminion'])

        collectorRedises = [svc for svc in svcs if svc.name == 'collectorredis']
        ignoreDaemonList = ['RabbitMQ-Ceilometer',]

        changed = False

        for daemon in daemons:
            if daemon.name in ignoreDaemonList:
                continue
            try:
                collectorRedisEndpoint = ([
                    endpoint for endpoint in daemon.endpoints
                    if endpoint.name == 'CollectorRedis'][0])
                collectorRedisEndpoint.purpose = 'import_all'
                changed = True
            except IndexError:
                log.error(
                        "Collector redis endpoint does not exist in {} "
                        "service definition.".format(daemon.name)
                )
                return

        for collectorRedis in collectorRedises:
            parent = ctx.getServiceParent(collectorRedis)
            parentName = parent.name if parent else ""

            collectorRedis.startup = "{{ if ne .InstanceID 0 }} /bin/sed -i 's/# slaveof <masterip> <masterport>/slaveof rd1 6379/' /etc/redis.conf & {{ end }} /usr/bin/redis-server /etc/redis.conf"
            collectorRedis.changeOptions = ['restartAllOnInstanceZeroDown']
            collectorRedis.hostPolicy = 'REQUIRE_SEPARATE'
            collectorRedis.privileged = True
            collectorRedis.instanceLimits.maximum = 0

            endpoints = []
            endpoints.append(
                sm.Endpoint(
                    name = 'zproxy',
                    purpose = 'import',
                    application = 'zproxy',
                    portnumber = 8080,
                    protocol = 'tcp',
                    applicationtemplate = 'zproxy'
            ))
            endpoints.append(
                sm.Endpoint(
                    name = 'CollectorRedis',
                    purpose = 'export',
                    application = parentName + '_redis',
                    portnumber = 6379,
                    protocol = 'tcp',
                    applicationtemplate = '{{(parent .).Name}}_redis'
            ))
            endpoints.append(
                sm.Endpoint(
                    name = 'CollectorRedises',
                    purpose = 'import_all',
                    application = parentName + '_redis',
                    portnumber = 16379,
                    protocol = 'tcp',
                    applicationtemplate = '{{(parent .).Name}}_redis',
                    virtualaddress = 'rd{{ plus 1 .InstanceID }}:6379'
            ))

            collectorRedis.endpoints = endpoints
            changed = True

        if changed:
            ctx.commit()

ReplicateCollectorRedis()
