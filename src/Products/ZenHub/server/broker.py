##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, 2018 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from twisted.spread import pb
from twisted.spread.interfaces import IUnjellyable


class ZenSecurityOptions(object):
    """Override SecurityOptions with more permissive security."""

    def isModuleAllowed(self, moduleName):
        """Return True always because all modules are allowed."""
        return True

    def isClassAllowed(self, klass):
        """Return True if the given class is allowed, False otherwise.

        Assumes the module has already been allowed.

        A class is allowed if it implements the IUnjellyable interface.
        """
        return IUnjellyable.implementedBy(klass)

    def isTypeAllowed(self, typeName):
        """Return True always because all all typenames are allowed."""
        return True


zenSecurityOptions = ZenSecurityOptions()


class ZenBroker(pb.Broker):
    """Extend pb.Broker to pass the ZenSecurityOptions object to pb.Broker."""

    def __init__(self, **kw):
        """Initialize an instance of ZenBroker."""
        kw["security"] = zenSecurityOptions
        pb.Broker.__init__(self, **kw)


class ZenPBClientFactory(pb.PBClientFactory):
    """Extend pb.PBClientFactory to specify ZenBroker as the protocol."""

    protocol = ZenBroker


class ZenPBServerFactory(pb.PBServerFactory):
    """Extend pb.PBServerFactory to specify ZenBroker as the protocol."""

    protocol = ZenBroker
