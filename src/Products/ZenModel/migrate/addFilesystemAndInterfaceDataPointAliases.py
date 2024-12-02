##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

def attachAliases( dmd, aliasMap ):
    for template in [ t.getObject() for t in dmd.searchRRDTemplates()]:
        for ds in template.datasources():
            for dp in ds.datapoints():
                if aliasMap.has_key( dp.id ):
                    if not dp.hasAlias( aliasMap[dp.id][0] ):
                        dp.addAlias( *aliasMap[dp.id] )


class AddFilesystemAndInterfaceDataPointAliases(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        attachAliases( dmd, 
          {'ifInOctets' : ('inputOctets__bytes',),
           'ifOutOctets' : ('outputOctets__bytes',),
           'ifHCInOctets' : ('inputOctets__bytes',),
           'ifHCOutOctets' : ('outputOctets__bytes',),
           'usedBlocks' : ('usedFilesystemSpace__bytes', 
                           '${here/blockSize},*')}
           )

            
AddFilesystemAndInterfaceDataPointAliases()
