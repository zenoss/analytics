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

log = logging.getLogger("zen.zentrap.oidmap")


class OidMap(object):
    """
    Retrieves the OID map from ZenHub.
    """

    def __init__(self, app):
        self._app = app
        self._checksum = None
        self._oidmap = {}

    def to_name(self, oid, exactMatch=True, strip=False):
        """
        Returns a MIB name based on an OID and special handling flags.

        @param oid: SNMP Object IDentifier
        @type oid: string
        @param exactMatch: find the full OID or don't match
        @type exactMatch: boolean
        @param strip: show what matched, or matched + numeric OID remainder
        @type strip: boolean
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        if isinstance(oid, tuple):
            oid = ".".join(map(str, oid))

        oid = oid.strip(".")
        if exactMatch:
            return self._oidmap.get(oid, oid)

        oidlist = oid.split(".")
        for i in range(len(oidlist), 0, -1):
            name = self._oidmap.get(".".join(oidlist[:i]), None)
            if name is None:
                continue

            oid_trail = oidlist[i:]
            if len(oid_trail) > 0 and not strip:
                return "%s.%s" % (name, ".".join(oid_trail))
            return name

        return oid

    @defer.inlineCallbacks
    def task(self):
        log.debug("retrieving oid map")
        try:
            service = yield self._app.getRemoteConfigCacheProxy()
            checksum, oidmap = yield service.callRemote(
                "getOidMap", self._checksum
            )
            if checksum is None:
                if self._checksum is None:
                    log.info("waiting for the OID map to be built")
                else:
                    log.debug("no update available for the current OID map")
            else:
                state = "initial" if self._checksum is None else "updated"
                self._checksum = checksum
                self._oidmap = oidmap
                log.info("received %s OID map", state)
        except Exception:
            log.exception("failed to retrieve oid map")
