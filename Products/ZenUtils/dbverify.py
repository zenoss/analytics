#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys
from optparse import OptionParser
import subprocess
import re
from Products.ZenUtils.path import zenPath

class Main(object):

    def verify(self, component, expected_version):
        
        s = None
        # connect to out db client abstraction
        zendb = zenPath("Products", "ZenUtils", "ZenDB.py")
        s = subprocess.Popen([zendb, "--usedb", component, "--execsql", "SELECT VERSION();"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
            
        stdout, stderr = s.communicate()
        if s.returncode != 0:
           print >> sys.stderr, "Error executing db cmdline client: %s %s " % (stdout, stderr,)
           sys.exit(1)
        match = re.compile("\d+(\.\d+){1,2}").search(stdout)
        if match is None:
           print >> sys.stderr, "Could not extract version info from database connection."

        server_version = match.group()
 
        e_ver = tuple(int(v) for v in expected_version.split('.'))
        s_ver = tuple(int(v) for v in server_version.split('.'))
        if s_ver < e_ver:
            print >> sys.stderr, "Server version: %s < Expected version: %s" % (
                server_version, expected_version)

if __name__=="__main__":
    
    usage = "Usage: %prog [zodb|zep] [version]"
    epilog = "Verifies connectivity with the db server for zodb or zep configued in global.conf."
    parser = OptionParser(usage=usage, epilog=epilog)
    (options, args) = parser.parse_args()

    if len(args) != 2:
        parser.print_usage()
        sys.exit(1)

    component = args[0]
    if component not in ('zodb', 'zep'):
        print >> sys.stderr, "Invalid component given."
        parser.print_usage()
        sys.exit(1)

    main = Main()
    main.verify(component, args[1])
