##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import re
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenossSecurity import ZEN_VIEW

from Products.ZenRelations.RelSchema import ToOne, ToManyCont
from Products.ZenUtils.Utils import prepId
from Products.ZenWidgets import messaging
from Products.ZenModel.WinServiceClass import WinServiceClass
from Service import Service


def manage_addWinService(context, id, description, userCreated=None, 
                         REQUEST=None, newClassName="/WinService/"):
    """
    Create a WinService and add it to context. context should be a 
    device.os.winservices relationship.
    """
    className = re.sub(r'/serviceclasses/.*', r'/', newClassName)
    s = WinService(id)
    # Indexing is subscribed to ObjectAddedEvent, which fires
    # on _setObject, so we want to set service class first.
    args = {'name':id, 'description':description, 'newClassName':className}
    s.__of__(context).setServiceClass(args)
    context._setObject(id, s)
    s = context._getOb(id)
    s.serviceName = id
    s.caption = description
    if userCreated: s.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                  +'/manage_main')
    return s


class WinService(Service):
    """Windows Service Class
    """
    portal_type = meta_type = 'WinService'

    serviceName = ""
    caption = ""
    pathName = ""
    serviceType = ""
    startMode = ""
    startName = ""
    monitoredStartModes = []
    collectors = ('zenwin',)

    _properties = Service._properties + (
        {'id': 'serviceName', 'type':'string', 'mode':'w'},
        {'id': 'caption', 'type':'string', 'mode':'w'},
        {'id': 'pathName', 'type':'string', 'mode':'w'},
        {'id': 'serviceType', 'type':'string', 'mode':'w'},
        {'id': 'startMode', 'type':'string', 'mode':'w'},
        {'id': 'startName', 'type':'string', 'mode':'w'},
        {'id': 'monitoredStartModes', 'type':'lines', 'mode':'w'},
    )

    _relations = Service._relations + (
        ("os", ToOne(ToManyCont, "Products.ZenModel.OperatingSystem", "winservices")),
    )

    factory_type_information = (
        {
            'immediate_view' : 'winServiceDetail',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'winServiceDetail'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'winServiceManage'
                , 'permissions'   : ("Manage DMD",)
                },
            )
         },
        )

    security = ClassSecurityInfo()


    def getInstDescription(self):
        """Return some text that describes this component.  Default is name.
        """
        return "'%s' StartMode:%s StartName:%s" % (self.caption,
                        self.startMode, self.startName)


    def getMonitoredStartModes(self):
        if self.monitoredStartModes:
            return self.monitoredStartModes
        return self.serviceclass().monitoredStartModes


    def getStatus(self, statClass=None):
        """
        Return the status number for this WinService
        """
        if self.startMode not in self.getMonitoredStartModes():
            return -1
        return Service.getStatus(self, statClass)


    def getServiceClass(self):
        """Return a dict like one set by zenwinmodeler for services.
        """
        desc = self.description
        if not desc:
            svccl = self.serviceclass()
            if svccl: desc = svccl.description
        return {'name': self.serviceName, 'description': self.caption }


    def setServiceClass(self, kwargs):
        """Set the service class where name=ServiceName and description=Caption.
        """
        self.serviceName = kwargs['name']
        self.caption = kwargs['description']
        path = kwargs.get('newClassName')
        if not path:
            path = '/WinService/'
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(
            name=self.serviceName, description=self.caption, path=path, factory=WinServiceClass)
        self.serviceclass.addRelation(srvclass)


    def name(self):
        """Return the name of this service.
        """
        return self.serviceName

    def getCaption(self):
        return self.caption
    primarySortKey = getCaption

    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self, id=None, description=None, 
                            pathName=None, serviceType=None,
                            startMode=None, startName=None,
                            monitoredStartModes=[],
                            monitor=False, severity=5, 
                            REQUEST=None):
        """Edit a Service from a web page.
        """
        msg = []
        renamed = False
        if id is not None:
            self.serviceName = id
            self.description = description
            self.caption = description
            self.pathName = pathName
            self.serviceType = serviceType
            self.startMode = startMode
            self.startName = startName

            if self.id != id:
                id = prepId(id)
                self.setServiceClass(dict(name=id, description=description))
                renamed = self.rename(id)

        if set(monitoredStartModes) != set(self.getMonitoredStartModes()):
            self.monitoredStartModes = monitoredStartModes
            msg.append("Updated monitored start modes")

        tmpl = super(WinService, self).manage_editService(
            monitor, severity, msg=msg, REQUEST=REQUEST)
        if REQUEST and renamed:
            messaging.IMessageSender(self).sendToBrowser(
                'Service Renamed',
                "Object renamed to: %s" % self.id
            )
            return self.callZenScreen(REQUEST, renamed)
        return tmpl

InitializeClass(WinService)
