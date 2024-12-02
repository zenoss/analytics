##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Interface


class IServiceDefinition(Interface):
    """
    Marks a ServiceDefinition class.
    """


class IServiceInstance(Interface):
    """
    Marks a ServiceInstance class.
    """

class IServiceStatus(Interface):
    """
    Marks a ServiceStatus class.
    """
