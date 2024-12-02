##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class UpdateZookeeperConfigs(Migrate.Step):
    "Alter zookeeper.cfg."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zookeepers = filter(lambda s: s.name == "ZooKeeper", ctx.services)
        log.info("Found %i services named 'ZooKeeper'" % len(zookeepers))

        for zookeeper in zookeepers:

            # Update zookeeper.cfg.
            cfs = filter(lambda f: f.name == "/etc/zookeeper.cfg", zookeeper.originalConfigs)
            log.info("Found %i files named '/etc/zookeeper.cfg' '" % len(cfs))
            for cf in cfs:
                if cf.content.find("autopurge.snapRetainCount") < 0:
                    cf.content += "\nautopurge.snapRetainCount=3"
                    log.info("Added autopurge.snapRetainCount=3")
                else:
                    log.info("Found previous autopurge.snapRetainCount; not updating.")

                if cf.content.find("autopurge.purgeInterval") < 0:
                    cf.content += "\nautopurge.purgeInterval=1"
                    log.info("Added autopurge.purgeInterval=1")
                else:
                    log.info("Found previous autopurge.purgeInterval; not updating.")


        # Commit our changes.
        ctx.commit()


UpdateZookeeperConfigs()
