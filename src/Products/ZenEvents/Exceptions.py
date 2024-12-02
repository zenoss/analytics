##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__= """Zenoss exceptions

Some common exceptions detected by layers close to the GUI,
which can be caught by things such as dmd.error_handler()
"""


from Products.ZenUtils.Exceptions import ZentinelException

class ZenEventError(ZentinelException):
    """
    General problem with the event system.
    """

class ZenBackendFailure(ZenEventError):
    """MySQL or ZEO backend database connection is lost.
    """

class MySQLConnectionError(ZenEventError):
    """MySQL database connection is lost.
    """

class ZenEventNotFound(ZenEventError):
    """
    Lookup of event failed
    """

class pythonThresholdException(ZenEventError):
    """
    User-supplied threshold Python expression caused
    a traceback.
    """

class rpnThresholdException(ZenEventError):
    """
    User-supplied threshold RPN expression caused
    a traceback.
    """
