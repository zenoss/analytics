##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

"""ServiceTester

Simple utility class for testing out zenhub services.
Sample usage (at the bottom of a service):

if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(PingPerformanceConfig)
    def printer(config):
        for ip in config.monitoredIps:
            print '\t', ip
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()

Note that the service instance can be found as an attribute
on the tester object.

ie tester.service == PingPerformanceConfig(dmd, 'localhost')
"""

import logging

from pprint import pprint

from Products.ZenUtils.Utils import setLogLevel
from Products.ZenUtils.ZCmdBase import ZCmdBase

log = logging.getLogger("zen.ServiceTester")


class ServiceTester(ZCmdBase):
    doesLogging = False

    def __init__(self, Klass):
        ZCmdBase.__init__(self, False, False, False)
        # It's super annoying to try to figure out how to get the
        # zenhub service to drop into debug mode.  Use the following.
        setLogLevel(logging.DEBUG)
        logging.basicConfig()
        self.service = Klass(self.dmd, self.options.monitor)

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option(
            "--monitor",
            "--collector",
            dest="monitor",
            default="localhost",
            help="Specify the collector to collect against.",
        )
        self.parser.add_option(
            "-d",
            "--device",
            dest="device",
            help="Show the configs for a single device",
        )

    def pprint(self, arg):
        pprint(arg)

    def showDeviceInfo(self):
        if self.options.device:
            name = self.options.device
            config = self.service.remote_getDeviceConfigs([name])
            if config:
                print("Config for %s =" % name)
                self.printDeviceProxy(config[0])
            else:
                log.warn("No configs found for %s", name)
        else:
            devices = sorted(
                x.id for x in self.service.remote_getDeviceConfigs()
            )
            print("Device list = %s" % devices)

    def printDeviceProxy(self, proxy):
        """
        Device proxies don't report their interal state very well. This
        should be overwritten by the zenhub service writer.
        """
        pprint(proxy)
