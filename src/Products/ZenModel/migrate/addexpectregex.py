##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Set expectRegex property for IpService objects that need it

'''
import Migrate

class AddExpectRegex(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        regexmap = {
            'tcp_00025' : r'220',
            'tcp_00110' : r'\+OK',
            'tcp_00587' : r'220',
            'tcp_00022' : r'SSH',
            'tcp_00143' : r'OK',
        }            

        for id in regexmap.keys():
            svc = dmd.Services.IpService.find(id)
            if svc:
                svc.expectRegex = regexmap[id]

AddExpectRegex()
