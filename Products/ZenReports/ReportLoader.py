##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import sys

import transaction

from Products.ZenModel.Report import Report
from Products.ZenUtils.path import zenPath
from Products.ZenUtils.ZCmdBase import ZCmdBase


class ReportLoader(ZCmdBase):
    """Load Zope reports into the ZODB."""

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option(
            "-f",
            "--force",
            dest="force",
            action="store_true",
            default=0,
            help="Load all reports, overwriting any existing reports.",
        )
        self.parser.add_option(
            "-d",
            "--dir",
            dest="dir",
            default="reports",
            help="Directory from which to load reports: default '%default'",
        )
        self.parser.add_option(
            "-p",
            "--zenpack",
            dest="zenpack",
            default="",
            help="ZenPack from which to load reports",
        )

    # FIXME: This call is deprecated, look for all instances of this
    def loadDatabase(self):
        self.loadAllReports()

    def loadAllReports(self):
        """
        Load reports from the directories into the ZODB
        """
        repdirs = [zenPath("Products/ZenReports", self.options.dir)]
        if self.options.zenpack:
            repdirs = self.getZenPackDirs(self.options.zenpack)

        for repdir in repdirs:
            if os.path.isdir(repdir):
                self.loadDirectory(repdir)
                transaction.commit()

    def getZenPackDirs(self, name):
        matches = []
        for zp in self.dmd.ZenPackManager.packs():
            if re.search(name, zp.id):
                path = os.path.join(zp.path(), self.options.dir)
                matches.append(path)

        if not matches:
            self.log.error(
                "No ZenPack named '%s' was found -- exiting",
                self.options.zenpack,
            )
            sys.exit(1)
        return matches

    def reports(self, directory):
        def normalize(f):
            return f.replace("_", " ")

        def toOrg(path):
            path = normalize(path).split("/")
            path = path[path.index("reports") + 1 :]
            return "/" + "/".join(path)

        return [
            (toOrg(p), normalize(f[:-4]), os.path.join(p, f))
            for p, ds, fs in os.walk(directory)
            for f in fs
            if f.endswith(".rpt")
        ]

    def unloadDirectory(self, repdir):
        self.log.info("Removing reports from %s", repdir)
        reproot = self.dmd.Reports
        for orgpath, fid, fullname in self.reports(repdir):
            rorg = reproot.createOrganizer(orgpath)
            if getattr(rorg, fid, False):
                rorg._delObject(fid)
            while rorg.id != "Reports":
                if not rorg.objectValues():
                    id = rorg.id
                    rorg = rorg.getPrimaryParent()
                    rorg._delObject(id)

    def loadDirectory(self, repdir):
        self.log.info("Loading reports from %s", repdir)
        reproot = self.dmd.Reports
        for orgpath, fid, fullname in self.reports(repdir):
            rorg = reproot.createOrganizer(orgpath)
            if getattr(rorg, fid, False):
                # Do not rewrite reports that were changed by zenpack
                if self.options.force and not getattr(rorg, fid).pack():
                    rorg._delObject(fid)
                else:
                    continue
            self.log.info("loading: %s/%s", orgpath, fid)
            self.loadFile(rorg, fid, fullname)

    def loadFile(self, root, id, fullname):
        fdata = file(fullname).read()
        rpt = Report(id, text=fdata)
        root._setObject(id, rpt)
        return rpt


if __name__ == "__main__":
    rl = ReportLoader()
    rl.loadAllReports()
