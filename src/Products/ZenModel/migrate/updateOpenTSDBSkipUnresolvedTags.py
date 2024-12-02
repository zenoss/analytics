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


class UpdateOpenTSDBSkipUnresolvedTags(Migrate.Step):
    """ Enable OpenTSDB option to skip unresolved tags.

        This migration step iterates through services that have opentsdb.conf as an original
        configuration file.  For each of these services both original and latest config files
        are checked to see to see they have the parameter 'tsd.query.skip_unresolved_tagvs'.
        - If the parameter does not exist, then the parameter is added and set to True (enabled).
        - If the parameter already exists, then no change is made to the config file.
    """

    version = Migrate.Version(110, 0, 0)
    SKIP_UNRESOLVED_TAGVS = 'tsd.query.skip_unresolved_tagvs'

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
                if config.content.find(self.SKIP_UNRESOLVED_TAGVS) < 0:
                    config.content += "%s = True\n" % self.SKIP_UNRESOLVED_TAGVS
                    log.info("Updated original config with parameter %s enabled" % self.SKIP_UNRESOLVED_TAGVS)

            configs = filter(lambda f: f.name == "/opt/zenoss/etc/opentsdb/opentsdb.conf", tsdb.configFiles)
            log.info("Found %i config files named '/opt/zenoss/etc/opentsdb/opentsdb.conf'." % len(configs))
            for config in configs:
                if config.content.find(self.SKIP_UNRESOLVED_TAGVS) < 0:
                    config.content += "%s = True\n" % self.SKIP_UNRESOLVED_TAGVS
                    log.info("Updated config with parameter %s enabled" % self.SKIP_UNRESOLVED_TAGVS)

        # Commit our changes.
        ctx.commit()

UpdateOpenTSDBSkipUnresolvedTags()

