##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenHub.HubService import HubService
from Products.ZenHub.PBDaemon import translateError

from ZODB.POSException import ConflictError


class TestService(HubService):
    def remote_echo(self, value):
        return value

    @translateError
    def remote_raiseException(self, message):
        raise Exception(message)

    @translateError
    def remote_raiseConflictError(self, message):
        raise ConflictError(message)
