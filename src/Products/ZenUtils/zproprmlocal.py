##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Remove local value of zProperty from Devices"""

from __future__ import absolute_import, print_function

import sys

import transaction

from Acquisition import aq_base

from .ZCmdBase import ZCmdBase


class ZPropRmLocal(ZCmdBase):
    """Remove local value of zProperty from Devices"""

    def run(self):
        msg = []

        if not self.options.deviceClass:
            msg.append(
                "You must specify a device class with the" " --class option."
            )

        if not self.options.zPropName:
            msg.append(
                "You must specify a zProperty name with the"
                " --zproperty option."
            )

        if msg:
            print("\n".join(msg))
            sys.exit(0)

        try:
            devClass = self.dmd.Devices.getOrganizer(self.options.deviceClass)
        except KeyError:
            print(
                "Unable to locate device class %s" % self.options.deviceClass
            )
            sys.exit(0)

        devs = []
        if self.options.recurse:
            devList = devClass.getSubDevicesGen()
        else:
            devList = devClass.devices()
        for dev in devList:
            if hasattr(aq_base(dev), self.options.zPropName):
                dev._delProperty(self.options.zPropName)
                devs.append(dev)

        transaction.commit()

        print(
            "Deleted %s from %s devices." % (self.options.zPropName, len(devs))
        )
        for d in devs:
            sys.stdout.write(d.getPrimaryId())

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option(
            "--class",
            dest="deviceClass",
            default="/",
            help="Device class to operate on",
        )
        self.parser.add_option(
            "--zproperty",
            dest="zPropName",
            default=None,
            help="Name of the zProperty to remove from" " devices",
        )
        self.parser.add_option(
            "-r",
            "--recurse",
            dest="recurse",
            action="store_true",
            default=False,
            help="Recurse into subclasses of --class",
        )


def main():
    ZPropRmLocal().run()
