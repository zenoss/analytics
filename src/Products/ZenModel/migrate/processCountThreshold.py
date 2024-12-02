##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate
from Products.AdvancedQuery import Eq
from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
from Products.Zuul.interfaces import ICatalogTool

class ProcessCountThreshold(Migrate.Step):
    version = Migrate.Version(4, 2, 4)

    def cutover(self, dmd):
        templates = ICatalogTool(dmd).search("Products.ZenModel.RRDTemplate.RRDTemplate",
                                             query=Eq("name", "OSProcess"))
        for t in templates:
            template = t.getObject()
            threshold = MinMaxThreshold('count')
            template.thresholds._setObject("count", threshold)
            t = template.thresholds._getOb("count")
            t.dsnames = ProcessCountThreshold.datapoints(template)
            print t.getPrimaryId(), t.dsnames, t
            t.minval = 'here.getMinProcessCount()'
            t.maxval = 'here.getMaxProcessCount()'

    @staticmethod
    def datapoints(template):
        return ["%s_count" % d.id for d in template.datasources() \
                    if any(True for p in d.datapoints() if p.id == "count")]

ProcessCountThreshold()
