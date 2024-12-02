##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from AccessControl import AuthEncoding
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from BTrees.OOBTree import OOBTree
from DateTime import DateTime
from OFS.Folder import Folder
from exceptions import Exception

from Products.CMFCore.utils import getToolByName
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces.plugins import (IAnonymousUserFactoryPlugin,
                                                            IAuthenticationPlugin)

from Products.PluggableAuthService.permissions import ManageUsers
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements

import logging

log = logging.getLogger('AccountLocker')

TOOL = 'AccountLocker'
PLUGIN_ID = 'account_locker_plugin'
PLUGIN_TITLE = 'Lock an account after numerous failed login attempts'

class Locked(Exception):
    pass


manage_addAccountLockerForm = PageTemplateFile(
    'www/accountLockerAdd',
    globals(),
    __name__='manage_addAccountLockerForm')


def manage_addAccountLocker(context, id, title=None, REQUEST=None):

    obj = AccountLocker(id, title)
    context._setObject(obj.getId(), obj)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')


class AccountLocker(Folder, BasePlugin):

    """
    """

    meta_type = 'Account Locker plugin'
    security = ClassSecurityInfo()

    _properties = (
        {'id': 'title',
         'label': 'Title',
         'type': 'string',
         'mode': 'w',
         },
        {'id': '_max_attempts',
         'label': 'Number of Allowed Attempts',
         'type': 'int',
         'mode': 'w',
         },
        {'id': '_reset_period',
         'label': 'Attempt Reset Period (seconds)',
         'type': 'int',
         'mode': 'w',
        }
      
    )

    def __init__(self, id, title=None):
        self._id = self.id = id
        self.title = title
        self._login_attempts = OOBTree()
        self._max_attempts = 3
        self._reset_period = 300 #seconds


    def remote_ip(self):
        ip = self.REQUEST.get('HTTP_X_FORWARDED_FOR', '')
        if not ip:
            ip = self.REQUEST.get('REMOTE_ADDR', '')
        return ip


    def authenticateCredentials(self, credentials):
        """
        It runs as a first plugin from all IAuthenticationPlugin we have installed, if 
        account is locked raises exception to stop authentication for the rest authenticators we have. 
        If last failed attempt 
        """
        request = self.REQUEST
        response = request['RESPONSE']
        pas_instance = self._getPAS()

        login = credentials.get('login')
        password = credentials.get('password')

        if None in (login, password, pas_instance):
            return None

        is_locked, last_attempt =  self.isLocked(login)
        if is_locked:              
            delta = DateTime().asdatetime() - last_attempt.asdatetime()
            if delta.seconds > self.getResetPeriod():
                self.resetAttempts(login)
            else:
                remaining = self.getResetPeriod() - delta.seconds
                msg = "Account is locked due to" \
                       " numerous failed attempts, please contact your administrator" \
                       " or try again in {0} seconds".format(remaining)

                request.SESSION['locked_message'] = msg 
                raise Locked
        
        request.set('attempted_logins', (login, password))

        return None

    
    security.declarePrivate('createAnonymousUser')
    def createAnonymousUser(self):
        """ 
         If it runs then autheticated failed, look IAnonymousUserFactoryPlugin. 
        """
        
        login, password = self.REQUEST.get('attempted_logins', ('', ''))
        #Whitelisted failed authentications for /authorization/login URL
        #as it has public.premissions and accessible for anonymous users 
        #see ZEN-27450
        if login and '/authorization/login' not in self.REQUEST['PATH_INFO']:
            self.setAttempt(login, password)
            log.info("Failed login attempt: %s ", login)


    def getRootPlugin(self):
        pas = self.getPhysicalRoot().acl_users
        plugins = pas.objectValues([self.meta_type])
        if plugins:
            return plugins[0]


    security.declarePrivate('setAttempt')
    def setAttempt(self, login, password):
        """
         Set counter to 1 or bump it when authentication failed, if previous failed 
         attempt was more than reset period time instead of bumping counter reset it to 1
        """

        root = self.getRootPlugin()
        count, last, IP, reference = root._login_attempts.get(
            login, (0, None, '', None))

        if reference and AuthEncoding.pw_validate(reference, password):
            # don't count repeating same password
            return
        if last:
            delta = DateTime().asdatetime() - last.asdatetime()
            if delta.seconds > self.getResetPeriod():
                # set counter to 1 instead of bumping, some sort of autoreset. 
                count = 1
            else:
                count += 1
        
        else:
            count += 1
        IP = self.remote_ip()
        log.debug("user '%s' failed to login, attempt #%i %s last: %s", login, count, IP, last)
        last = DateTime()
        reference = AuthEncoding.pw_encrypt(password)
        root._login_attempts[login] = (count, last, IP, reference)


    security.declarePrivate('getAttempts')
    def getAttempts(self, login):
        """
         Get attempts for particular account.       
        """
        root = self.getRootPlugin()
        count, last, IP, pw_hash = root._login_attempts.get(
            login, (0, None, '', ''))
        return count, last, IP


    def getResetPeriod(self):
         reset_period = getattr(self, '_reset_period', 300) #seconds
         return reset_period


    def getMaxAttempts(self):
        attempts = getattr(self, '_max_attempts', 3)
        return attempts


    security.declarePrivate('isLocked')
    def isLocked(self, login):
        """
         Check if particular account is locked.
        """
        root = self.getRootPlugin()
        count, last, IP = root.getAttempts(login)
        return (count >= root.getMaxAttempts(), last)


    def resetAttempts(self, login, password=None):
        """
         Reset attempts for particular account
        """
        root = self.getRootPlugin()
        if root._login_attempts.get(login, None):
            del root._login_attempts[login]


    #
    #   ZMI
    #
    manage_options = (
        (
            {'label': 'Users',
                'action': 'manage_users', },
        )
        + BasePlugin.manage_options[:1]
        + Folder.manage_options[:1]
        + Folder.manage_options[2:]
    )


    security.declareProtected(ManageUsers, 'manage_users')
    manage_users = PageTemplateFile(
        'www/manageLockouts', globals(), __name__='manage_users')


    security.declareProtected(ManageUsers, 'manage_resetUsers')
    def manage_resetUsers(self, logins, RESPONSE=None):
        """
        """
        for login in logins:
            self.resetAttempts(login)
        message = "User reset"
        if RESPONSE is not None:
            RESPONSE.redirect(
                '%s/manage_users?manage_tabs_message=%s' % (
                    self.absolute_url(), message)
            )

    
    security.declareProtected(ManageUsers, 'getAttemptInfo')
    def getAttemptInfo(self, login):
        """
        """
        count, last, IP = self.getAttempts(login)
        return {
            'login': login,
            'last': last,
            'IP': IP,
            'count': count
        }


    security.declareProtected(ManageUsers, 'listAttempts')
    def listAttempts(self):
        root = self.getRootPlugin()
        return [self.getAttemptInfo(x) for x in root._login_attempts.keys()]


    security.declareProtected(ManageUsers, 'resetAllAccounts')
    def resetAllAccounts(self):
         root = self.getRootPlugin()
         root._login_attempts.clear()


classImplements(AccountLocker,
                IAuthenticationPlugin,
                IAnonymousUserFactoryPlugin
                )


InitializeClass(AccountLocker)

def setup(context):

    def activatePluginForInterfaces(pas, plugin, selected_interfaces):
        plugin_obj = pas[plugin]
        activatable = []
        for info in plugin_obj.plugins.listPluginTypeInfo():
            interface = info['interface']
            interface_name = info['id']
            if plugin_obj.testImplements(interface) and \
                    interface_name in selected_interfaces:
                    activatable.append(interface_name)

        plugin_obj.manage_activateInterfaces(activatable)


    def movePluginToTop(pas, plugin_id, interface_name):
        plugin_registry = pas.plugins
        interface = plugin_registry._getInterfaceFromName(interface_name)
        while plugin_registry.listPlugins(interface)[0][0] != plugin_id:
            plugin_registry.movePluginsUp(interface, [plugin_id])


    app = context.getPhysicalRoot()
    zport = app.zport
    
    app_acl = getToolByName(app, 'acl_users')
    zport_acl = getToolByName(zport, 'acl_users')

    if hasattr(app_acl, 'account_locker_plugin'):
        return

    context_interfaces = {app_acl:('IAuthenticationPlugin', 'IAnonymousUserFactoryPlugin'),
                zport_acl:('IAuthenticationPlugin',)}

    for context in context_interfaces:
        manage_addAccountLocker(context, PLUGIN_ID, PLUGIN_TITLE)

    for context, interfaces in context_interfaces.iteritems():
        activatePluginForInterfaces(context, PLUGIN_ID, interfaces)

    for context in context_interfaces:
        movePluginToTop(context, PLUGIN_ID, 'IAuthenticationPlugin')

