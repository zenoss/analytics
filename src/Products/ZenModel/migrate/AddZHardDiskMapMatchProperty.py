############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.migrate")

def _getSshLinux(dmd):
    try:
        return dmd.Devices.Server.aq_explicit.SSH.aq_explicit.Linux
    except AttributeError:
        return None

HARD_DISK_MAP_MATCH_PROPERTY = 'zHardDiskMapMatch'

import Migrate

class AddZHardDiskMapMatchProperty(Migrate.Step):
    """
    The property zHardDiskMapMatch is defined on /Devices/Server/Linux, 
    but it needs to be copied to /Devices/Server/SSH/Linux
    """

    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):
        try:
            log.debug('Adding %s property to /Devices/Server/SSH/Linux if necessary', HARD_DISK_MAP_MATCH_PROPERTY)
            sshLinux = _getSshLinux(dmd)
            if sshLinux:
                if not sshLinux.getProperty(HARD_DISK_MAP_MATCH_PROPERTY):
                    hdRegex = dmd.Devices.Server.Linux.getProperty(HARD_DISK_MAP_MATCH_PROPERTY)
                    sshLinux.setZenProperty(HARD_DISK_MAP_MATCH_PROPERTY, hdRegex)
        except Exception as e:
            log.warn('Exception trying to add %s property to /Devices/Server/SSH/Linux: %s', HARD_DISK_MAP_MATCH_PROPERTY, e)

AddZHardDiskMapMatchProperty()
