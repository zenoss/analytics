##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger('zen.actioninfos')

from zope.interface import implements, implementsOnly

from Products.Zuul.infos import InfoBase
from Products.Zuul.interfaces.actions import (
    IEmailActionContentInfo, IPageActionContentInfo,
    ICommandActionContentInfo, ISnmpTrapActionContentInfo,
    ISyslogActionContentInfo, ISNMPv3ActionContentInfo
)
from zope.schema.fieldproperty import FieldProperty

_marker = object()

class ActionFieldProperty(FieldProperty):
    """
    We store action content properties in a container on the NotificationSubscription.
    This class will act mostly like a FieldProperty - it is extended because we
    have to proxy the property request into the content property on the object
    that's been adapted into an IInfo object. The __init__ signature is different
    than that of a FieldProperty for convenience.
    """
    def __init__(self, interfaceKlass, name):
        self.__field = interfaceKlass[name]
        self.__name = name

    def __get__(self, inst, klass):
        if inst is None:
            return self

        value = inst.__dict__.get('_object').content.get(self.__name, _marker)
        if value is _marker:
            field = self.__field.bind(inst)
            value = getattr(field, 'default', _marker)
            if value is _marker:
                raise AttributeError(self.__name)
        return value

    def __set__(self, inst, value):
        field = self.__field.bind(inst)
        field.validate(value)
        if field.readonly and self.__name in inst.__dict__.get('_object').content:
            raise ValueError(self.__name, 'field is readonly')
        inst.__dict__.get('_object').content[self.__name] = value

    def __getattr__(self, name):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return getattr(self.__field, name)


class ActionContentInfo(InfoBase):
    """
    Marker interface
    """
    pass

class EmailActionContentInfo(ActionContentInfo):
    implements(IEmailActionContentInfo)

    body_content_type = ActionFieldProperty(IEmailActionContentInfo, 'body_content_type')
    subject_format = ActionFieldProperty(IEmailActionContentInfo,'subject_format')
    body_format = ActionFieldProperty(IEmailActionContentInfo, 'body_format')
    clear_subject_format = ActionFieldProperty(IEmailActionContentInfo, 'clear_subject_format')
    clear_body_format = ActionFieldProperty(IEmailActionContentInfo, 'clear_body_format')
    email_from = ActionFieldProperty(IEmailActionContentInfo, 'email_from')
    skipfails = ActionFieldProperty(IEmailActionContentInfo, 'skipfails')
    host = ActionFieldProperty(IEmailActionContentInfo, 'host')
    port = ActionFieldProperty(IEmailActionContentInfo, 'port')
    useTls = ActionFieldProperty(IEmailActionContentInfo, 'useTls')
    user = ActionFieldProperty(IEmailActionContentInfo, 'user')
    password = ActionFieldProperty(IEmailActionContentInfo, 'password')


class PageActionContentInfo(ActionContentInfo):
    implements(IPageActionContentInfo)

    clear_subject_format = ActionFieldProperty(IPageActionContentInfo, 'clear_subject_format')
    subject_format = ActionFieldProperty(IPageActionContentInfo, 'subject_format')


class CommandActionContentInfo(ActionContentInfo):
    implements(ICommandActionContentInfo)

    action_timeout = ActionFieldProperty(ICommandActionContentInfo, 'action_timeout')
    body_format = ActionFieldProperty(ICommandActionContentInfo, 'body_format')
    clear_body_format = ActionFieldProperty(ICommandActionContentInfo, 'clear_body_format')
    user_env_format = ActionFieldProperty(ICommandActionContentInfo, 'user_env_format')


class SnmpTrapActionContentInfo(ActionContentInfo):
    implements(ISnmpTrapActionContentInfo)

    action_destination = ActionFieldProperty(ISnmpTrapActionContentInfo, 'action_destination')
    community = ActionFieldProperty(ISnmpTrapActionContentInfo, 'community')
    version = ActionFieldProperty(ISnmpTrapActionContentInfo, 'version')
    port = ActionFieldProperty(ISnmpTrapActionContentInfo, 'port')


class SNMPv3ActionContentInfo(SnmpTrapActionContentInfo):
    implementsOnly(ISNMPv3ActionContentInfo)

    securityEngineId = ActionFieldProperty(ISNMPv3ActionContentInfo, 'securityEngineId')
    contextEngineId = ActionFieldProperty(ISNMPv3ActionContentInfo, 'contextEngineId')

    contextName = ActionFieldProperty(ISNMPv3ActionContentInfo, 'contextName')

    authProto = ActionFieldProperty(ISNMPv3ActionContentInfo, 'authProto')
    securityName = ActionFieldProperty(ISNMPv3ActionContentInfo, 'securityName')
    securityPassphrase = ActionFieldProperty(ISNMPv3ActionContentInfo, 'securityPassphrase')
    privProto = ActionFieldProperty(ISNMPv3ActionContentInfo, 'privProto')
    privacyPassphrase = ActionFieldProperty(ISNMPv3ActionContentInfo, 'privacyPassphrase')


class SyslogActionContentInfo(InfoBase):
    implements(ISyslogActionContentInfo)

    host = ActionFieldProperty(ISyslogActionContentInfo, 'host')
    port = ActionFieldProperty(ISyslogActionContentInfo, 'port')
    protocol = ActionFieldProperty(ISyslogActionContentInfo, 'protocol')
    facility = ActionFieldProperty(ISyslogActionContentInfo, 'facility')

