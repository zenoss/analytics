##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import Interface


class ICallHomeCollector(Interface):
    """
    Implementers provide call home data.
    """

    def generateData(self):
        """
        Generate data to be sent via call home.

        @return: Dictionary of data to be sent.  Values keyed by "_ERRORS_"
            should be objects that will be attached at the top level.
        @rtype: dict
        """


class IMasterCallHomeCollector(Interface):
    """
    Implementers provide call home data when collected on zenoss master.
    """

    def generateData(self, dmd):
        """
        Generate data to be sent via call home.

        @param dmd: Databse connection
        @return: Dictionary of data to be sent values keyed by "_ERRORS_"
            should be objects that will be attached at the top level.
        @rtype: dict
        """


class IVersionHistoryCallHomeCollector(Interface):
    """
    Implementers provide version history records.
    """

    def addVersionHistory(self, dmd, callHomeData):
        """
        Create records to be added to version history.
        @param the callhome data that will be modified then sent.
        """


class IHostData(Interface):
    """
    Used to gather Host machine statistics for call home.
    """

    def callHomeData(self):
        """
        @return:: name, value pairs of host stats for call home.
        @rtype: list or generator of tuples.
        """


class IZenossData(Interface):
    """
    Used to gather Zenoss statistics for call home.
    """

    def callHomeData(self, dmd):
        """
        @param: dmd connection.
        @return: name, value pairs of Zenoss instance stats for call home.
        @rtype: list or generator of tuples.
        """


class IZenossEnvData(Interface):
    """
    Used to gather the Zenoss environment data for call home.
    """

    def callHomeData(self):
        """
        @return: name, value pairs of host stats for call home
        @rtype: list or generator of tuples
        """


class IDeviceLink(Interface):
    """
    Subscription Adapter to determine if a device is linked to
    another resource (such as a VM component). The adapter name of this
    interface is used for the call home key: Linked Devices - %s, where
    %s is the name of the adapter.
    """

    def linkedDevice(self):
        """
        Return a linked object, if it exists.
        @return: A linked object of ZenModelRM type or None
        """


class IDeviceResource(Interface):
    """
    Subscription Adapter to Provide more resource data about a device
    """

    def processDevice(self, stats):
        """
        Determine any resource metrics about the device and add or update
        the passed in stats dictionary
        @param: stats - statistics about the device
        @type: dictionary
        @return: None
        """


class IDeviceType(Interface):
    """
    Adapter to determine the type of device. examples: Xen, VMware,
    Physical etc...
    """

    def type(self):
        """
        @return: type of device. example: "VMware", "Xen", "Physical
        @rtype: str
        """

    def isVM(self):
        """
        @return: True if device is a vm, false otherwise
        @rtype: bool
        """


class IVirtualDeviceType(Interface):
    """
    Subscription adapter. Determine the virtual machine type of a device
    if any. More than one impl can be registered per Device
    """

    def vmType(self):
        """
        @return the type of virtual machine or None if not a virtual
                machine or it cannot be determined
        """


class IDeviceCpuCount(Interface):
    """
    Adapter to Provide more cpu count for a device
    """

    def cpuCount(self):
        """
        Determine number of CPUs on a device
        @return: number of cpus
        @rtype: int
        """
