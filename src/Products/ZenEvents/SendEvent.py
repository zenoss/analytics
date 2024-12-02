##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
import socket
import xmlrpclib

from Products.ZenUtils.Utils import  basicAuthUrl

class SendEvent(object):

    def __init__(self, agent, username, password, url):
        self.agent = agent
        self.url = basicAuthUrl(username, password, url)
        self.server = xmlrpclib.Server(self.url)
        severities = self.server.getSeverities()
        for name, value in severities:
            setattr(self, name, value)


    def sendEvent(self, deviceName, evclass, msg, severity, **kwargs):
        """
        Send a ZenEvent to the event manager.  Events must have:
        deviceName - which is the FQDN of the device
        evclass - the event class of the event
        msg - the event message
        severity - the severity of the event 

        agent - is the management collection system that the event came through

        Other potential fields are:

        """
        event = {}
        event['Node'] = deviceName
        event['Class'] = evclass
        event['Summary'] = msg
        event['Severity'] = severity
        event['Agent'] = self.agent
        event['Manager'] = socket.getfqdn()
        event.update(kwargs)
        try:
            self.server.sendEvent(event)
        except Exception:
            raise
