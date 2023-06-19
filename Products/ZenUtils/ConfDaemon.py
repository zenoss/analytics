##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ConfDaemon

Base class for making daemon programs

$Id: ConfDaemon.py,v 1.9 2003/08/29 20:33:10 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

import signal
import os
import sys
import socket
import time

from CmdBase import CmdBase
from .path import zenPath

class ConfDaemon(CmdBase):
    
    def __init__(self):
        CmdBase.__init__(self)
        signal.signal(signal.SIGINT, self.sigTerm)
        signal.signal(signal.SIGTERM, self.sigTerm)
        if self.options.daemon and sys.platform != 'win32':
            self.becomeDaemon() 
        self.dnstries = 3
        self.forwarddnscache = {}
        self.reversednscache = {}

    def becomeDaemon(self):
        """fork twice to become a daemon"""
        pid = 0
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            print >>sys.stderr, ("fork #1 failed: %d (%s)" % 
                    (e.errno, e.strerror))
        os.chdir("/")
        os.setsid()
        os.umask(0)
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            print >>sys.stderr, ("fork #2 failed: %d (%s)" % 
                    (e.errno, e.strerror))
        myname = sys.argv[0].split(os.sep)[-1] + ".pid"
        varhome = zenPath('var')
        pidfile = os.path.join(varhome, myname)
        if os.path.exists(varhome):
            file = open(pidfile, 'w')
            file.write(str(os.getpid()))
            file.close()
        else:
            print "ERROR: unable to open pid file %s" % pidfile
            sys.exit(1) 


    def forwardDnsLookup(self, hostname):
        """try the forward lookup dnstries times if it fails look in cache"""
        try:
            ip = self._dnsLookup(socket.gethostbyname, hostname)
            self.forwarddnscache[hostname] = ip
            return ip
        except socket.error:
            if hostname in self.forwarddnscache:
                return self.forwarddnscache[hostname]
            else:
                raise


    def reverseDnsLookup(self, addr):
        """try the reverse lookup dnstries times if it fails look in cache"""
        try:
            ip = self._dsnLookup(socket.gethostbyaddr, addr)
            self.reversednscache[addr] = ip
            return ip
        except socket.error:
            if addr in self.reversednscache:
                return self.reversednscache[addr]
            else:
                raise


    def _dnsLookup(self, function, target):
        """try dns lookup dnstries times"""
        ip = None
        i=0
        while 1: 
            try:
                i+=1
                ip = function(target)
            except socket.error:
                if i > self.getDnsTries():
                    raise 
            if ip: break
        return ip
        

    def getDnsTries(self):
        if not hasattr(self, 'dnstries'):
            self.dnstries=3
        return self.dnstries

        
    def sigTerm(self, signum=None, frame=None):
        from Products.ZenUtils.Utils import unused
        unused(signum, frame)
        self.log.info('Daemon %s shutting down', self.__class__.__name__)
        sys.exit(0)



    def getConfig(self):
        """handle errors when loading config from server
        we try configtries times if no previous config is found"""
        for i in range(self.options.configtries):
            try:
                self.loadConfig()
                return
            except Exception:
                if self.validConfig():
                    self.log.exception(
                    "configuration load exception using previous configuration")
                    return
                else:
                    self.log.exception('config load failed')
                    if i <= (self.options.configtries - 2):
                        self.log.warn(
                            "initial config load failed will retry")
                        time.sleep(self.options.configsleep)
                    else:
                        self.log.critical(
                            "initial config load failed %d times exiting",
                            self.options.configtries)
                        sys.exit(2)


    def buildOptions(self):
        CmdBase.buildOptions(self)
        self.parser.add_option('-c', '--cycle',
                    dest='cycle',
                    default=0,
                    action="store_true",
                    help="Cycle continuously on cycleInterval from zope")
        self.parser.add_option('-d', '--daemon',
                    dest='daemon',
                    default=0,
                    action="store_true",
                    help="Become a unix daemon")
        self.parser.add_option('-T', '--configtries',
                    dest='configtries',
                    default=5,
                    type='int',
                    action="store",
                    help="How many times to retry config connection")
        self.parser.add_option('-S', '--configsleep',
                    dest='configsleep',
                    default=20,
                    type='int',
                    action="store",
                    help="How long to sleep between config connections")
