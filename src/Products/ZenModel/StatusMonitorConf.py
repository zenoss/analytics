##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import warnings
warnings.warn('Products.Device.StatusMonitorConf', DeprecationWarning)

__doc__="""StatusMonitorConf

The configuration object for monitors.

"""

from Products.ZenRelations.RelSchema import *

from Products.ZenModel.Monitor import Monitor
from Products.ZenModel.StatusColor import StatusColor


class StatusMonitorConf(Monitor, StatusColor):
    '''Configuration for monitors'''
    portal_type = meta_type = "StatusMonitorConf"

    monitorRootName = "StatusMonitors"

    _relations = (
        ("devices", ToMany(ToMany,"Products.ZenModel.Device","monitors")),
        )
