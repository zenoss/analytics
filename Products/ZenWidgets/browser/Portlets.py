##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import re
import json

from Products.Five.browser import BrowserView
from Products.AdvancedQuery import Eq, Or

from Products.ZenUtils.Utils import relative_time
from Products.Zuul import getFacade
from Products.ZenEvents.HeartbeatUtils import getHeartbeatObjects
from zenoss.protocols.services import ServiceException
from zenoss.protocols.services.zep import ZepConnectionError
from Products.ZenUtils.guid.interfaces import IGUIDManager
from Products.ZenUtils.jsonutils import json
from Products.ZenUtils.Utils import nocache, formreq, extractPostContent
from Products.ZenWidgets import messaging
from Products.ZenModel.Device import Device
from Products.ZenModel.ZenossSecurity import (
    MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE,
    TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION,
    UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD,
    ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE,
    ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE,
    ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS,
    ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE,
    ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER,
    ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT,
    ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE,
    ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER,
    ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE,
    ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS,
    ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW)
from Products.ZenEvents.browser.EventPillsAndSummaries import \
                                   getDashboardObjectsEventSummary, \
                                   ObjectsEventSummary,    \
                                   getEventPillME

import logging
log = logging.getLogger('zen.portlets')


def zepConnectionError(retval=None):
    def outer(func):
        def inner(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ZepConnectionError, e:
                msg = 'Connection refused. Check zeneventserver status on <a href="/zport/dmd/daemons">Services</a>'
                messaging.IMessageSender(self.context).sendToBrowser("ZEP connection error",
                                                        msg,
                                                        priority=messaging.CRITICAL,
                                                        sticky=True)
                log.warn("Could not connect to ZEP")
            return retval
        return inner
    return outer

class TopLevelOrganizerPortletView(ObjectsEventSummary):
    """
    Return JSON event summaries for a root organizer.
    """
    @nocache
    @formreq
    def __call__(self, dataRoot):
        self.dataRoot = dataRoot
        return super(TopLevelOrganizerPortletView, self).__call__()

    def _getObs(self):
        return self.context.dmd.getDmdRoot(self.dataRoot).children()


class ProductionStatePortletView(BrowserView):
    """
    Return a map of device to production state in a format suitable for a
    YUI data table.
    """
    @nocache
    @formreq
    def __call__(self, *args, **kwargs):
        return self.getDevProdStateJSON(*args, **kwargs)

    @json
    def getDevProdStateJSON(self, prodStates=['Maintenance']):
        """
        Return a map of device to production state in a format suitable for a
        YUI data table.

        @return: A JSON representation of a dictionary describing devices
        @rtype: "{
            'columns':['Device', 'Prod State'],
            'data':[
                {'Device':'<a href=/>', 'Prod State':'Production'},
                {'Device':'<a href=/>', 'Prod State':'Maintenance'},
            ]}"
        """
        devroot = self.context.dmd.Devices
        if isinstance(prodStates, basestring):
            prodStates = [prodStates]
        orderby, orderdir = 'id', 'asc'
        catalog = getattr(devroot, devroot.default_catalog)
        queries = []
        for state in prodStates:
            queries.append(Eq('getProdState', state))
        query = Or(*queries)
        objects = catalog.evalAdvancedQuery(query, ((orderby, orderdir),))
        devs = (x.getObject() for x in objects)
        mydict = {'columns':['Device', 'Prod State'], 'data':[]}
        for dev in devs:
            if not self.context.checkRemotePerm(ZEN_VIEW, dev): continue
            mydict['data'].append({
                'Device' : dev.getPrettyLink(),
                'Prod State' : dev.getProdState()
            })
            if len(mydict['data'])>=100:
                break
        return mydict


class WatchListPortletView(BrowserView):
    """
    Accepts a list of paths to Zope objects which it then attempts to resolve.
    If no list of paths is given, it will try to read them from the POST data
    of the REQUEST object.

    @param entities: A list of paths that should be resolved into objects
        and passed to L{getDashboardObjectsEventSummaryJSON}.
    @type entities: list
    @return: A JSON-formatted string representation of the columns and rows
        of the table
    @rtype: string
    """
    @nocache
    @formreq
    def __call__(self, *args, **kwargs):
        return self.getEntityListEventSummary(*args, **kwargs)

    @json
    def getEntityListEventSummary(self, entities=None):
        if entities is None:
            entities = []
        elif isinstance(entities, basestring):
            entities = [entities]
        def getob(e):
            e = str(e)
            try:
                if not e.startswith('/zport/dmd'):
                    bigdev = '/zport/dmd' + e
                obj = self.context.dmd.unrestrictedTraverse(bigdev)
            except (AttributeError, KeyError):
                obj = self.context.dmd.Devices.findDevice(e)
            if self.context.has_permission("View", obj): return obj
        entities = filter(lambda x:x is not None, map(getob, entities))
        return getDashboardObjectsEventSummary(
            self.context.dmd.ZenEventManager, entities)


class DeviceIssuesPortletView(BrowserView):
    """
    A list of devices with issues.
    """
    @nocache
    def __call__(self):
        return self.getDeviceIssuesJSON()

    @json
    def getDeviceIssuesJSON(self):
        """
        Get devices with issues in a form suitable for a portlet on the
        dashboard.

        @return: A JSON representation of a dictionary describing devices
        @rtype: "{
            'columns':['Device', "Events'],
            'data':[
                {'Device':'<a href=/>', 'Events':'<div/>'},
                {'Device':'<a href=/>', 'Events':'<div/>'},
            ]}"
        """
        mydict = {'columns':[], 'data':[]}
        mydict['columns'] = ['Device', 'Events']
        deviceinfo = self.getDeviceDashboard()
        for alink, pill in deviceinfo:
            mydict['data'].append({'Device':alink,
                                   'Events':pill})
        return mydict

    @zepConnectionError([])
    def getDeviceDashboard(self):
        """return device info for bad device to dashboard"""
        zep = getFacade('zep')
        manager = IGUIDManager(self.context.dmd)
        deviceSeverities = zep.getDeviceIssuesDict()
        zem = self.context.dmd.ZenEventManager

        bulk_data = []

        for uuid in deviceSeverities.keys():
            uuid_data = {}
            uuid_data['uuid'] = uuid
            severities = deviceSeverities[uuid]
            try:
                uuid_data['severities'] = dict((zep.getSeverityName(sev).lower(), counts) for (sev, counts) in severities.iteritems())
            except ServiceException:
                continue
            bulk_data.append(uuid_data)

        bulk_data.sort(key=lambda x:(x['severities']['critical'], x['severities']['error'], x['severities']['warning']), reverse=True)

        devices_found = 0
        MAX_DEVICES = 100

        devdata = []
        for data in bulk_data:
            uuid = data['uuid']
            severities = data['severities']
            dev = manager.getObject(uuid)
            if dev and isinstance(dev, Device):
                if (not zem.checkRemotePerm(ZEN_VIEW, dev)
                    or dev.productionState < zem.prodStateDashboardThresh
                    or dev.priority < zem.priorityDashboardThresh):
                    continue
                alink = dev.getPrettyLink()
                pill = getEventPillME(dev, severities=severities)
                evts = [alink,pill]
                devdata.append(evts)
                devices_found = devices_found + 1
                if devices_found >= MAX_DEVICES:
                    break
        return devdata

heartbeat_columns = ['Host', 'Daemon Process', 'Seconds Down']

class HeartbeatPortletView(BrowserView):
    """
    Heartbeat issues in YUI table form, for the dashboard portlet
    """
    @nocache
    def __call__(self):
        return self.getHeartbeatIssuesJSON()

    @zepConnectionError({'columns': heartbeat_columns, 'data':[]})
    @json
    def getHeartbeatIssuesJSON(self):
        """
        Get heartbeat issues in a form suitable for a portlet on the dashboard.

        @return: A JSON representation of a dictionary describing heartbeats
        @rtype: "{
            'columns':['Host', 'Daemon Process', 'Seconds Down'],
            'data':[
                {'Device':'<a href=/>', 'Daemon':'zenhub', 'Seconds':10}
            ]}"
        """
        data = getHeartbeatObjects(deviceRoot=self.context.dmd.Devices,
                keys=heartbeat_columns)
        return {'columns': heartbeat_columns, 'data': data}


class UserMessagesPortletView(BrowserView):
    """
    User messages in YUI table form, for the dashboard portlet.
    """
    @nocache
    @json
    def __call__(self):
        """
        Get heartbeat issues in a form suitable for a portlet on the dashboard.

        @return: A JSON representation of a dictionary describing heartbeats
        @rtype: "{
            'columns':['Host', 'Daemon Process', 'Seconds Down'],
            'data':[
                {'Device':'<a href=/>', 'Daemon':'zenhub', 'Seconds':10}
            ]}"
        """
        ICONS = ['/zport/dmd/img/agt_action_success-32.png',
                 '/zport/dmd/img/messagebox_warning-32.png',
                 '/zport/dmd/img/agt_stop-32.png']
        msgbox = messaging.IUserMessages(self.context)
        msgs = msgbox.get_messages()
        cols = ['Message']
        res = []
        for msg in msgs:
            res.append(dict(
                title = msg.title,
                imgpath = ICONS[msg.priority],
                body = msg.body,
                ago = relative_time(msg.timestamp),
                deletelink = msg.absolute_url_path() + '/delMsg'
            ))
        res.reverse()
        return { 'columns': cols, 'data': res }
