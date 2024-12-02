##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Exceptions


$Id: Exceptions.py,v 1.2 2003/10/04 15:54:36 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

from Products.ZenUtils.Exceptions import ZentinelException

class ZenModelError(ZentinelException): pass

class IpAddressConflict(ZenModelError): 
    """Two or more devices have the same ip"""

class IpCatalogNotFound(ZenModelError):
    """Can't find the Ip Catalog in the context passed"""

class WrongSubnetError(ZenModelError):
    pass

class DeviceExistsError(ZenModelError):
    """a device with this fqdn is already in the dmd"""
    def __init__(self, msg, dev):
        ZenModelError.__init__(self, msg)
        self.dev = dev

class PathNotFoundError(ZenModelError):
    """no object found in the dmd at the path given"""

class TraceRouteGap(ZenModelError):
    """Missing data found during traceroute."""


class NoSnmp(ZenModelError):
    """Can't open an snmp connection to the device."""

class NoIPAddress(ZenModelError):
    """No IP Address found for device name."""
