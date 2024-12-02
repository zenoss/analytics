###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging

from twisted.internet import defer, reactor
from twisted.internet import task as twistedTask
from zope import component, interface

from Products import ZenCollector

from .interfaces import IPingTaskCorrelator

LOG = logging.getLogger("zen.zenping.SimpleCorrelator")

# amount of IPs/events to process before giving time to the reactor
_SENDEVENT_YIELD_INTERVAL = 100  # should always be >= 1


def noOpYield():
    return twistedTask.deferLater(
        reactor,
        0,
        lambda: None,
    )


def simpleCorrelator(ipTasks, connected_ips=True, reactorYield=noOpYield):

    downTasks = {
        ipTask.config.ip: ipTask
        for ipTask in ipTasks.itervalues()
        if not ipTask.delayedIsUp
    }

    # find connectedIps of down tasks, and create a lookup
    downConnectedIps = {}

    if connected_ips:
        for ip, ipTask in ipTasks.iteritems():
            if ipTask.isUp or ipTask.delayedIsUp:
                continue
            if ipTask._device.connectedIps:
                for connectedIp, componentId in ipTask._device.connectedIps:
                    if connectedIp != ip and connectedIp not in downTasks:
                        downConnectedIps[connectedIp] = ipTask, componentId

    i = 0
    # for every down ipTask
    for currentIp, ipTask in downTasks.iteritems():
        i += 1
        # walk the hops in the traceroute
        for hop in ipTask.trace:

            if hop.ip != currentIp:
                if hop.ip in downTasks:
                    # we found our root cause!
                    rootCause = downTasks[hop.ip]
                    rootCauseMessage = (
                        "IP %r on interface %r is connected "
                        "to device %r and is also in the traceroute "
                        "for monitored ip %r on device %r"
                        % (
                            hop.ip,
                            rootCause.config.iface,
                            rootCause.configId,
                            currentIp,
                            ipTask.configId,
                        )
                    )
                    cause = {
                        "rootcause.deviceId": rootCause.configId,
                        "rootcause.componentId": rootCause.config.iface
                        or None,
                        "rootcause.componentIP": hop.ip,
                        "rootcause.message": rootCauseMessage,
                    }
                    ipTask.sendPingDown(suppressed=True, **cause)
                    break
                if hop.ip in downConnectedIps:
                    rootCause, componentId = downConnectedIps[hop.ip]
                    rootCauseMessage = (
                        "IP %r on interface %r is connected "
                        "to device %r and is also in the traceroute "
                        "for monitored ip %r on device %r"
                        % (
                            hop.ip,
                            componentId,
                            rootCause.configId,
                            currentIp,
                            ipTask.configId,
                        )
                    )
                    cause = {
                        "rootcause.deviceId": rootCause.configId,
                        "rootcause.componentId": componentId,
                        "rootcause.componentIP": hop.ip,
                        "rootcause.message": rootCauseMessage,
                    }
                    ipTask.sendPingDown(
                        suppressed=True,
                        suppressedWithconnectedIp="True",
                        **cause
                    )
                    break
        else:
            # no root cause found
            ipTask.sendPingDown()

        # give time to reactor to send events if necessary
        if i % _SENDEVENT_YIELD_INTERVAL:
            yield reactorYield()


class SimpleCorrelator(object):
    interface.implements(IPingTaskCorrelator)

    def __call__(self, ipTasks):
        """
        Correlate ping down events.

        This simple correlator will take a list of PingTasks and filters out
        up tasks. It loops through the list and the last known trace route
        for each of the ip's. For every hop in the traceroute (starting from
        the collector to the ip in question), the hop's ip is searched for in
        downTasks. If it's found, then this collector was also monitoring the
        source of the problem.

        Note: this does not take in to account multiple routes to the ip in
        question. It uses only the last known traceroute as given by nmap which
        will not have routing loops and hosts that block icmp.
        """

        options = component.getUtility(
            ZenCollector.interfaces.ICollector
        ).options
        connected_ips = True if options.connected_ips == "enabled" else False

        f = defer.inlineCallbacks(simpleCorrelator)
        return f(ipTasks, connected_ips)
