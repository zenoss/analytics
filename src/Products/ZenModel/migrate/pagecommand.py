##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''pagecommand

Add settings for pageCommand to dmd
Remove settings for snpp from dmd

'''
import Migrate
import os.path
import sys

def parseconfig(options):
    """parse a config file which has key value pairs delimited by white space"""
    if not os.path.exists(options.configfile):
        print >>sys.stderr, "WARN: config file %s not found skipping" % (
                            options.configfile)
        return
    lines = open(options.configfile).readlines()
    for line in lines:
        if line.lstrip().startswith('#'): continue
        if line.strip() == '': continue
        key, value = line.split(None, 1)
        value = value.rstrip('\r\n')
        key = key.lower()
        defval = getattr(options, key, None)
        if defval: value = type(defval)(value)
        setattr(options, key, value)


class OptionsBucket:
    pass

from Products.ZenUtils.Utils import zenPath

class pagecommand(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        options = OptionsBucket()
        options.configfile = zenPath('etc', 'zenactions.conf')
        parseconfig(options)
        if hasattr(dmd, 'snppHost'):
            del dmd.snppHost
        if hasattr(dmd, 'snppPort'):
            del dmd.snppPort
        if not hasattr(dmd, 'pageCommand'):
            dmd.pageCommand = getattr(options, 'pagecommand', '') or '$ZENHOME/bin/zensnpp localhost 444 $RECIPIENT'

pagecommand()
