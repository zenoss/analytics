##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ExportRM

Export RelationshipManager objects from a Zope database
"""

from __future__ import print_function

import datetime
import sys

from Products.ZenUtils.ZCmdBase import ZCmdBase


class ExportRM(ZCmdBase):
    """
    Wrapper class around exportXml() to create XML exports of relations.
    """

    def __init__(self):
        """
        Initializer that creates an output file, or if nothing is specified
        with the command-line option --outfile, sends to stdout.
        """
        ZCmdBase.__init__(self)
        if not self.options.outfile:
            self.outfile = sys.stdout
        else:
            self.outfile = open(self.options.outfile, "w")

    def buildOptions(self):
        """
        Command-line options setup
        """
        ZCmdBase.buildOptions(self)

        self.parser.add_option(
            "-o",
            "--outfile",
            dest="outfile",
            help="Output file for exporting XML objects. Default is stdout",
        )

        self.parser.add_option(
            "--ignore",
            action="append",
            dest="ignorerels",
            default=[],
            help="Relations that should be ignored.  Every relation to "
            "ignore must be specified with a separate --ignorerels option.",
        )

    def getVersion(self):
        """
        Gather our current version information

        @return: Zenoss version information
        @rtype: string
        """
        from Products.ZenModel.ZenossInfo import ZenossInfo

        zinfo = ZenossInfo("")
        return str(zinfo.getZenossVersion())

    def getServerName(self):
        """
        Gather our Zenoss server name

        @return: Zenoss server name
        @rtype: string
        """
        import socket

        return socket.gethostname()

    def export(self, root=None):
        """
        Create XML header and then call exportXml() for all objects
        starting at root.

        @param root: DMD object root
        @type root: object
        """

        if not root:
            root = self.dataroot

        if not hasattr(root, "exportXml"):
            print(
                "ERROR: Root object for %s is not exportable "
                "(exportXml not found)" % root
            )
            sys.exit(1)

        export_date = datetime.datetime.now()
        version = self.getVersion()
        server = self.getServerName()

        # TODO: When the DTD gets created, add the reference here
        self.outfile.write(
            """<?xml version="1.0" encoding="ISO-8859-1" ?>

<!--
    Zenoss RelationshipManager export completed on %s

    Use ImportRM to import this file.

    For more information about Zenoss, go to http://www.zenoss.com
 -->

<objects version="%s" export_date="%s" zenoss_server="%s" >\n"""
            % (export_date, version, export_date, server)
        )

        # Pass off all the hard work to the objects
        root.exportXml(self.outfile, self.options.ignorerels, True)

        # Write the ending element
        self.outfile.write("</objects>\n")


def main():
    ExportRM().export()
