##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ ='''IpServiceLoader

A script to load the IANA well known port numbers.

$Id: IpServiceLoader.py,v 1.5 2004/04/15 23:47:50 edahl Exp $'''

__version__ = "$Revision: 1.5 $"[11:-2]

import os
import re


from Products.ZenUtils.BasicLoader import BasicLoader

from Products.ZenModel.IpService import getIpServiceKey
from Products.ZenModel.IpServiceClass import IpServiceClass

class IpServiceLoader(BasicLoader):

    lineparse = re.compile(r"^(\S+)\s+(\d+)/(\S+)(.*)")
        
    
    def __init__(self, noopts=0, app=None):
        self.filename = os.path.join(os.path.dirname(__file__), 
                            "port-numbers.txt")
        BasicLoader.__init__(self, noopts, app, ignoreComments=False)
        services = self.dmd.getDmdRoot('Services')
        self.privserv = services.createOrganizer("/IpService/Privileged")
        self.regserv = services.createOrganizer("/IpService/Registered")
        self.lastservice = None


    def loaderBody(self, line):
        if line.startswith("#"): return
        m = self.lineparse.search(line)
        if not m: return
        keyword, port, proto, descr = m.groups()
        descr = descr.strip()
        port = int(port)
        svc = self.privserv.find(keyword)
        portkey = getIpServiceKey(proto, port)
        if not svc:
            serviceKeys = (keyword, portkey)
            svc = IpServiceClass(keyword, serviceKeys=serviceKeys,
                               description=descr, port=port)
            if port < 1024:
                self.privserv.serviceclasses._setObject(svc.id, svc)
            else:
                self.regserv.serviceclasses._setObject(svc.id, svc)
            self.log.info("Added IpServiceClass %s", keyword)
        else:
            svc.addServiceKey(portkey)


if __name__ == "__main__":
    loader = IpServiceLoader()
    loader.loadDatabase()
    print "Database Load is finished!"
