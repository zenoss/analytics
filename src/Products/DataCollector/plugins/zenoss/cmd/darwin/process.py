##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.ProcessCommandPlugin import ProcessCommandPlugin


class process(ProcessCommandPlugin):
    """Maps ps output to process."""

    command = "/bin/ps axho command"

    def _filterLines(self, lines):
        """Skip the first line as it is a header"""
        return lines[1:]

    def condition(self, device, log):
        return device.os.uname == "Darwin"
