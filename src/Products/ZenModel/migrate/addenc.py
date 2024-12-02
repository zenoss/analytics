##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
import logging
log = logging.getLogger('zen.migrate')

class AddressEncoding(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        for loc in dmd.Locations.getSubOrganizers():
            try:
                loc.address.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    loc.address = loc.address.decode('latin-1').encode('utf-8')
                except Exception:
                    log.error("Unable to decode address '%s'" % loc.address + \
                              " on location %s" % loc.id)
        dmd.geocache = ''

AddressEncoding()
