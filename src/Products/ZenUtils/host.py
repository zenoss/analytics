##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Host related stuff.
"""

from zope.interface import Interface, Attribute

class IHost(Interface):
    """
    For inspecting Control Center hosts.
    """

    id = Attribute("Globally unique host identifier")
    name = Attribute("Name of the host")
    poolId = Attribute("Name of the pool on which the host is running")
    ipAddr = Attribute("IP Address of the host")
    cores = Attribute("Number of processor cores")
    memory = Attribute("Memory (bytes) available on the host")
    privateNetwork = Attribute("Private network of the host")
    createdAt = Attribute("Time host was added")
    updatedAt = Attribute("Time the host was updated")
    kernelVersion = Attribute("Kernel version of the host OS")
    kernelRelease = Attribute("Kernel release number of the host OS")



class IHostManager(Interface):
    """
    For identifying and locating Zenoss hosts.
    """

    def query(self):
        """
        Returns a sequence of IHost objects
        """

    def get(id, default=None):
        """
        Retrieve the IHost object of the identified host.
        The default argument is returned if the host doesn't exist.

        :param string id: The host ID (not its name).
        :param object default: Alternate return value
        """

__all__ = (
    "IHostManager", "IHost"
)
