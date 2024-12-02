##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import base64
import logging
import urllib2

from urllib import urlencode

from Products.ZenCallHome.CallHomeStatus import CallHomeStatus
from Products.ZenCallHome.transport import CallHome

POST_CHECKIN_URL = "https://callhome.zenoss.com/callhome/v2/post"
_URL_TIMEOUT = 5

logger = logging.getLogger("zen.callhome")


def direct_post(dmd):
    callhome = CallHome(dmd)
    chs = CallHomeStatus()
    if not callhome.attempt("directpost"):
        return

    payload = callhome.get_payload()
    if not payload:
        logger.warning("Error getting or encrypting payload for direct-post")
        return
    payload = base64.urlsafe_b64encode(payload)

    params = urlencode({"enc": payload})

    chs.stage(chs.REQUEST_CALLHOME)
    try:
        httpreq = urllib2.urlopen(POST_CHECKIN_URL, params, _URL_TIMEOUT)
        returnPayload = httpreq.read()
    except Exception as e:
        chs.stage(chs.REQUEST_CALLHOME, "FAILED", str(e))
        logger.warning("Error retrieving data from callhome server %s", e)
    else:
        chs.stage(chs.REQUEST_CALLHOME, "FINISHED")
        callhome.save_return_payload(returnPayload)
