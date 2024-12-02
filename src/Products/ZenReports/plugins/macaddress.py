##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenReports.Utils import Record


class macaddress(object):
    ignoreInterfaces = ["lo", "sit0"]

    def run(self, dmd, args):
        report = []
        # ZEN-30539
        if args.get("adapt", ""):
            return report
        catalog = dmd.ZenLinkManager.layer2_catalog
        for brain in catalog():
            if brain.macaddress is None:  # Bad catalog
                continue
            macaddress = brain.macaddress.upper()
            if not macaddress or macaddress == "00:00:00:00":
                continue
            ifaceName = brain.interfaceId.rsplit("/", 1)[-1]
            if ifaceName in self.ignoreInterfaces:
                continue
            deviceName = brain.deviceId.rsplit("/", 1)[-1]
            report.append(
                Record(
                    devicePath=brain.deviceId,
                    deviceName=deviceName,
                    interfacePath=brain.interfaceId,
                    interfaceName=ifaceName,
                    macaddress=brain.macaddress,
                )
            )
        return report
