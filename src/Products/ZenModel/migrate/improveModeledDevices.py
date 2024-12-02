##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Change modeledDevices datapoint rrdtype to COUNTER and set 0 to Min Y in
'Modeled Devices' graph defenition
"""

import logging
import Migrate
from Products.ZenUtils.Utils import unused

log = logging.getLogger("zen.migrate")


_MODELED_DEVICES_ID = 'modeledDevices'
_MODELED_DEVICES_GRAPH_ID = 'Modeled Devices'


class ImproveModeledDevices(Migrate.Step):

    version = Migrate.Version(114,0,0)

    def cutover(self, dmd):
        rrdTemplate = dmd.Monitors.rrdTemplates.PerformanceConf
        dp = rrdTemplate.datasources.zenmodeler.datapoints._getOb(_MODELED_DEVICES_ID, None)
        if dp is not None:
            dp.rrdtype = 'COUNTER'

	modeledDevicesGD = rrdTemplate.graphDefs._getOb(_MODELED_DEVICES_GRAPH_ID, None)
	if modeledDevicesGD is not None:
            modeledDevicesGD.miny = 0


ImproveModeledDevices()
