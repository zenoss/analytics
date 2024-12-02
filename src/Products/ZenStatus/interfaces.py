##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope import interface
from zope.component.interfaces import Interface

from Products.ZenCollector import interfaces


class IPingTask(interfaces.IScheduledTask):
    """
    Task to perform process pings on an ip.
    """

    def processPingResult(pingResult):
        """
        Process a ping result.
        """
        pass


class IParserReadyForOptionsEvent(Interface):
    """
    A parser is ready for extra options to be added.
    """

    parser = interface.Attribute("The option parser")


class IPingTaskFactory(interfaces.IScheduledTaskFactory):
    """
    Factory to create PingTasks.
    """


class IPingCollectionPreferences(interfaces.ICollectorPreferences):
    """
    Class to customize app startup based on ping backend.
    """


class IPingTaskCorrelator(interface.Interface):
    """
    Class that will attempt correlation given the list of all
    ip tasks for a zenping instance.
    """

    def __call__(pingTasks):
        pass


class IPingResult(interface.Interface):
    """
    Class to store results from ping scan.
    """

    timestamp = interface.Attribute(
        """Timestamp of when ping was returned (seconds since epoch)."""
    )

    address = interface.Attribute("""Address of the host""")

    trace = interface.Attribute("""traceroute of the host""")

    getStatusString = interface.Attribute("""status string: up or down""")

    isUp = interface.Attribute("""true if host is up, false if host is down""")

    rtt = interface.Attribute(
        """round trip time aka ping time aka rtt; nan if host was down"""
    )

    variance = interface.Attribute(
        """variance of the rtt; nan if host was down"""
    )

    stdDeviation = interface.Attribute(
        """standard deviation of the rtt; nan if host was down"""
    )
