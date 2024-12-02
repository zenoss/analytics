##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from ..form.schema import Int, Float, List
from ..utils import ZuulMessageFactory as _t
from . import IInfo, ITreeNode, IFacade


class IMonitorTreeNode(ITreeNode):
    """
    """


class IMonitorInfo(IInfo):
    """
    Set of attributes describing a performance monitor.
    """
    eventlogCycleInterval = Int(
        title=_t("Event Log Cycle Interval (seconds)"),
        description=_t("How often zeneventlog collects events")
    )

    processCycleInterval = Int(
        title=_t("Process Cycle Interval (seconds)"),
        description=_t(
            "How often zenprocess collects performance metrics "
            "about running processes")
    )

    statusCycleInterval = Int(
        title=_t("Status Cycle Interval (seconds)"),
        description=_t("How often zenstatus polls tests configured ports")
    )

    winCycleInterval = Int(
        title=_t("Windows Cycle Interval (seconds)"),
        description=_t("How often zenwinperf collects performance metrics")
    )

    wmibatchSize = Int(
        title=_t("WMI Batch Size"),
        description=_t("Size of the number of WMI queries we issue at a time")
    )

    wmiqueryTimeout = Int(
        title=_t("WMI Query Timeout (seconds)"),
        description=_t(
            "How long zeneventlog and zenwin will wait on a WMI "
            "response when collecting")
    )

    configCycleInterval = Int(
        title=_t("Config Cycle Interval (minutes)"),
        description=_t(
            "The interval, specified in minutes, that the collector&apos;s "
            "configuration will be updated from the ZenHub service")
    )

    pingTimeOut = Float(
        title=_t("Ping Timeout (seconds)"),
        description=_t(
            "How long zenping will wait before timing out a ping request")
    )

    pingTries = Int(
        title=_t("Ping Tries"),
        description=_t(
            "Number of times zenping will attempt to ping a device")
    )

    pingCycleInterval = Int(
        title=_t("Ping Cycle Interval (seconds)"),
        description=_t("How often zenping will attempt to ping devices")
    )

    modelerCycleInterval = Int(
        title=_t("Modeler Cycle Interval (minutes)"),
        description=_t("How often zenmodeler will remodel devices")
    )

    discoveryNetworks = List(
        title=_t("Discovery Networks"),
        description=_t(
            "Comma separated list of subnets that zendisc will "
            "run discovery on")
    )


class IMonitorFacade(IFacade):
    """
    An interface describing how to lookup, create, edit, and delete
    IMonitor objects.
    """

    def query(monitorId=None):
        """
        Return a sequence of IMonitorInfo objects.
        """

    def get(monitorId, default=None):
        """
        Return the IMonitorInfo object having the specified ID.
        """

    def add(monitorId, sourceId=None):
        """
        Creates a new performance monitor.  The new monitor is created as
        a copy of the monitor given by sourceId.  If sourceId is not
        specified, then the default monitor is the source.

        The IMonitorInfo object of the new monitor is returned.
        """

    def delete(monitorId):
        """
        Deletes the identified performance monitor.
        """
