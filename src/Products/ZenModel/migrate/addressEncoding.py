##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zLinks to DeviceClass.

'''
import Migrate

class UpdateAddressEncoding(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        for loc in dmd.Locations.getSubOrganizers():
            try:
                loc.address.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    loc.address = loc.address.decode('latin-1').encode('utf-8')
                except UnicodeDecodeError as UnicodeEncodeError:
                    pass

UpdateAddressEncoding()
