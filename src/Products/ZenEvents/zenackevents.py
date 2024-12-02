##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import sys

from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.Zuul.facades import getFacade

log = logging.getLogger(name="zen.ackevents")


class zenackevents(ZenScriptBase):
    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenScriptBase.buildOptions(self)
        self.parser.add_option(
            "--userid",
            dest="userid",
            default="",
            help="name of user who is acking the event",
        )

        self.parser.add_option(
            "--evid",
            dest="evids",
            action="append",
            help="event id that is acked",
        )

        self.parser.add_option(
            "--state",
            type="int",
            dest="state",
            default=1,
            help="event id that is acked [default: ack]",
        )

    def ack(self):
        if not self.options.evids:
            self.parser.error(
                "Require one or more event ids to be acknowledged."
            )
        if not self.options.userid:
            self.parser.error(
                "Require username who is acknowledging the event."
            )
        if self.options.state not in (0, 1):
            self.parser.error("Invalid state: %d" % self.options.state)

        zep = getFacade("zep", self.dmd)
        event_filter = zep.createEventFilter(uuid=self.options.evids)
        try:
            # Old event states = 0=New, 1=Acknowledge
            if self.options.state == 0:
                zep.reopenEventSummaries(
                    eventFilter=event_filter, userName=self.options.userid
                )
            elif self.options.state == 1:
                zep.acknowledgeEventSummaries(
                    eventFilter=event_filter, userName=self.options.userid
                )
        except Exception as e:
            if log.isEnabledFor(logging.DEBUG):
                log.exception("Failed to acknowledge events")
            print(e.message, file=sys.stderr)
            sys.exit(1)


def main():
    zenackevents(connect=True).ack()
