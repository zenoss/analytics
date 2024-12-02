##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
This removes some daemons that no longer exist from the localhost performance template.
"""

import logging
import Migrate

log = logging.getLogger("zen.migrate")

class UpdateLocalhostTemplate(Migrate.Step):
    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        collectorTemplate = dmd.unrestrictedTraverse('/zport/dmd/Monitors/rrdTemplates/PerformanceConf', None)
        if not collectorTemplate is None:
            datasourcesToRemove = ('zenwin', 'zeneventlog')
            # find the datasources and remove them
            for datasource in datasourcesToRemove:
                if collectorTemplate.datasources._getOb(datasource, None):
                    collectorTemplate.datasources._delObject(datasource)

            # now make sure that these datasources are not in the graphs
            for graph in collectorTemplate.graphDefs():
                for datasource in datasourcesToRemove:
                    if graph.graphPoints._getOb(datasource, None):
                        graph.graphPoints._delObject(datasource)
            # event queue log named these graph points terribly so search for them
            eventQueueGraph = collectorTemplate.graphDefs._getOb('Event Queue', None)
            if eventQueueGraph is None:
                return
            for datasource in datasourcesToRemove:
                for p in eventQueueGraph.graphPoints():
                    if hasattr(p, 'dpName') and datasource in p.dpName:
                        p.graphPoints._delObject(p.id)
            # remove the cycle points graph since we don't collect this metric anymore
            if collectorTemplate.graphDefs._getOb('Data Points', None):
                collectorTemplate.graphDefs._delObject('Data Points')
UpdateLocalhostTemplate()
