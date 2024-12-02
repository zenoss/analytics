##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from zope.interface import Interface

class IDaemonConfig(Interface):
    def getConfig():
        """Return a zeneventd.conf"""
