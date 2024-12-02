##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import transaction

from Products.ZenReports import Utils


class swinventory:
    def run(self, dmd, args):
        report = []
        # ZEN-30539
        if args.get("adapt", ""):
            return report
        recordCount = 0
        for m in dmd.Manufacturers.objectValues():
            if m.id == "Unknown" or m.meta_type != "Manufacturer":
                continue
            for p in m.products.objectValues():
                if p.meta_type == "SoftwareClass":
                    c = 0
                    for i in p.instances():
                        try:
                            if dmd.checkRemotePerm("View", i.device()):
                                c += 1
                        except Exception:
                            continue
                        i._p_invalidate()
                    if c == 0:
                        continue
                    report.append(
                        Utils.Record(
                            manufLink=m.getIdLink(),
                            manufId=m.id,
                            softLink=p.getIdLink(),
                            softId=p.id,
                            count=c,
                        )
                    )
                p._p_invalidate()
            m._p_invalidate()
            recordCount += 1
            if recordCount % 100 == 0:
                transaction.abort()
        return report
