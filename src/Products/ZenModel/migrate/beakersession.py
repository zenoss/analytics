##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Migrate to using beaker session

'''

import Migrate

class BeakerSession(Migrate.Step):
    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        ''' Remove default session_data_manager and use beaker session data manager
        '''
        app = dmd.getPhysicalRoot()
        portal = app.zport
        sdmId = 'session_data_manager'
        for context in [app, portal]:
            if context.hasObject(sdmId):
                context._delObject(sdmId)

        from  Products.BeakerSessionDataManager.sessiondata import addBeakerSessionDataManager

        addBeakerSessionDataManager(app, sdmId, 'Beaker Session Data Manager')

BeakerSession()
