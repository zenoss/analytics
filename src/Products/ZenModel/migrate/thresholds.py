##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
from Products.ZenModel.ThresholdClass import ThresholdClass

import logging
log = logging.getLogger("zen.migrate")

class Thresholds(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def replaceThreshold(self, template, old):
        if not isinstance(old, ThresholdClass):
            new = MinMaxThreshold(old.id)
            template.thresholds.removeRelation(old)
            for p in old._properties:
                name = p['id']
                setattr(new, name, getattr(old, name))
            old = new
        template.thresholds._setObject(old.id, old)

    def cutover(self, dmd):
        for t in dmd.Devices.getAllRRDTemplates():
            log.debug("Converting thresholds on %r", t)
            for old in t.thresholds():
                log.debug("   %r", old)
                self.replaceThreshold(t, old)

thresholds = Thresholds()
