##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''smtpsnpp

Add settings for smtp/snpp host/port to dmd

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

class smtpsnpp(Migrate.Step):
    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        options = OptionsBucket()
        options.configfile = zenPath('etc', 'zenactions.conf')
        parseconfig(options)
        if not hasattr(dmd, 'smtpHost'):
            dmd.smtpHost = getattr(options, 'smtphost', '') or 'localhost'
        if not hasattr(dmd, 'smtpPort'):
            try:
                dmd.smtpPort = int(getattr(options, 'smtpport', ''))
            except ValueError:
                dmd.smtpPort = 25
        if not hasattr(dmd, 'snppHost'):
            dmd.snppHost = getattr(options, 'snpphost', '') or 'localhost'
        if not hasattr(dmd, 'snppPort'):
            try:
                dmd.snppPort = int(getattr(options, 'snppport', ''))
            except ValueError:
                dmd.snppPort = 444

smtpsnpp()
