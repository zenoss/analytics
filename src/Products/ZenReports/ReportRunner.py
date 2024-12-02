#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import csv

from pprint import pprint
from sys import stdout

from Products.ZenUtils.ZCmdBase import ZCmdBase


class ReportRunner(ZCmdBase):
    """Run a report plugin and display the output."""

    def main(self):
        if self.options.list:
            plugins = self.dmd.ReportServer.listPlugins()
            pprint(sorted(plugins))
            return

        plugin = self.args[0]
        args = {}
        for a in self.args[1:]:
            if a.find("=") > -1:
                key, value = a.split("=", 1)
                args[key] = value

        self.log.debug("Running '%s' with %r", plugin, args)
        result = self.dmd.ReportServer.plugin(plugin, args)
        if not result:
            self.log.warn("No results returned from plugin.")
            return

        if self.options.export == "csv":
            self.writeCsv(result)
        else:
            if self.options.export_file:
                fh = open(self.options.export_file, "w")
            else:
                fh = stdout
            pprint(result, stream=fh)
            if fh is not stdout:
                fh.close()

    def writeCsv(self, results):
        """
        Write the CSV output to standard output.
        """
        if self.options.export_file:
            fh = open(self.options.export_file, "w")
        else:
            fh = stdout

        sampleRow = results[0]
        fieldnames = sorted(sampleRow.values.keys())

        # Write a header line that DictReader can import
        fh.write(",".join(fieldnames) + "\n")
        writer = csv.DictWriter(
            fh, fieldnames, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n"
        )
        for line in results:
            writer.writerow(line.values)

        if fh is not stdout:
            fh.close()

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.usage = (
            "%prog [options] report_plugin [report_paramater=value]*"
        )
        self.parser.remove_option("--daemon")
        self.parser.remove_option("--cycle")
        self.parser.remove_option("--watchdog")
        self.parser.remove_option("--watchdogPath")
        self.parser.remove_option("--socketOption")
        self.parser.add_option(
            "--list",
            action="store_true",
            default=False,
            help="Show full names of all plugins to run. If the plugin"
            " name is unique, just the name may be used.",
        )
        self.parser.add_option(
            "--export",
            default="python",
            help="Export the values as 'python' (default) or 'csv'",
        )
        self.parser.add_option(
            "--export_file",
            default="",
            help="Optional filename to store the output",
        )


if __name__ == "__main__":
    rr = ReportRunner()
    rr.main()
