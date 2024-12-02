##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from twisted.internet import defer

log = logging.getLogger("zen.zentrap.users")


class CreateAllUsers(object):
    """
    Create all users task.
    """

    def __init__(self, app, receiver):
        self._app = app
        self._receiver = receiver
        self._users = []

    @defer.inlineCallbacks
    def task(self):
        try:
            service = yield self._app.getRemoteConfigServiceProxy()
            users = yield service.callRemote("createAllUsers")
            diffs = tuple(u for u in users if u not in self._users)
            if diffs:
                log.debug(
                    "received %d new/updated user%s",
                    len(diffs),
                    "s" if len(diffs) != 1 else "",
                )
                self._receiver.create_users(diffs)
            self._users = users
        except Exception:
            log.exception("failed to retrieve SNMP users")
