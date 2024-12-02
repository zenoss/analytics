##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """BaseReport

BaseReport is the base class for all viewable report devices

$Id: BaseReport.py, v.4.1.70 2012/06/12 10:08:56 smousa Exp $"""

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenMessaging.audit import audit

class BaseReport(ZenModelRM):

    def auditRunReport(self):
        # ZEN-1000: audit in case a poorly written report takes down the system
        audit('UI.Report.Run', self.getPrimaryId(), title=self.title)
