#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

""" ZenTestCommand

Test the run of a ZenCommand and print output
"""

import logging
import sys

from copy import copy

from Products.ZenUtils.Utils import executeStreamCommand, executeSshCommand
from Products.ZenUtils.ZenScriptBase import ZenScriptBase

log = logging.getLogger("zen.zentestcommand")
snmptemplate = (
    "snmpwalk -c%(zSnmpCommunity)s " "-%(zSnmpVer)s %(manageIp)s %(oid)s"
)


class TestRunner(ZenScriptBase):
    def __init__(self):
        ZenScriptBase.__init__(self, connect=True)
        self.getDataRoot()
        self.device = None
        self.usessh = False

    def getCommand(self, devName=None, dsName=None):
        if not devName:
            devName = self.options.devName
        if not dsName:
            dsName = self.options.dsName
        devices = self.dmd.getDmdRoot("Devices")
        self.device = devices.findDevice(devName)
        if not self.device:
            self.write("Could not find device %s." % devName)
            sys.exit(1)
        dataSource = None
        for templ in self.device.getRRDTemplates():
            for ds in templ.getRRDDataSources():
                if ds.id == dsName:
                    dataSource = ds
                    break
                if dataSource:
                    break
        if not dataSource:
            self.write(
                "No datasource %s applies to device %s." % (dsName, devName)
            )
            sys.exit(1)
        if dataSource.sourcetype == "COMMAND":
            self.usessh = dataSource.usessh
            return dataSource.getCommand(self.device)
        elif dataSource.sourcetype == "SNMP":
            snmpinfo = copy(self.device.getSnmpConnInfo().__dict__)
            snmpinfo["oid"] = dataSource.getDescription()
            return snmptemplate % snmpinfo
        else:
            self.write(
                "No COMMAND or SNMP datasource %s applies to device %s."
                % (dsName, devName)
            )

    def write(self, text):
        print(text)

    def run(self):
        device, dsName = self.options.device, self.options.dsName
        if not (device and dsName):
            self.write("Must provide a device and datasource.")
            sys.exit(2)
        cmd = self.getCommand(device, dsName)
        if self.usessh:
            executeSshCommand(device, cmd, self.write)
        else:
            executeStreamCommand(cmd, self.write)

    def buildOptions(self):
        ZenScriptBase.buildOptions(self)
        self.parser.add_option(
            "-d",
            "--device",
            dest="device",
            help="Device on which to test command",
        )
        self.parser.add_option(
            "--datasource", dest="dsName", help="COMMAND datasource to test"
        )
        self.parser.add_option(
            "-t",
            "--timeout",
            dest="timeout",
            default=1,
            type="int",
            help="Command timeout",
        )


if __name__ == "__main__":
    tr = TestRunner()
    tr.run()
