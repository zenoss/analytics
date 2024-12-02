##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add a default zFileSystemMapIgnoreTypes property to key device classes now that
the HRFileSystemMap uses it.

'''
import Migrate

class addDefaultZFileSystemMapIgnoreTypes(Migrate.Step):
    version = Migrate.Version(2, 4, 0)
    
    def cutover(self, dmd):
        if not dmd.Devices.zFileSystemMapIgnoreTypes:
            dmd.Devices.zFileSystemMapIgnoreTypes = [
                'other', 'ram', 'virtualMemory', 'removableDisk', 'floppyDisk',
                'compactDisk', 'ramDisk', 'flashMemory', 'networkDisk']

        try:
            if not dmd.Devices.Server.Windows.WMI.hasProperty(
                'zFileSystemMapIgnoreTypes'):
                dmd.Devices.Server.Windows.WMI._setProperty(
                    'zFileSystemMapIgnoreTypes', [])
        except AttributeError:
            pass

addDefaultZFileSystemMapIgnoreTypes()
