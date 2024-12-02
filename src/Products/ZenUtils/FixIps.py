##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenUtils.Utils import getSubObjects

from Products.ZenUtils.ZCmdBase import ZCmdBase
from transaction import get_transaction

class FixIps(ZCmdBase):

    def fixips(self):
        ips = getSubObjects(self.dmd, self.filter, self.decend)
        self.ccount = 0
        for ip in ips:
            self.log.debug("fixing ip %s", ip.id)
            int = ip.interface()
            if int:
                ip.removeRelation("interface")
                ip.addRelation("interface", int)
                self.ccount += 1
                if (self.ccount >= self.options.commitCount 
                    and not self.options.noCommit):
                    self.mycommit(ip)
        if self.options.noCommit:
            self.log.info("not commiting any changes")
        else:
            self.mycommit()


    def filter(self, obj):
        return obj.meta_type == "IpAddress"


    def decend(self, obj):
        return (obj.meta_type == "IpNetwork" or 
            (obj.meta_type == "To Many Relationship" and 
                (obj.id == "subnetworks" or obj.id == "ipaddresses")))


    def mycommit(self, ip=None):
        if not ip:
            ipname = "all"
        else:
            ipname = ip.id
        self.log.info('commiting group of ips ending with %s', ipname)
        trans = get_transaction()
        trans.note('FixIps reconnect ips')
        trans.commit()
        self.ccount = 0

    
    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-x', '--commitCount',
                    dest='commitCount',
                    default=20,
                    type="int",
                    help='how many lines should be loaded before commit')

        self.parser.add_option('-n', '--noCommit',
                    dest='noCommit',
                    action="store_true",
                    default=0,
                    help='Do not store changes to the Dmd (for debugging)')


if __name__ == "__main__":
    fips = FixIps()
    fips.fixips()
