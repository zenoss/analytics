##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from twisted.cred import checkers, portal
from twisted.spread import pb
from zope.interface import implementer

from .utils import getLogger


@implementer(portal.IRealm)
class HubRealm(object):
    """Defines realm from which avatars are retrieved.

    NOTE: Only one avatar is used.  Only one set of credentials are used to
    log into ZenHub, so the Realm cannot distingish between different clients.
    All connections look like the same user so they all get same avatar.
    """

    def __init__(self, avatar):
        """Initialize an instance of HubRealm.

        :param avatar: Represents the logged in client.
        :type avatar: HubAvatar
        """
        self.__avatar = avatar
        self.__log = getLogger(self)

    def requestAvatar(self, name, mind, *interfaces):
        """Return an avatar.

        Raises NotImplementedError if interfaces does not include
        pb.IPerspective.
        """
        if pb.IPerspective not in interfaces:
            raise NotImplementedError
        self.__log.debug(
            "Client authenticated who=probably-%s",
            "zenhubworker" if mind else "collector-daemon",
        )
        return (
            pb.IPerspective,
            self.__avatar,
            lambda: self._disconnected(mind),
        )

    def _disconnected(self, mind):
        self.__log.debug(
            "Client disconnected who=probably-%s",
            "zenhubworker" if mind else "collector-daemon",
        )


def getCredentialCheckers(pwdfile):
    """Load the password file.

    @return: an object satisfying the ICredentialsChecker
    interface using a password file or an empty list if the file
    is not available.  Uses the file specified in the --passwd
    command line option.
    """
    checker = checkers.FilePasswordDB(pwdfile)
    return [checker]
