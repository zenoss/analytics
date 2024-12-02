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
sm.require("1.0.0")


class CheckHBaseTablesExist(Migrate.Step):
    """
    Add existence of HBase tables to the Prereqs of OpenTSDB reader.
    See ZEN-24094
    """

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Find the services to edit.
        # For "lite" services, there is a single opentsdb service and, it should
        # not be edited. For "full" services, the opentsdb service is an organizer
        # with reader and writer subservices. The reader services should be
        # edited.
        opentsdbs = [i for i in ctx.services if i.name == 'opentsdb' ]
        readers = [i for i in ctx.services if i.name == 'reader' and
                ctx.getServiceParent(i) in opentsdbs]

        changed = False

        for reader in readers:
            reader.prereqs = [sm.Prereq(name='HBase Regionservers up', script='{{with $rss := (child (child (parent (parent .)) "HBase") "RegionServer").Instances }}wget -q -O- http://localhost:61000/status/cluster | grep \'{{$rss}} live servers\'{{end}}'), sm.Prereq(name='HBase tables exist', script='wget -q -O- http://localhost:61000 | [[ $(grep -c -E -o \"\\b${CONTROLPLANE_TENANT_ID}-tsdb(-|\\s|$)\") == 4 ]]')]
            changed = True

        if changed:
            ctx.commit()

CheckHBaseTablesExist()
