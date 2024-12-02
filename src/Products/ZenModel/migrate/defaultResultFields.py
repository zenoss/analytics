##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add eventState and severity as default result fields.

'''
import Migrate

class AddResultFields(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        zem = dmd.ZenEventManager
        for attr in ('DeviceResultFields', 'ComponentResultFields',
                     'defaultResultFields'):
            curfields = list(getattr(zem, attr))
            if 'eventState' not in curfields:
                curfields.insert(0, 'eventState')
            if 'severity' not in curfields:
                curfields.insert(1, 'severity')
            setattr(zem, attr, tuple(curfields))

AddResultFields()
