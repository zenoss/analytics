##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os
import shutil
import sys

from Products.ZenRelations.utils import importClasses
from Products.ZenUtils.path import zenPath

logging.basicConfig()
root = logging.getLogger()
root.setLevel(logging.CRITICAL)


class HtmlGenerator(object):
    def __init__(self, baseModule, classList, outdir="docs"):
        self.outdir = outdir
        self.baseModule = baseModule
        self.classList = classList
        self._classnames = {}

    def generate(self):
        """Generate all html docs for the classList we were given."""
        for cls in self.classList:
            self.genHtml(cls)
        self.genIndexHtml()

    def genIndexHtml(self):
        """
        Generate our index file must be called after all classes are processed.
        """
        self.of = open(os.path.join(self.outdir, "index.html"), "w")
        self.writeHeader()
        keys = sorted(self._classnames.keys())
        self.writeTableHeader("Classes", ("ClassName",))
        for clsname in keys:
            filepath = self._classnames[clsname]
            self.of.write("""<tr class="tablevalues">""")
            self.td("""<a href="%s">%s</a>""" % (filepath, clsname))
        self.of.write("</table>")
        self.writeFooter()
        self.of.close()

    def genHtml(self, cls):
        """Generate html documentaion for a class's schema."""
        logging.info("generating doc for class %s...", cls.__name__)
        filename = self.getFileName(cls)
        self._classnames[cls.__name__] = self.getHref(cls)
        self.of = open(filename, "w")
        self.writeHeader()
        self.genPropertiesTable(cls)
        self.genRelationsTable(cls)
        self.writeFooter()
        self.of.close()

    def genPropertiesTable(self, cls):
        props = getattr(cls, "_properties", False)
        if not props:
            return
        self.writeTableHeader("Properties", ("name", "type", "mode", "setter"))
        for prop in props:
            self.of.write("""<tr class="tablevalues">""")
            for key in ("id", "type", "mode", "setter"):
                self.of.write("""<td>%s</td>""" % prop.get(key, ""))
            self.of.write("</tr>")
        self.of.write("</table>")

    def genRelationsTable(self, cls):
        rels = getattr(cls, "_relations", False)
        if not rels:
            return
        self.writeTableHeader(
            "Relations",
            (
                "Local Name",
                "Local Type",
                "Remote Type",
                "Remote Class",
                "Remote Name",
            ),
        )
        for name, rel in rels:
            self.of.write("""<tr class="tablevalues">""")
            self.td(name)
            self.td(rel.__class__.__name__)
            self.td(rel.remoteType.__name__)
            self.td(
                """<a href="%s.html">%s</a>"""
                % (rel.remoteClass, rel.remoteClass)
            )

            self.td(rel.remoteName)
            self.of.write("</tr>")
        self.of.write("</table>")

    def writeTableHeader(self, title, colnames):
        self.of.write("<table>")
        self.of.write(
            """<tr class="tabletitle"><td colspan="%s">%s</td></tr>"""
            % (len(colnames), title)
        )
        self.of.write("""<tr class="tableheader">""")
        for colname in colnames:
            self.of.write("<td>%s</td>" % colname)

    def writeHeader(self):
        self.of.write("<html>")
        self.of.write("<head>")
        self.of.write(
            """<link rel="stylesheet" href="schemadoc.css" """
            """type="text/css" />"""
        )
        self.of.write("</head>")
        self.of.write("<body>")

    def writeFooter(self):
        self.of.write("</body></html>")

    def getHref(self, cls):
        name = getattr(cls, "__name__", cls)
        return ".".join((self.baseModule, name)) + ".html"

    def getFileName(self, cls, outdir=True):
        filename = os.path.join(self.outdir, self.getHref(cls))
        dirname = os.path.dirname(filename)
        if not os.path.isdir(dirname):
            os.makedirs(dirname, 0o750)
        return filename

    def td(self, value):
        self.of.write("<td>%s</td>" % value)


baseModule = None
if len(sys.argv) > 1:
    baseModule = sys.argv[1]
docdir = zenPath("zendocs/schema")
classList = importClasses(
    basemodule=baseModule, skipnames=("ZentinelPortal", "ZDeviceLoader")
)
htmlGen = HtmlGenerator(baseModule, classList, docdir)
htmlGen.generate()
cssfile = os.path.join(os.path.dirname(__file__), "schemadoc.css")
shutil.copy2(cssfile, docdir)
