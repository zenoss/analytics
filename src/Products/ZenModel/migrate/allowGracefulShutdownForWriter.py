##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
import servicemigration as sm
import Migrate


log = logging.getLogger("zen.migrate")
sm.require("1.1.14")


class AllowGracefulShutdownForWriter(Migrate.Step):
    """Modify opentsdb-writer service def for graceful shutdown."""

    version = Migrate.Version(200, 5, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        service = next(
            (s for s in ctx.services if s.name == "writer"), None,
        )
        if service is None:
            log.error("Unable to find the 'opentsdb-writer' service")
            return

        if "/bin/sh" not in service.startup:
            log.info("Nothing to migrate")
            return
        service.startup = "/opt/opentsdb/start-opentsdb.sh {{with $zks := (child (child (parent"\
            " (parent .)) \"HBase\") \"ZooKeeper\").Instances }}{{ range (each $zks) }}localhost"\
            ":{{plus 2181 .}}{{if ne (plus 1 .) $zks}},{{end}}{{end}}{{end}}"
        service.environment = [
            "TSDB_JAVA_MEM_MB=-Xmx{{bytesToMB .RAMCommitment}}m",
            "{{ if eq .InstanceID 0 }}CREATE_TABLES=1{{else }}CREATE_TABLES=0{{ end }}"
        ]
        ctx.commit()
        log.info("Updated the 'opentsdb-writer' service")


AllowGracefulShutdownForWriter()
