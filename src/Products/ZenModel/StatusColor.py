##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Status

StatusColor class is a base for things which have status
that needs to be represented in html with color.

$Id: StatusColor.py,v 1.8 2004/04/04 01:51:19 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]

class StatusColor:
    """Status object"""

    def devStatusColor(self, status):
        retval="#00ff00"
        if status == -1:
            retval = "#d02090"
        elif status == -2:
            retval = "#ff9900"
        elif status > 0:
            retval = "#ff0000"
        return retval

    def pingColor(self):
        return self.statusColor(self.pingStatus)

    def snmpColor(self):
        return self.statusColor(self.snmpStatus)
