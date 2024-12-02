##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from .manager import SecondaryNavigationManager


def getSelectedNames(view):
    mgr = SecondaryNavigationManager(view.context, view.request, view)
    mgr.update()
    primary = mgr.getActivePrimaryName()
    for v in mgr.getActiveViewlets():
        if v.selected:
            secondary = v.__name__
            break
    else:
        secondary = ""
    return primary, secondary
