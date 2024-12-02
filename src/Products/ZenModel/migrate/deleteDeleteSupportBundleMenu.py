##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Migrate


class DeleteDeleteSupportBundleMenu(Migrate.Step):
    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        # no-op if menu doesn't exist
        dmd.manage_deleteZenMenu('SupportBundleFiles_list')


DeleteDeleteSupportBundleMenu()

