##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.ProcessCommandPlugin import ProcessCommandPlugin


class process(ProcessCommandPlugin):
    """Parses ps command output to model processes."""

    command = "ps axho args"
