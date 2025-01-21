#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import time
from Products.ZenEvents.Schedule import Schedule
from Products.ZenEvents.ActionRule import ActionRule

print "Adjusting schedules for daylight savings time."
print "%s %s" % ('-'*57, '-'*21)

from Products.ZenUtils.ZenScriptBase import ZenScriptBase
dmd = ZenScriptBase(connect=True).dmd

s = Schedule(None, dmd)
for next, window in s.makeWorkList(time.time(), s.getWindows()):
    nextList = time.localtime(next)
    startList = time.localtime(window.start)
    target = window.target()
    windowString = "%s on " % window.id
    if isinstance(target, ActionRule):
        windowString += "%s/%s" % (target.getUserid(), target.getId())
    else:
        windowString += target.getId()
    if nextList[3] == startList[3]:
        print "%56s: No adjustment needed." % windowString
    elif nextList[3] == (startList[3] - 1) or \
        (nextList[3] == 23 and startList[3] == 0):
        print "%56s: Fall back." % windowString
        window.start = next + 3600
    elif nextList[3] == (startList[3] + 1) or \
        (nextList[3] == 0 and startList[3] == 23):
        print "%56s: Spring forward." % windowString
        window.start = next - 3600

import transaction
trans = transaction.get()
trans.note("fixSchedulesForDST")
trans.commit()
