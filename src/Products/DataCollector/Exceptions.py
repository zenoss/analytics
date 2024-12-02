##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Exceptions

Common exceptions for data collectors
"""

from Products.ZenUtils.Exceptions import ZentinelException


class DataCollectorError(ZentinelException):
    pass


class ObjectCreationError(DataCollectorError):
    """Failed to create a related object while appling maps"""


class LoginFailed(DataCollectorError):
    """Indicates a failed login to the remote device"""


class CommandTimeout(DataCollectorError):
    """Full command response was not received before timeout was reached"""


class StateTimeout(DataCollectorError):
    """A timeout occured while we were waiting for some data"""


class NoServerFound(DataCollectorError):
    """No telnet or ssh server found on a machine at the given port"""


class CommandNotFound(DataCollectorError):
    """No command found to run"""


class NoValidConnection(DataCollectorError):
    """No valid connection found to make"""
