##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Migrate


"""
Add global cycle time zProp for 'COMMAND' type datasources,
migrate existing datasources which we have in core to use it.
"""


class AddzCommandCollectionInterval(Migrate.Step):
    version = Migrate.Version(200, 2, 0)

    
    def cutover(self, dmd):
        
        cycletime = '${here/zCommandCollectionInterval}'
        if not hasattr(dmd.Devices, 'zCommandCollectionInterval'):
            dmd.Devices._setProperty('zCommandCollectionInterval', 300, 'int')


            for template in [ t.getObject() for t in dmd.searchRRDTemplates()]:
                for ds in template.datasources():
                    if 'COMMAND' in ds.sourcetype and not ds.pack():
                        ds.cycletime = cycletime
           
                  
AddzCommandCollectionInterval()
