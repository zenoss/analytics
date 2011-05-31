#!/usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.Zuul.facades import getFacade

class zenackevents(ZenScriptBase):

    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('--userid',
                    dest="userid",default="",
                    help="name of user who is acking the event")
        
        self.parser.add_option('--evid',
                    dest="evids", action="append",
                    help="event id that is acked")

        self.parser.add_option('--state', type='int',
                    dest="state", default=1,
                    help="event id that is acked [default: ack]")

    def ack(self):
        if not self.options.evids:
            self.parser.error("Require one or more event ids to be acknowledged.")
        if not self.options.userid:
            self.parser.error("Require username who is acknowledging the event.")
        if not self.options.state in (0,1):
            self.parser.error("Invalid state: %d" % self.options.state)

        zep = getFacade('zep', self.dmd)
        event_filter = zep.createEventFilter(uuid=self.options.evids)
        # Old event states = 0=New, 1=Acknowledge
        if self.options.state == 0:
            zep.reopenEventSummaries(eventFilter=event_filter, userName=self.options.userid)
        elif self.options.state == 1:
            zep.acknowledgeEventSummaries(eventFilter=event_filter, userName=self.options.userid)

if __name__ == '__main__':
    zae = zenackevents(connect=True)
    zae.ack()
