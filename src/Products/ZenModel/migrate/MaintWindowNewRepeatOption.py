##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = '''

Edit Maintenance Window properties to comply with ZEN-13930 fix

$Id:$
'''
import Migrate


class UpdateMW(Migrate.Step):
    version = Migrate.Version(4, 2, 5)

    def cutover(self, dmd):
        for brain in dmd.maintenanceWindowSearch():
            try:
                m = brain.getObject()
            except Exception:
                continue
            if m.repeat == 'First Sunday of the Month':
                m.repeat = 'Monthly: day of week'
                m.days = 'Sunday'
                m.occurrence = '1st'
            elif m.repeat == 'Monthly':
                m.repeat = 'Monthly: day of month'

UpdateMW()
