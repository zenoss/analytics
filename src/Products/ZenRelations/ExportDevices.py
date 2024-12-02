##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

__doc__ = """ExportDevices
Export devices from /zport/dmd/Devices inside the Zope database
"""

import datetime
import re
import StringIO
import sys

from xml.dom.minidom import parseString

from Products.ZenUtils.ZCmdBase import ZCmdBase

# Blank line regular expression
_newlines = re.compile("\n[\t \r]*\n", re.M)


# TODO: ZEN-2505 May want to remove this class
class ExportDevices(ZCmdBase):
    """
    Wrapper class around exportXml() to create XML exports of devices.
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
            help="Relations that should be ignored.  Every relation to"
            + " ignore must be specified with a separate --ignorerels option.",
        )

    def strip_out_zenoss_internals(self, doc):
        """
        Remove Zenoss internal-use objects that we don't need for an import.
        doc is our XML document tree.

        @param doc: XML tree
        @type doc: XML DOM document
        @return: XML output
        @rtype: string
        """

        _retain_class = (
            "Products.ZenModel.DeviceClass",
            "Products.ZenModel.Device",
        )

        _retain_props = (
            "description",
            "productionState",
            "priority",
            "monitors",
        )

        def denewline(s):
            """
            Remove blank lines and standardize on Unix-style newlines.

            @param s: XML output
            @type s: string
            @return: XML output
            @rtype: string
            """
            while re.search(_newlines, s):
                s = re.sub(_newlines, "\n", s)
            return s

        def clearObjects(node):
            """
            Remove devices from the export list

            @param node: XML tree
            @type node: XML DOM object
            """

            def keepDevice(elem):
                """
                Look for objects that we should be exporting...

                @param elem: XML element
                @type elem: XML DOM object
                @return: should the element be kept in the resulting output?
                @rtype: boolean
                """
                try:
                    return not elem.getAttribute("module") in _retain_class
                except Exception:
                    return True

            try:
                elems = node.getElementsByTagName("object")
            except AttributeError:
                pass
            else:
                elems = filter(keepDevice, elems)
                [elem.parentNode.removeChild(elem) for elem in elems]

        def clearProps(node):
            """
            Remove any properties that shouldn't be exported

            @param node: XML tree
            @type node: XML DOM object
            """
            try:
                props = node.getElementsByTagName("property")
            except AttributeError:
                pass
            else:
                for prop in props:
                    if prop.getAttribute("module") not in _retain_props:
                        prop.parentNode.removeChild(prop)

        # From our XML document root, do any last-minute cleanup
        # before exporting.
        root = doc.getElementsByTagName("objects")[0]
        clearObjects(root)
        clearProps(root)

        # Standardize the output of the standard XML pretty printer
        return denewline(doc.toprettyxml().replace("\t", " " * 4))

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

    def export(self):
        """
        Create XML header and then call exportXml() for all objects
        starting at root.
        """

        root = self.dmd.Devices
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
        buffer = StringIO.StringIO()
        buffer.write(
            """<?xml version="1.0" encoding="ISO-8859-1" ?>

<!--
    Zenoss Device export completed on %s

    Use ImportDevices to import this file.

    For more information about Zenoss, go to http://www.zenoss.com
 -->

<objects version="%s" export_date="%s" zenoss_server="%s" >\n"""
            % (export_date, version, export_date, server)
        )

        # Pass off all the hard work to the objects
        root.exportXml(buffer, self.options.ignorerels, True)

        # Write the ending tag
        buffer.write("</objects>\n")

        # Create an XML document tree that we clean up and then export
        doc = parseString(buffer.getvalue())
        finalxml = self.strip_out_zenoss_internals(doc)

        # Actually write out the file
        self.outfile.write(finalxml)
        self.outfile.close()

        # Clean up our StringIO object
        buffer.close()
        doc.unlink()


if __name__ == "__main__":
    ex = ExportDevices()
    ex.export()
