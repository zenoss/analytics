##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Update the regexes on manufacturers so that a variety of different manufacturer
names all get mapped to the same manufacturer within Zenoss.

'''
import Migrate

manuRegexes = {
    'Apple': ('^Apple Computer',),
    'Broadcom': ('^Broadcom Corp$',),
    'Cisco': ('^ciscoSystems$',),
    'Dell': ('^Dell Inc\.$',),
    'F5 Networks': ('^F5 Networks Inc$',),
    'HP': ('Hewlett\-Packard',),
    'Intel': ('^Intel Corporation$',),
    'Microsoft': ('^Microsoft Corporation$',),
    'Net-SNMP': ('^net snmp$',),
    'Nortel': ('^Nortel Networks$',),
    'Sun': ('^Sun Microsystems',),
    'VMware': ('^VMware, Inc.$',),
    'WinZip': ('^WinZip Computing',),
    'XGI': ('^XGI Xabre Graphics Inc$',),
    }

class updateManufacturerRegexes(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        for mname, regexes in manuRegexes.items():
            m = dmd.Manufacturers.getManufacturer(mname)

            # Don't update manufacturers that already have regexes set.
            if m.regexes: continue

            m.regexes = regexes

updateManufacturerRegexes()
