##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
Add zCommandUserCommandTimeout z property.  This one is only applied for
user commands run.
'''

import Migrate


class addzCommandUserCommandTimeout(Migrate.Step):

    version = Migrate.Version(107, 0, 0)

    def cutover(self, dmd):
        if not hasattr(dmd.Devices, 'zCommandUserCommandTimeout'):
            dmd.Devices._setProperty('zCommandUserCommandTimeout', 15.0, type='float')


addzCommandUserCommandTimeout()
