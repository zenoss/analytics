##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = 'add the ReportServer to existing systems'

__version__ = "$Revision$"[11:-2]

import Migrate

class ReportServer(Migrate.Step):
    version = Migrate.Version(1, 1, 0)
    
    def cutover(self, dmd):
        from Products.ZenReports.ReportServer import manage_addReportServer
        portal = dmd.getPhysicalRoot().zport
        id = 'ReportServer'
        if not hasattr(portal, id):
            manage_addReportServer(portal, id)

ReportServer()
