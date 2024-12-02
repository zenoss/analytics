##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.notifications")


from zope.interface import implements
from AccessControl.class_init import InitializeClass
from App.special_dtml import DTMLFile
from AccessControl import ClassSecurityInfo
from AdministrativeRoleable import AdministrativeRoleable
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenossSecurity import *
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable
from Products.ZenUtils.Time import LocalDateTime
from Products.ZenUtils.ZenTales import talesEvalStr, talEval
from Products.ZenEvents.events2.proxy import EventProxy, EventSummaryProxy
from zenoss.protocols.protobufs.zep_pb2 import Event, EventSummary
from zenoss.protocols.jsonformat import from_dict
from zenoss.protocols.wrappers import EventSummaryAdapter
from Products.ZenEvents.EventManagerBase import EventManagerBase

def manage_addNotificationSubscriptionManager(context, REQUEST=None):
    """Create the notification subscription manager."""
    nsm = NotificationSubscriptionManager(NotificationSubscriptionManager.root)
    context._setObject(NotificationSubscriptionManager.root, nsm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')

class NotificationSubscriptionManager(ZenModelRM):
    """Manage notification subscriptions.

    @todo: change the icon parameter in factory_type_information.
    """

    _id = "NotificationSubscriptionManager"
    root = 'NotificationSubscriptions'
    meta_type = _id

    sub_meta_types = ("NotificationSubscription",)

    factory_type_information = (
        {
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Management of notification subscriptions""",
            'icon'           : 'UserSettingsManager.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addNotificationSubscriptionManager',
            'immediate_view' : 'editSettings',
            'actions'        : (
                {
                    'id'            : 'settings',
                    'name'          : 'Settings',
                    'action'        : '../editSettings',
                    'permissions'   : ( ZEN_MANAGE_DMD, )
                })
         },
    )


addNotificationSubscription = DTMLFile('dtml/addNotificationSubscription',globals())

def manage_addNotificationSubscription(context, id, title = None, REQUEST = None):
    """Create a notification subscription"""
    ns = NotificationSubscription(id, title)
    context._setObject(id, ns)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')

class NoneDefaultingDict(dict):
    def __missing__(self, key):
        ret = NoneDefaultingDict()
        self[key] = ret
        return ret

class NotificationEventSummaryProxy(EventSummaryProxy):
    @property
    def severityString(self):
        """
        The old event system used to export 'severityString' as a field to use in notifications.
        """
        try:
            return EventManagerBase.severities[self.severity]
        except KeyError:
            return "Unknown"

    @property
    def component(self):
        """
        Mapping title to component to support unmangled component names.
        """
        return self._event.actor.element_sub_title

    @property
    def componentId(self):
        return self._event.actor.element_sub_identifier

class NotificationEventContextWrapper(NoneDefaultingDict):
    def __init__(self, evtsummary, clearevtsummary=None):
        super(NotificationEventContextWrapper,self).__init__()
        self['evt'] = NotificationEventSummaryProxy(evtsummary)
        self['eventSummary'] = EventSummaryAdapter(evtsummary)
        if clearevtsummary is not None:
            self['clearEvt'] = NotificationEventSummaryProxy(clearevtsummary)
            self['clearEventSummary'] = EventSummaryAdapter(clearevtsummary)
        else:
            self['clearEvt'] = NoneDefaultingDict()
            self['clearEventSummary'] = NoneDefaultingDict()

class NotificationSubscription(ZenModelRM, AdministrativeRoleable):
    """
    A subscription to a signal that produces notifications in the form of
    actions.
    """
    implements(IGloballyIdentifiable)

    _id = "NotificationSubscription"
    meta_type = _id

    enabled = False
    action = 'email'
    send_clear = False

    delay_seconds = 0
    repeat_seconds = 0
    send_initial_occurrence = True

    # recipients is a list of uuids that will recieve the push from this
    # notification. (the User, Group or Role to email/page/etc.)
    # the uuid objects will need to implement some form of actionable target
    # See IAction classes for more info.
    recipients = []

    # a list of trigger uuids that this notification is subscribed to.
    subscriptions = []

    _properties = ZenModelRM._properties + (
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'send_clear', 'type':'boolean', 'mode':'w'},
        {'id':'send_initial_occurrence', 'type':'boolean', 'mode':'w'},
        {'id':'delay_seconds', 'type':'int', 'mode':'w'},
        {'id':'repeat_seconds', 'type':'int', 'mode':'w'},
    )

    _relations = (
        ("adminRoles",
        ToManyCont(
            ToOne,
            "Products.ZenModel.AdministrativeRole",
            "managedObject"
        )), 
        ("windows",
        ToManyCont(
            ToOne,
            "Products.ZenModel.NotificationSubscriptionWindow",
            "notificationSubscription"
        )),
    )

    factory_type_information = (
        {
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Define the notification and the signals to
                which it is subscribed.""",
            # @todo: fix this icon
            'icon'           : 'ActionRule.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addNotificationSubscription',
            'immediate_view' : 'editNotificationSubscription',
            'actions'        :(
                {
                    'id'            : 'edit',
                    'name'          : 'Edit',
                    'action'        : 'editNotificationSubscription',
                    'permissions'   : (ZEN_CHANGE_ALERTING_RULES,)
                }
            )
         },
    )

    security = ClassSecurityInfo()

    def __init__(self, id, title=None, buildRelations=True):
        self.globalRead = False
        self.globalWrite = False
        self.globalManage = False

        self.content = {}
        
        super(ZenModelRM, self).__init__(id, title=title, buildRelations=buildRelations)

    security.declareProtected(ZEN_CHANGE_ALERTING_RULES, 'manage_editNotificationSubscription')
    def manage_editNotificationSubscription(self, REQUEST=None):
        """Update notification subscription properties"""
        return self.zmanage_editProperties(REQUEST)

    def isActive(self):
        """
        Using maintenance windows and `enabled`, determine if this notification
        is active for right now.
        """
        if self.enabled:
            log.debug('Notification is enabled: %s', self.id)
            windows = self.windows()
            if windows:
                log.debug('Notification has (%s) windows.', len(windows))

                enabled_windows = []
                for window in windows:
                    if window.enabled:
                        log.debug('Notification has enabled window: %s', window.id)
                        enabled_windows.append(window)

                if enabled_windows:
                    for window in enabled_windows:
                        if window.isActive():
                            log.debug('Window is active: %s', window.id)
                            return True

                    # there are windows that are enabled, but none of them are
                    # active. This notification isn't active.
                    return False

                # If there are no enabled windows, defer to the notification's
                # enabled setting
                return True
            else:
                log.debug('Notification is enabled, but has no windows, it is active.')
                return True
        else:
            log.debug('Notification NOT enabled: %s', self.id)
            return False

InitializeClass(NotificationSubscriptionManager)
InitializeClass(NotificationSubscription)
