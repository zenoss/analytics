##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""
Changes all of the ToManyRelationships to be persistent lists instead of
regular python lists.
This results in performance improvements when accessing the objects
"""

import Migrate

class ToManyPersistentList(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        root = dmd.Services
        # migrate services
        for org in root.getSubOrganizers():
            for svcclass in org.serviceclasses():
                svcclass.instances.convertToPersistentList()

        # device organizers
        for root in (dmd.Groups, dmd.Systems, dmd.Locations):
            for org in root.getSubOrganizers():
                org.devices.convertToPersistentList()

ToManyPersistentList()
