##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Migrate


"""
Add zStatusEventClass z property. That allows you to choose what event class
will affect on device status(change Up/Down status).
"""


class AddzStatusEventClass(Migrate.Step):
    version = Migrate.Version(200, 4, 0)

    def cutover(self, dmd):
        if not hasattr(dmd.Devices, 'zStatusEventClass'):
            dmd.Devices._setProperty('zStatusEventClass', '/Status/',
                                     type='string')
        elif dmd.Devices.zStatusEventClass == '/Status/*':
            dmd.Devices._updateProperty('zStatusEventClass', '/Status/')

AddzStatusEventClass()
