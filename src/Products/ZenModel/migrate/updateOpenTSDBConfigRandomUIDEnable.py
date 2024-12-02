##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import servicemigration as sm
import servicemigration.service as service


sm.require("1.0.0")
log = logging.getLogger("zen.migrate")


class UpdateOpenTSDBConfigRandomUIDEnable(Migrate.Step):
    """ Enable OpenTSDB random UID assignment

        This migration step iterates through services that have opentsdb.conf as an original
        configuration file.  For each of these services both original and latest config fles
        are checked to see to see they have the parameter 'tsd.core.uid.random_metrics'.
        - If the paramter does not exist then the parameter is added and set to True (enabled).
        - If the paramter already exists then no change is made to the config file.
    """

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        """ This method is called by the migration process and overrides the method
            located in the parent class Migrate.Step.
        """
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        tsdbs = filter(lambda s: "opentsdb" in ctx.getServicePath(s), ctx.services)
        log.info("Found %i services with 'opentsdb' in their service path." % len(tsdbs))

        tsdbs = filter(lambda s: "/opt/zenoss/etc/opentsdb/opentsdb.conf" in [i.name for i in s.originalConfigs], tsdbs)
        log.info("Of those, %i services use /opt/zenoss/etc/opentsdb/opentsdb.conf." % len(tsdbs))

        for tsdb in tsdbs:
            original_configs = filter(lambda f: f.name == "/opt/zenoss/etc/opentsdb/opentsdb.conf", tsdb.originalConfigs)
            log.info("Found %i original config files named '/opt/zenoss/etc/opentsdb/opentsdb.conf'." % len(original_configs))
            for config in original_configs:
                if config.content.find("tsd.core.uid.random_metrics") < 0:
                    config.content += "tsd.core.uid.random_metrics = True\n"
                    log.info("Updated original config with parameter tsd.core.uid.random_metrics enabled")

            configs = filter(lambda f: f.name == "/opt/zenoss/etc/opentsdb/opentsdb.conf", tsdb.configFiles)
            log.info("Found %i config files named '/opt/zenoss/etc/opentsdb/opentsdb.conf'." % len(configs))
            for config in configs:
                if config.content.find("tsd.core.uid.random_metrics") < 0:
                    config.content += "tsd.core.uid.random_metrics = True\n"
                    log.info("Updated config with parameter tsd.core.uid.random_metrics enabled")

        # Commit our changes.
        ctx.commit()

UpdateOpenTSDBConfigRandomUIDEnable()
