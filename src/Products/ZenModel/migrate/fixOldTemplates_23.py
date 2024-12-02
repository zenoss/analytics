##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Fix templates for defect #2719

$Id:$
'''
import Migrate

class FixOldTemplates_23(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        for template in dmd.Devices.getAllRRDTemplates():
            for graph in template.graphDefs():
                if graph.id == 'Throughput':
                    self.fixIpInterfaceTemplates(graph)
                    continue

    def fixIpInterfaceTemplates(self, graph):
        if graph.custom: return
        for gp in graph.graphPoints():
            if gp.id.endswith('InOctets'):
                gp.legend = 'Inbound'
            elif gp.id.endswith('OutOctets'):
                gp.legend = 'Outbound'

FixOldTemplates_23()
