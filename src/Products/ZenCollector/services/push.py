##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenHub.zodb import onUpdate
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenModel.ZenPack import ZenPack
from Products.ZenUtils.AutoGCObjectReader import gc_cache_every


class UpdateCollectorMixin(object):
    """Push data back to collection daemons."""

    @onUpdate(PerformanceConf)
    def perfConfUpdated(self, conf, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            if conf.id == self.instance:
                for listener in self.listeners:
                    listener.callRemote(
                        "setPropertyItems", conf.propertyItems()
                    )

    @onUpdate(ZenPack)
    def zenPackUpdated(self, zenpack, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            for listener in self.listeners:
                try:
                    listener.callRemote(
                        "updateThresholdClasses",
                        self.remote_getThresholdClasses(),
                    )
                except Exception:
                    self.log.warning(
                        "Error notifying a listener of new threshold classes"
                    )
