##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import base64
import json
import logging
import random
import string
import zlib

from zope import interface
from Products.Five.viewlet import viewlet

from Products.ZenUI3.browser.interfaces import IHeadExtraManager
from Products.ZenUtils.Ext import DirectRouter

from Products.ZenCallHome.transport import CallHome

JS_CALLHOME_URL = "https://callhome.zenoss.com/callhome/v2/js"
MAX_GET_SIZE = 768

logger = logging.getLogger("zen.callhome")


def split_to_range(strToSplit, maxSize):
    return [
        strToSplit[i : i + maxSize] for i in range(0, len(strToSplit), maxSize)
    ]


def encode_for_js(toEnc):
    base64ToEnc = base64.urlsafe_b64encode(toEnc)
    randToken = "".join(
        random.choice(string.ascii_letters + string.digits) for x in range(8)
    )
    encPackets = split_to_range(base64ToEnc, MAX_GET_SIZE)
    encPackets = [
        json.dumps(
            {
                "idx": x,
                "tot": len(encPackets),
                "rnd": randToken,
                "dat": encPackets[x],
            }
        )
        for x in range(len(encPackets))
    ]
    return [base64.urlsafe_b64encode(zlib.compress(x)) for x in encPackets]


@interface.implementer(IHeadExtraManager)
class ScriptTag(viewlet.ViewletBase):
    """
    JS script tag injector for browser-based checkins
    """

    def render(self):
        dmd = self.context.dmd

        # if not logged in, inject nothing
        if not dmd.ZenUsers.getUserSettings():
            return ""

        callhome = CallHome(dmd)
        # if we've checked in or attempted to check in recently, inject nothing
        if not callhome.attempt("browserjs"):
            return ""

        payload = callhome.get_payload(method="browserjs")
        if not payload:
            logger.warning("Error getting or encrypting payload for browserjs")
            return ""

        # Output the checkin data to a js snippet, wait a few seconds in the
        # browser, and inject script tags to the checkin url to the body tag.
        # This makes sure that the browser never waits on the checkin url.
        # Callbacks from the server script invoke the next
        # Zenoss.Callhome_next()
        return """<script type="text/javascript">
            var packets = %s,
                currentPacket = 0;
            Zenoss.Callhome_next = function() {
                if (currentPacket < packets.length) {
                    var script = document.createElement('script');
                    script.type= 'text/javascript';
                    script.src = "%s?enc=" + packets[currentPacket];
                    document.body.appendChild(script);
                }
                currentPacket += 1;
            };
            var task = new Ext.util.DelayedTask(Zenoss.Callhome_next);
            task.delay(5000);
            </script>""" % (
            json.dumps(encode_for_js(payload)),
            JS_CALLHOME_URL,
        )


class CallhomeRouter(DirectRouter):
    def checkin(self, returnPayload):
        # record successful check in
        callhome = CallHome(self.context.dmd)
        callhome.save_return_payload(returnPayload)
        return ""
