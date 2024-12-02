##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from Products.ZenHub.errors import translateError
from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
from Products.ZenModel.ValueChangeThreshold import ValueChangeThreshold

log = logging.getLogger("zen.thresholdmixin")


class ThresholdMixin(object):
    _cached_thresholdClasses = []

    @translateError
    def remote_getThresholdClasses(self):
        log.info("retrieving threshold classes")
        try:
            if not self._cached_thresholdClasses:
                classes = [MinMaxThreshold, ValueChangeThreshold]
                for pack in self.dmd.ZenPackManager.packs():
                    classes += pack.getThresholdClasses()
                self._cached_thresholdClasses = map(
                    lambda c: c.__module__, classes
                )
            return self._cached_thresholdClasses
        finally:
            log.info(
                "retrieved threshold classes: %s",
                self._cached_thresholdClasses,
            )

    @translateError
    def remote_getCollectorThresholds(self):
        from Products.ZenModel.BuiltInDS import BuiltInDS

        log.info("retrieving threshold instances")
        instances = None
        try:
            instances = self.conf.getThresholdInstances(BuiltInDS.sourcetype)
        finally:
            log.info("retrieved threshold instances: %s", instances)

        return instances
