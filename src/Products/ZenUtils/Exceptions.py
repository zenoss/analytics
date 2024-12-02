##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from exceptions import Exception


class ZentinelException(Exception):
    """Root of all Zentinel Exceptions"""
    pass


class ZenPathError(ZentinelException):
    """When walking a path something along the way wasn't found."""
    pass


class ZenResolveExceptionError(ZentinelException):
    '''failed to resolve exception from twisted.python.failure.Failure
    '''
    pass


def resolveException(failure):
    '''Given a twisted.python.failure
    return the remote exception type that was initially raised.
    '''

    try:
        # return the original exception
        if isinstance(failure.value, Exception):
            return failure.value

        # raise the original exception capture and return it
        try:
            failure.raiseException()
        except Exception as err:
            return err

    except Exception:
        return ZenResolveExceptionError(failure)
