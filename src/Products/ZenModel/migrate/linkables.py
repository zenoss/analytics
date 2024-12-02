##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add link relations to all IpInterfaces.
Create a LinkManager object on the dmd.

'''
import Migrate
from Products.ZenModel.LinkManager import manage_addLinkManager
from Products.ZenModel.Linkable import Linkable


class Linkability(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):

       # Create a LinkManager if one does not exist
        if not hasattr(dmd, 'ZenLinkManager'):
            manage_addLinkManager(dmd)

        # Build relations on all Linkable components
        for component in dmd.Devices.getSubComponents():
                if isinstance(component, Linkable):
                    component.buildRelations()

Linkability()
