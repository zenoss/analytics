##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenUtils.ZCmdBase import ZCmdBase
zodb = ZCmdBase(noopts=True)
zem = zodb.dmd.ZenEventManager

from Products.ZenEvents.Event import Event
from Products.ZenEvents.ZenEventClasses import Status_Ping

evt = Event()
evt.device = "gate.confmon.loc"
evt.eventClass = Status_Ping
evt.summary = "device is down"
evt.severity = 5
zem.sendEvent(evt)

evt = Event()
evt.device = "gate.confmon.loc"
evt.eventClass = "TestEvent"
evt.summary = "this is a test event"
evt.severity = 3
evt.ntseverity = "info"
evt.ntsource = "Zope"
zem.sendEvent(evt)
