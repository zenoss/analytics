##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenUtils.Exceptions import ZentinelException


class RRDException(ZentinelException):
    pass


class RRDObjectNotFound(RRDException):
    pass


class TooManyArgs(RRDException):
    pass


class RRDTemplateError(RRDException):
    pass


class RRDGraphError(RRDException):
    pass
