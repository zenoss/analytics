############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

__doc__ = """
See ZEN-2690 Generate an error level event when a zenoss process fails.
"""
import logging
import Migrate
from Products.ZenEvents.ZenEventClasses import Debug, Error
log = logging.getLogger("zen.migrate")


class ZenossProcessClasszFailSeverity(Migrate.Step):    

    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):
        try:
            processOrganizer = dmd.Processes.Zenoss
            if processOrganizer.zFailSeverity == Debug:
                processOrganizer.setZenProperty('zFailSeverity', Error)
        except AttributeError:
            log.warn('Unable to set zFailSeverity on /zport/dmd/Processes/Zenoss')

            
ZenossProcessClasszFailSeverity()
