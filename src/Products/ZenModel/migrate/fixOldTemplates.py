##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Update existing templates to include fixes in r7650.

$Id:$
'''
import Migrate
import re

class FixOldTemplates(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import twotwoindexing
        self.dependencies = [ twotwoindexing.twotwoindexing ]

    def cutover(self, dmd):
        for template in dmd.Devices.getAllRRDTemplates():
            if template.id == 'FileSystem':
                for graph in template.graphDefs():
                    if graph.id == 'Utilization':
                        self.fixFileSystemTemplates(graph)
                        continue

            for graph in template.graphDefs():
                if graph.id == 'Throughput':
                    self.fixIpInterfaceTemplates(graph)
                    continue


    def fixFileSystemTemplates(self, graph):
        if not graph.custom.startswith('CDEF:percent=usedBlocks'): return
        graph.custom = ''
        graph.miny = 0
        graph.maxy = 100
        for gp in graph.graphPoints():
            if gp.id != 'usedBlocks': continue
            gp.lineType = 'AREA'
            gp.format = '%5.2lf%%'
            gp.legend = 'Used'
            gp.rpn = '${here/totalBlocks},/,100,*'


    def fixIpInterfaceTemplates(self, graph):
        if graph.custom: return
        if not re.search('bits', graph.units, re.I): return
        graph.units = 'bits/sec'
        graph.miny = 0
        for gp in graph.graphPoints():
            if not gp.id.endswith('Octets') or gp.rpn: continue
            gp.rpn = '8,*'
            if gp.id.endswith('InOctets'):
                gp.legend = 'Inbound'
            elif gp.id.endswith('OutOctets'):
                gp.legend = 'Outbound'


FixOldTemplates()
