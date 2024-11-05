##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = "Convert old-style zenpacks to zenpack eggs"

from Pruducts.ZenUtils.path import zenPath
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenModel.ZenPack import ZenPackException
import ZenPackCmd
import os, sys
import shutil


class Eggify(ZenScriptBase):
    "Eggify ZenPacks"

    def run(self):
        if not self.options.newid:
            raise ZenPackException('You must specify a new id with the'
                ' --newid option.')
        zpName = self.args[0]
        if not os.path.isdir(zenPath('Products', zpName)):
            raise ZenPackException('Can not locate %s.' % zpName +
                ' This command only operates on installed ZenPacks.')
        (possible, msgOrId) = ZenPackCmd.CanCreateZenPack(
                                                    None, self.options.newid)
        if possible:
            newId = msgOrId
        else:
            raise ZenPackException('Unable to eggify %s: %s' % (
                                                            zpName, msgOrId))                        
        
        self.connect()
        
        # Create new zenpack
        eggDir = ZenPackCmd.CreateZenPack(newId, prevZenPackName=zpName)
        
        # Copy old one into new one
        parts = newId.split('.')
        zpDir = os.path.join(eggDir, *parts)
        os.system('rm -rf %s' % zpDir)
        shutil.copytree(zenPath('Products', zpName), zpDir, symlinks=False)
        
        # Create a skins directory if there isn't one
        skinsDir = os.path.join(zpDir, 'skins', zpName)
        if not os.path.isdir(skinsDir):
            os.makedirs(skinsDir)
        
        # Install it
        ZenPackCmd.InstallEggAndZenPack(self.dmd, eggDir, link=True)

        # Confirm pack is eggified
        pack = self.dmd.ZenPackManager.packs._getOb(zpName, None)
        success = pack and pack.isEggPack()

        if success:
            print('%s successfully converted to %s.' % (zpName, newId))
            print('The code for %s is located at $ZENHOME/ZenPacks/%s' %
                    (newId, newId))
            print('NOTE: If your ZenPack provides DataSource classes '
                    'or any other python class for objects that are stored '
                    'in the object database then further steps are '
                    'required.  Please see the Zenoss Developer Guide for '
                    'more instructions.')        

    def buildOptions(self):
        self.parser.add_option('--newid',
                               dest='newid',
                               default=None,
                               help='Specify a new name for this ZenPack. '
                                'It must contain at least three package names '
                                'separated by periods, the first one being '
                                '"ZenPacks"')
        ZenScriptBase.buildOptions(self)


if __name__ == '__main__':
    e = Eggify()
    try:
        e.run()
    except ZenPackException as e:
        import sys
        sys.stderr.write('%s\n' % str(e))
        sys.exit(-1)
