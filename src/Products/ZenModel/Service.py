##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""Service.py

Service is a function provided by computer (like a server).  it
is defined by a protocol type (udp/tcp) and a port number.

"""

from Acquisition import aq_chain
from AccessControl import ClassSecurityInfo
from Commandable import Commandable

from Products.ZenRelations.RelSchema import ToOne, ToMany, ToManyCont
from Products.ZenWidgets import messaging

from EventView import EventView
from OSComponent import OSComponent
from ZenPackable import ZenPackable

class Service(OSComponent, Commandable, ZenPackable):
    """
    Service class
    """
    portal_type = meta_type = 'Service'

    _relations = OSComponent._relations + ZenPackable._relations + (
        ("serviceclass", ToOne(ToMany,"Products.ZenModel.ServiceClass","instances")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        )

    security = ClassSecurityInfo()

    def key(self):
        """
        Return tuple (manageIp, name) for this service to uniquely id it.
        """
        return (self.getManageIp(), self.name())

    def name(self):
        """
        Return the name of this service. (short name for net stop/start).
        """
        svccl = self.serviceclass()
        if svccl: return svccl.name
        return ""

    title = name

    def monitored(self):
        """
        Should this service be monitored or not. Use ServiceClass aq path.
        """
        return self.monitor and self.getAqProperty("zMonitor")


    def isMonitored(self):
        """
        Returns the same as "monitored" but from the catalog instead of from
        the service class.
        """
        try:
            index_dict = self.primaryAq().componentSearch.getIndexDataForUID(
                self.getPrimaryId())
        except KeyError:
            return self.monitored()

        return bool(index_dict.get('monitored', self.monitored()))


    def getStatus(self, statClass=None):
        """
        Return the status number for this component of class statClass.
        """
        if not self.isMonitored() \
            or not self.device() \
            or not self.device().monitorDevice(): return -1
        if not statClass: statClass = "/Status/%s" % self.meta_type
        return EventView.getStatus(self, statClass)

    def getSeverities(self):
        """
        Return a list of tuples with the possible severities
        """
        return self.ZenEventManager.getSeverities()


    def getFailSeverity(self):
        """
        Return the severity for this service when it fails.
        """
        return self.getAqProperty("zFailSeverity")


    def getFailSeverityString(self):
        """
        Return a string representation of zFailSeverity
        """
        return self.ZenEventManager.severities[self.getAqProperty("zFailSeverity")]


    def setServiceClass(self, kwargs):
        """
        Set the service class based on a dict describing the service.
        Dict keys are be protocol and port
        """
        name = kwargs['name']
        description = kwargs['description']
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(name=name, description=description)
        self.serviceclass.addRelation(srvclass)


    def getServiceClassLink(self):
        """
        Return an a link to the service class.
        """
        svccl = self.serviceclass()
        if svccl:
            if self.checkRemotePerm("View", svccl):
                return "<a href='%s'>%s</a>" % (svccl.getPrimaryUrlPath(),
                                                svccl.getServiceClassName())
            else:
                return svccl.getServiceClassName()
        return ""


    def getClassObject(self):
        """
        Return the ServiceClass for this service.
        """
        return self.serviceclass()


    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self,monitor=False,severity=5,msg=None,REQUEST=None):
        """
        Edit a Service from a web page.
        """
        if msg is None: msg=[]
        msg.append(self.setAqProperty("zMonitor", monitor, "boolean"))
        msg.append(self.setAqProperty("zFailSeverity", severity, "int"))
        msg = [ m for m in msg if m ]
        self.index_object()
        if not msg: msg.append("No action needed")
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Service Edited',
                ", ".join(msg)
            )
            return self.callZenScreen(REQUEST, redirect=True)


    def getUserCommandTargets(self):
        '''
        Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return [self]


    def getUserCommandEnvironment(self):
        """
        Return the environment to be used when processing a UserCommand
        """
        environ = Commandable.getUserCommandEnvironment(self)
        context = self.primaryAq()
        environ.update({'serv': context,  'service': context,})
        return environ


    def getAqChainForUserCommands(self):
        """
        Setup the aq chain as appropriate for the execution of a UserCommand
        """
        chain = aq_chain(self.getClassObject().primaryAq())
        chain.insert(0, self)
        return chain


    def getUrlForUserCommands(self):
        """
        Return the url where UserCommands are viewed for this object
        """
        return self.getPrimaryUrlPath() + '/serviceManage'
