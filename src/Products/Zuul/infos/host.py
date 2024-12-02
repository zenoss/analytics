##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import implementer
from Products.Zuul.interfaces import IHostInfo


@implementer(IHostInfo)
class HostInfo(object):
    """
    Info object for the applications returned from the control
    plane.
    """

    def __init__(self, host):
        """
        Initialize an instance of HostInfo.

        :param IHost host: The host.
        """
        self._object = host

    @property
    def id(self):
        return self._object.id

    uid = id

    @property
    def name(self):
        return self._object.name

    @property
    def poolId(self):
        return self._object.poolId

    @property
    def ipAddr(self):
        return self._object.ipAddr

    @property
    def cores(self):
        return self._object.cores

    @property
    def memory(self):
        return self._object.memory

    @property
    def privateNetwork(self):
        return self._object.privateNetwork

    @property
    def kernelVersion(self):
        return self._object.kernelVersion

    @property
    def kernelRelease(self):
        return self._object.kernelRelease
