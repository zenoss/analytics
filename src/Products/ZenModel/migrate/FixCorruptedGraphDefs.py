##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = '''

Fix templates for defect #7718

$Id:$
'''
import Migrate


class FixCorruptedGraphDefs(Migrate.Step):
    version = Migrate.Version(3, 0, 2)

    def cutover(self, dmd):
        for template in dmd.Devices.getAllRRDTemplates():
            for graphDef in template.graphDefs():
                self.zenfixit(graphDef)

    def zenfixit(self, graphDef):
        try:
            graphDef.miny = int(graphDef.miny)
        except ValueError:
            graphDef.miny = -1

        try:
            graphDef.maxy = int(graphDef.maxy)
        except ValueError:
            graphDef.maxy = -1


FixCorruptedGraphDefs()
