##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from twisted.spread import pb


class DeviceProxy(pb.Copyable, pb.RemoteCopy):
    """
    Provide a cache of configuration information as needed by plugins
    while running
    """

    def __init__(self):
        """
        Do not use base classes intializers
        """
        pass

    def getSnmpLastCollection(self):
        """
        Return the time of the last collection time

        @return: time of the last collection
        @rtype: Python DateTime object
        """
        from DateTime import DateTime

        return DateTime(float(self._snmpLastCollection))

    def getSnmpStatus(self):
        """
        Numeric status of our SNMP collection

        @return: status
        @rtype: number
        """
        return getattr(self, "_snmpStatus", 0)

    getSnmpStatusNumber = getSnmpStatus

    def getId(self):
        """
        Return our id

        @return: identification
        @rtype: string
        """
        return self.id


pb.setUnjellyableForClass(DeviceProxy, DeviceProxy)
