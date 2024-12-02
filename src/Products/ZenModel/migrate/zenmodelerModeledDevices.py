##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """Provide a graph for zenmodeler's modeled device rate.
"""
import logging
from Products.ZenUtils.Utils import unused
from Products.ZenModel.migrate import Migrate


log = logging.getLogger('zen.migrate')

_MODELED_DEVICES_ID = 'modeledDevices'
_MODELED_DEVICES_GRAPH_ID = 'Modeled Devices'

class zenmodelerModeledDevices(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        rrdTemplate = dmd.Monitors.rrdTemplates.PerformanceConf
        dp = rrdTemplate.datasources.zenmodeler.datapoints._getOb(_MODELED_DEVICES_ID, None)
        if dp is None:
            log.info("Adding modeledDevices datapoint and graph.")
            dp = rrdTemplate.datasources.zenmodeler.manage_addRRDDataPoint(_MODELED_DEVICES_ID)
            dp.rrdtype = 'DERIVE'

        modeledDevicesGD = rrdTemplate.graphDefs._getOb(_MODELED_DEVICES_GRAPH_ID, None)
        if modeledDevicesGD is None:
            modeledDevicesGD = rrdTemplate.manage_addGraphDefinition(_MODELED_DEVICES_GRAPH_ID)
            modeledDevicesGD.units = 'devices / sec'
            modeledDevicesGD.manage_addDataPointGraphPoints(['zenmodeler_modeledDevices',])

zenmodelerModeledDevices()
