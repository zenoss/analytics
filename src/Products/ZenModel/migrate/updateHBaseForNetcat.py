##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
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


class UpdateHBaseForNetcat(Migrate.Step):
    """ Recursively update all the HBase service healthchecks.  Necessary
    due to the hbase image changing from an ubuntu base to a centos base,
    which means BSD netcat to GNU netcat """

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        changes = False

        # 1) HMaster's prereq
        hmasters = filter(lambda s: s.name == "HMaster", ctx.services)
        log.info("Found %i services named 'HMaster'." % len(hmasters))
        for hmaster in hmasters: # Should only be one
            for prereq in filter(lambda p: p.name == 'All ZooKeepers up', hmaster.prereqs): # Should only be one
                if prereq.script == '{{with $zks := (child (parent .) \"ZooKeeper\").Instances }}{{ range (each $zks) }}echo ruok | nc -q10 zk{{plus 1 .}} 2181 | grep imok {{if ne (plus 1 .) $zks}}&& {{end}}{{end}}{{end}}':
                    prereq.script = '{{with $zks := (child (parent .) \"ZooKeeper\").Instances }}{{ range (each $zks) }}{ echo ruok; sleep 2; } | nc zk{{plus 1 .}} 2181 | grep imok {{if ne (plus 1 .) $zks}}&& {{end}}{{end}}{{end}}'
                    log.info("Added sleep to 'All ZooKeepers up' prereq.")
                    changes = True
                else:
                    log.info("No 'All ZooKeepers up' prereq found; skipping.")

        # 2) ZK Healthchecks
        zks = filter(lambda s: s.name == "ZooKeeper", ctx.services)
        log.info("Found %i services named 'ZooKeeper'." % len(zks))
        for zk in zks:
            answering = filter(lambda hc: hc.name == "answering", zk.healthChecks)
            log.info("Found %i 'answering' healthchecks." % len(answering))
            if len(answering) != 1:
                continue
            answering = answering[0]
            if answering.script == 'echo stats | nc -q 1 localhost {{ plus 2181 .InstanceID }} | grep -q Zookeeper':
                answering.script = '{ echo stats; sleep 1; } | nc 127.0.0.1 {{ plus 2181 .InstanceID }} | grep -q Zookeeper'
                log.info("Added sleep to 'answering' healthcheck.")
                changes = True
            else:
                log.info("Healthcheck is not as expected; skipping.")

        # 3) RegionServer Healthchecks
        regionservers = filter(lambda s: s.name == "RegionServer", ctx.services)
        log.info("Found %i services named 'RegionServer'." % len(regionservers))
        for rs in regionservers:
            answering = filter(lambda hc: hc.name == "answering", rs.healthChecks)
            log.info("Found %i 'answering' healthchecks." % len(answering))
            if len(answering) != 1:
                continue
            answering = answering[0]
            if answering.script == 'nc -z localhost {{ plus 60200 .InstanceID }}':
                answering.script = 'echo | nc localhost {{ plus 60200 .InstanceID }}'
                log.info("Added echo to 'answering' healthcheck.")
                changes = True
            else:
                log.info("Healthcheck is not as expected; skipping.")

        if changes:
            ctx.commit()

UpdateHBaseForNetcat()
