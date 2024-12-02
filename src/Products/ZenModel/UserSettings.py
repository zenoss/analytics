##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from DateTime import DateTime
from random import choice
from email.MIMEText import MIMEText
import socket
import logging
import re
log = logging.getLogger("zen.UserSettings")

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from Acquisition import aq_base
from Products.PluggableAuthService import interfaces
from Products.PluggableAuthService.PluggableAuthService \
    import _SWALLOWABLE_PLUGIN_EXCEPTIONS
from zExceptions import Unauthorized

from Products.ZenEvents.ActionRule import ActionRule
from Products.ZenEvents.CustomEventView import CustomEventView
from Products.ZenRelations.RelSchema import ToManyCont, ToOne, ToMany
from Products.ZenUtils import Time
from Products.ZenUtils.Utils import unused, prepId
from Products.ZenUtils.guid.interfaces import IGUIDManager
from Products.ZenUtils import DotNetCommunication
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable, IGlobalIdentifier
from Products.ZenUtils.csrf import validate_csrf_token
from Products.ZenWidgets import messaging
from Products.ZenModel.interfaces import IProvidesEmailAddresses, IProvidesPagerAddresses
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.deprecated import deprecated

from ZenossSecurity import (
   ZEN_MANAGE_DMD, ZEN_CHANGE_SETTINGS, ZEN_CHANGE_ADMIN_OBJECTS,
   ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_EVENT_VIEWS,
)
from ZenModelRM import ZenModelRM
from Products.ZenUtils import Utils
from zope.interface import implements

PASSWD_COMPLEXITY = "(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}"

class LocalAndLDAPUserEntries(Exception): pass

UserSettingsId = "ZenUsers"

def manage_addUserSettingsManager(context, REQUEST=None):
    """Create user settings manager."""
    ufm = UserSettingsManager(UserSettingsId)
    context._setObject(ufm.getId(), ufm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')


def rolefilter(r): return r not in ("Anonymous", "Authenticated", "Owner")


class UserSettingsManager(ZenModelRM):
    """Manage zenoss user folders.
    """
    security = ClassSecurityInfo()

    meta_type = "UserSettingsManager"

    #zPrimaryBasePath = ("", "zport")

    sub_meta_types = ("UserSettings",)

    factory_type_information = (
        {
            'id'             : 'UserSettingsManager',
            'meta_type'      : 'UserSettingsManager',
            'description'    : """Base class for all devices""",
            'icon'           : 'UserSettingsManager.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addUserSettingsManager',
            'immediate_view' : 'manageUserFolder',
            'actions'        :
         (
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : '../editSettings'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Commands'
                , 'action'        : '../dataRootManage'
                , 'permissions'   : (ZEN_MANAGE_DMD,)
                },
                { 'id'            : 'users'
                , 'name'          : 'Users'
                , 'action'        : 'manageUserFolder'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : '../ZenPackManager/viewZenPacks'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'portlets'
                , 'name'          : 'Portlets'
                , 'action'        : '../editPortletPerms'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : '../../About/zenossVersions'
                , 'permissions'   : ( ZEN_MANAGE_DMD, )
                },
                { 'id'            : 'eventConfig'
                , 'name'          : 'Events'
                , 'action'        : 'eventConfig'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'userInterfaceConfig'
                , 'name'          : 'User Interface'
                , 'action'        : '../userInterfaceConfig'
                , 'permissions'   : ( "Manage DMD", )
                },
           )
         },
        )


    def getAllUserSettings(self):
        """Return list user settings objects.
        """
        # This code used to filter out the admin user.
        # See ticket #1615 for why it no longer does.
        return sorted(self.objectValues(spec="UserSettings"),
                    key=lambda a: a.id)

    def getAllGroupSettings(self):
        """Return list group settings objects.
        """
        return sorted(self.objectValues(spec="GroupSettings"),
                    key=lambda a: a.id)

    def getAllUserSettingsNames(self, filtNames=()):
        """Return list of all zenoss usernames.
        """
        filtNames = set(filtNames)
        return [ u.id for u in self.getAllUserSettings()
                    if u.id not in filtNames ]

    def getAllGroupSettingsNames(self, filtNames=()):
        """Return list of all zenoss groupnames.
        """
        filtNames = set(filtNames)
        return [ g.id for g in self.getAllGroupSettings()
                    if g.id not in filtNames ]

    def getUsers(self):
        """Return list of Users wrapped in their settings folder.
        """
        users = []
        for uset in self.objectValues(spec="UserSettings"):
            user = self.acl_users.getUser(uset.id)
            if user: users.append(user.__of__(uset))
        return users


    def getUser(self, userid=None):
        """Return a user object.  If userid is not passed return current user.
        """
        if userid is None:
            user = getSecurityManager().getUser()
        else:
            user = self.acl_users.getUser(userid)
        if user: return user.__of__(self.acl_users)


    def getAllActionRules(self):
        for u in self.getAllUserSettings() + self.getAllGroupSettings():
            for ar in u.getActionRules():
                yield ar

    def getUserSettings(self, userid=None):
        """Return a user folder.  If userid is not passed return current user.
        """
        user=None
        if userid is None:
            user = getSecurityManager().getUser()
            userid = user.getId()
        if not userid: raise Unauthorized
        folder = self._getOb(userid,None)
        if not folder and userid:
            userid = str(userid)
            ufolder = UserSettings(userid)
            self._setObject(ufolder.getId(), ufolder)
            folder = self._getOb(userid)
            if not user:
                user = self.getUser(userid)
            if user:
                # Load default values from our auth backend
                psheets = user.listPropertysheets()
                psheets.reverse() # Because first sheet should have priority
                for ps in map(lambda ps: user.getPropertysheet(ps), psheets):
                    props = {}
                    for id in ps.propertyIds():
                        props[id] = ps.getProperty(id)
                    ufolder.updatePropsFromDict(props)
                folder.changeOwnership(user)
                folder.manage_setLocalRoles(userid, ("Owner",))
        return folder


    def getGroupSettings(self, groupid):
        groupid = prepId(groupid)
        if not self._getOb(groupid, False):
            gfolder = GroupSettings(groupid)
            self._setObject(gfolder.getId(), gfolder)
        return self._getOb(groupid)


    def setDashboardState(self, userid=None, REQUEST=None):
        """ Store a user's portlets and layout. If userid is not passed
            set the state for the current user.
        """
        # Return False in case we are trying to set dashboard state
        # for a user which doesn't exist.
        if userid and userid not in self.getAllUserSettingsNames():
            return False
        user = self.getUserSettings(userid)
        posted = Utils.extractPostContent(REQUEST)
        if posted:
            user.dashboardState = posted
            if REQUEST:
                audit('UI.Dashboard.Edit', username=userid)
        return True

    def getUserSettingsUrl(self, userid=None):
        """Return the url to the current user's folder.
        """
        uf = self.getUserSettings(userid)
        if uf: return uf.getPrimaryUrlPath()
        return ""


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addUser')
    @validate_csrf_token
    def manage_addUser(self, userid, password=None,roles=("ZenUser",),
                    REQUEST=None,**kw):
        """
        Add a Zenoss user to the system and set the user's default properties.

        @parameter userid: username to add
        @parameter password: password for the username
        @parameter roles: tuple of role names
        @parameter REQUEST: Zope object containing details about this request
        """
        if not userid: return

        userid= userid.strip()

        illegal_usernames= [ 'user', ]

        user_name= userid.lower()
        if user_name in illegal_usernames:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'The username "%s" is reserved.' % userid,
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return None

        if password is None:
            password = self.generatePassword()

        self.acl_users._doAddUser(userid,password,roles,"")
        user = self.acl_users.getUser(userid)
        ufolder = self.getUserSettings(userid)
        if REQUEST: kw = REQUEST.form
        ufolder.updatePropsFromDict(kw)

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'User Added',
                'User "%s" has been created.' % userid
            )
            audit('UI.User.Add', username=userid, roles=roles)  # don't send password
            return self.callZenScreen(REQUEST)
        else:
            return user


    def generatePassword(self):
        """ Generate a valid password.
        """
        # we don't use these to avoid typos: OQ0Il1
        chars = 'ABCDEFGHJKLMNPRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
        return ''.join(choice(chars) for i in range(6))


    def authenticateCredentials(self, login, password):
        """
        Authenticates a given set of credentials against all configured
        authentication plugins. Returns True for successful authentication and
        False otherwise.
        """
        if login == 'admin':
            acl_users = self.getPhysicalRoot().acl_users
        else:
            acl_users = self.acl_users

        try:
            authenticators = acl_users.plugins.listPlugins(
                interfaces.plugins.IAuthenticationPlugin)
        except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
            authenticators = ()

        # try each authenticator until a non-None user_id is returned
        for authenticator_id, auth in authenticators:
            try:
                uid_and_info = auth.authenticateCredentials(
                    {'login':login, 'password':password})

                if isinstance(uid_and_info, tuple):
                    # make sure tuple has enough values to unpack
                    user_id, info = (uid_and_info + (None,None))[:2]

                    # return if authentication was a success
                    if user_id is not None:
                        return True

            except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
                pass

        # indicate no successful authentications
        return False


    security.declarePrivate('manage_changeUser')
    def manage_changeUser(self, userid, password=None, sndpassword=None,
                          roles=None, domains=None, REQUEST=None, **kw):
        """Change a zenoss users settings.
        """
        user = self.acl_users.getUser(userid)
        if not user:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'User "%s" was not found.' % userid,
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return
        if password and password != sndpassword:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    "Passwords didn't match. No change.",
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                raise ValueError("passwords don't match")
        if REQUEST:
            # TODO: Record all the non-password values.
            #updates = dict((k,v) for k,v in kw.items() if 'password' not in k.lower())
            updates = {}
            if password: updates['password'] = '****'
            if roles: updates['roles': roles]
            if domains: updates['domains': domains]
        if password is None: password = user._getPassword()
        if roles is None: roles = user.roles
        if domains is None: domains = user.domains
        self.acl_users._doChangeUser(userid,password,roles,domains)
        ufolder = self.getUserSettings(userid)
        ufolder.updatePropsFromDict(kw)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Settings Saved',
                "Saved At: %s" % self.getCurrentUserNowString()
            )
            audit('UI.User.Edit', username=userid, data_=updates)
            return self.callZenScreen(REQUEST)
        else:
            return user


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteUsers')
    @validate_csrf_token
    def manage_deleteUsers(self, userids=(), REQUEST=None):
        """Delete a list of zenoss users from the system.
        """
        # get a list of plugins that can add manage users and then call the
        # appropriate methods
        #
        # XXX this needs to be reviewed when new plugins are added, such as the
        # LDAP plugin
        if 'admin' in userids or 'zenoss_system' in userids:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                "Cannot delete admin or zenoss_system user. No users were deleted.",
                messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        ifaces = [interfaces.plugins.IUserAdderPlugin]
        getPlugins = self.acl_users.plugins.listPlugins
        plugins = [ getPlugins(x)[0][1] for x in ifaces ]
        for userid in userids:
            # must remove the users from the group
            # before removing them from the plugins otherwise
            # their relationship will persist as a broken user
            if getattr(aq_base(self), userid, False):
                ufolder = self.getUserSettings(userid)
                for groupId in ufolder.getUserGroupSettingsNames():
                    group = self.getGroupSettings(groupId)
                    try:
                        group.manage_deleteUserFromGroup(userid)
                    except KeyError:
                        # they have an ldap mapping and we can't remove them from the group
                        pass
            try:
                for plugin in plugins:
                    plugin.removeUser(userid)
            except KeyError:
                # this means that there's no user in the acl_users, but that
                # Zenoss still sees the user; we want to pass on this exception
                # so that Zenoss can clean up
                pass
            if getattr(aq_base(self), userid, False):
                us = self._getOb(userid)
                us.removeAdminRoles()
                for ar in us.adminRoles():
                    ar.userSetting.removeRelation()
                    mobj = ar.managedObject().primaryAq()
                    mobj.adminRoles._delObject(ar.id)
                self._delObject(userid)

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Users Deleted',
                "Users were deleted: %s." % (', '.join(userids))
            )
            for userid in userids:
                audit('UI.User.Delete', username=userid)
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addGroup')
    @validate_csrf_token
    def manage_addGroup(self, groupid, REQUEST=None):
        """Add a zenoss group to the system and set its default properties.
        """
        if not groupid: return
        groupid = prepId(groupid)
        try:
            self.acl_users.groupManager.addGroup(groupid)
        except KeyError: pass
        self.getGroupSettings(groupid)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Group Added',
                'Group "%s" has been created.' % groupid
            )
            audit('UI.Group.Add', groupid)
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteGroups')
    @validate_csrf_token
    def manage_deleteGroups(self, groupids=(), REQUEST=None):
        """ Delete a zenoss group from the system
        """
        gm = self.acl_users.groupManager
        if isinstance(groupids, basestring):
            groupids = [groupids]
        for groupid in groupids:
            if self._getOb(groupid):
                group = self._getOb(groupid)
                group.removeAdminRoles()
                self._delObject(groupid)
            try:
                gm.removeGroup(groupid)
            except KeyError: pass
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Groups Deleted',
                "Groups were deleted: %s." % (', '.join(groupids))
            )
            for groupid in groupids:
                audit('UI.Group.Delete', groupid)
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addUsersToGroups')
    @validate_csrf_token
    def manage_addUsersToGroups(self, userids=(), groupids=(), REQUEST=None):
        """ Add users to a group
        """
        if isinstance(userids, basestring):
            userids = [userids]
        if isinstance(groupids, basestring):
            groupids = [groupids]
        for groupid in groupids:
            self._getOb(groupid).manage_addUsersToGroup(userids)
        if REQUEST:
            if not groupids:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'No groups were selected.',
                    priority=messaging.WARNING
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    'Groups Modified',
                    'Users %s were added to group %s.' % (
                        ', '.join(userids), ', '.join(groupids))
                )
            for userid in userids:
                for groupid in groupids:
                    audit('UI.User.AddToGroup', username=userid, group=groupid)
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_emailTestAdmin')
    def manage_emailTestAdmin(self, userid, REQUEST=None):
        ''' Do email test for given user
        '''
        userSettings = self.getUserSettings(userid)
        msg = userSettings.manage_emailTest()
        if msg:
            messaging.IMessageSender(self).sendToBrowser('Email Test', msg)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_pagerTestAdmin')
    def manage_pagerTestAdmin(self, userid, REQUEST=None):
        ''' Do pager test for given user
        '''
        userSettings = self.getUserSettings(userid)
        msg = userSettings.manage_pagerTest()
        if msg:
            messaging.IMessageSender(self).sendToBrowser('Pager Test', msg)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'cleanUserFolders')
    def cleanUserFolders(self):
        """Delete orphaned user folders.
        """
        userfolders = self._getOb(UserSettingsId)
        userids = self.acl_users.getUserNames()
        for fid in userfolders.objectIds():
            if fid not in userids:
                userfolders._delObject(fid)

    def getAllRoles(self):
        """Get list of all roles without Anonymous and Authenticated.
        """
        return filter(rolefilter, self.valid_roles())


    def exportXmlHook(self,ofile, ignorerels):
        map(lambda x: x.exportXml(ofile, ignorerels), self.getAllUserSettings())



@validate_csrf_token
def manage_addUserSettings(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = UserSettings(id, title)
    context._setObject(id, dc)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')


addUserSettings = DTMLFile('dtml/addUserSettings',globals())


class UserSettings(ZenModelRM):
    """zenoss user folder has users preferences.
    """
    implements(IProvidesEmailAddresses, IProvidesPagerAddresses, IGloballyIdentifiable)

    meta_type = "UserSettings"

    sub_meta_types = ("ActionRule",)

    email = ""
    pager = ""
    defaultPageSize = 40
    defaultEventPageSize = 30
    defaultAdminRole = "ZenUser"
    oncallStart = 0
    oncallEnd = 0
    escalationMinutes = 0
    dashboardState = ''
    netMapStartObject = ''
    eventConsoleRefresh = True
    zenossNetUser = ''
    zenossNetPassword = ''
    timezone = ''
    dateFormat = ''
    timeFormat = ''

    _properties = ZenModelRM._properties + (
        {'id':'email', 'type':'string', 'mode':'w'},
        {'id':'pager', 'type':'string', 'mode':'w'},
        {'id':'defaultPageSize', 'type':'int', 'mode':'w'},
        {'id':'defaultEventPageSize', 'type':'int', 'mode':'w'},
        {'id':'defaultAdminRole', 'type':'string', 'mode':'w'},
        {'id':'oncallStart', 'type':'int', 'mode':'w'},
        {'id':'oncallEnd', 'type':'int', 'mode':'w'},
        {'id':'escalationMinutes', 'type':'int', 'mode':'w'},
        {'id':'dashboardState', 'type':'string', 'mode':'w'},
        {'id':'netMapStartObject', 'type':'string', 'mode':'w'},
        {'id':'eventConsoleRefresh', 'type':'boolean', 'mode':'w'},
        {'id':'zenossNetUser', 'type':'string', 'mode':'w'},
        {'id':'zenossNetPassword', 'type':'string', 'mode':'w'},
        {'id':'timezone', 'type':'string', 'mode':'w'},
        {'id':'dateFormat', 'type':'string', 'mode':'w'},
        {'id':'timeFormat', 'type':'string', 'mode':'w'},
    )


    _relations =  (
        ("adminRoles", ToMany(ToOne, "Products.ZenModel.AdministrativeRole",
                              "userSetting")),
        ("messages", ToManyCont(ToOne,
            "Products.ZenWidgets.PersistentMessage.PersistentMessage",
            "messageQueue")),
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'immediate_view' : 'editUserSettings',
            'actions'        :
            (
                {'name'         : 'Edit',
                'action'        : 'editUserSettings',
                'permissions'   : (ZEN_CHANGE_SETTINGS,),
                },
                {'name'         : 'Administered Objects',
                'action'        : 'administeredDevices',
                'permissions'   : (ZEN_CHANGE_ADMIN_OBJECTS,)
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def hasNoGlobalRoles(self):
        """This user doesn't have global roles. Used to limit access
        """
        return self.id != 'admin' and len(self.getUserRoles()) == 0

    def getUserRoles(self):
        """Get current roles for this user.
        """
        user = self.getUser(self.id)
        if user:
            # This call will create GroupSettings objects for any externally-
            # sourced groups.
            self.getAllAdminRoles()
            return filter(rolefilter, user.getRoles())
        return []

    def getUserGroupSettingsNames(self):
        """Return group settings objects for user
        """
        user = self.getUser(self.id)
        if user:
            return self.acl_users._getGroupsForPrincipal(user)
        return ()


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'updatePropsFromDict')
    def updatePropsFromDict(self, propdict):
        props = self.propertyIds()
        for k, v in propdict.items():
            if k in props: setattr(self,k,v)


    def iseditable(self):
        """Can the current user edit this settings object.
        """
        currentUser = getSecurityManager().getUser()

        # Managers can edit any users' settings.
        if currentUser.has_role("Manager"):
            return True

        # thisUser can be None if the plugin that created it is inactive.
        thisUser = self.acl_users.getUser(self.id)
        if thisUser is None:
            return False

        # ZenManagers can edit any users' settings except for Managers.
        if currentUser.has_role("ZenManager") \
            and not thisUser.has_role("Manager"):
            return True

        # Users can edit their own settings.
        if thisUser.getUserName() == currentUser.getUserName():
            return True

        return False

    security.declareProtected(ZEN_CHANGE_SETTINGS, 'manage_resetPassword')
    @validate_csrf_token
    def manage_resetPassword(self, REQUEST=None):
        """
        Reset a password.
        """
        email = self.email.strip()
        if not email:
            messaging.IMessageSender(self).sendToBrowser(
                'Password Reset Failed',
                'Cannot send password reset email; user has no'+
                ' email address.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(self.REQUEST)

        curuser = self.getUser().getId()
        if self.id == "admin" and curuser != "admin":
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                '{0} cannot update admin password. Password not updated.'.format(curuser),
                priority=messaging.WARNING
            )
            return self.callZenScreen(self.REQUEST)

        newpw = self.generatePassword()
        body = """
        Your Zenoss password has been reset at %s's request.

        Your new password is: %s
        """ % (self.getUser().getId(), newpw)
        msg = MIMEText(body)
        msg['Subject'] = 'Zenoss Password Reset Request'
        msg['From'] = self.dmd.getEmailFrom()
        msg['To'] = email
        msg['Date'] = DateTime().rfc822()
        result, errorMsg = Utils.sendEmail(msg, self.dmd.smtpHost,
                            self.dmd.smtpPort,
                            self.dmd.smtpUseTLS, self.dmd.smtpUser,
                            self.dmd.smtpPass)
        if result:
            userManager = self.acl_users.userManager
            try:
                userManager.updateUserPassword(self.id, newpw)
            except KeyError:
                self.getPhysicalRoot().acl_users.userManager.updateUserPassword(
                                self.id, newpw)
            messaging.IMessageSender(self).sendToBrowser(
                'Password reset',
                'An email with a new password has been sent.'
            )
            audit('UI.User.ResetPassword', username=self.id)
            loggedInUser = self.REQUEST['AUTHENTICATED_USER']
            # we only want to log out the user if it's *their* password
            # they've changed, not, for example, if the admin user is
            # changing another user's password
            if loggedInUser.getUserName() == self.id:
                self.acl_users.logout(self.REQUEST)
        else:
            messaging.IMessageSender(self).sendToBrowser(
                'Password reset failed',
                'Unable to send password reset email: %s' % errorMsg,
                priority=messaging.WARNING
            )
            audit('UI.User.ResetPassword', username=self.id,
                  errorMsg='Unable to send password reset email: %s' % errorMsg)
        return self.callZenScreen(self.REQUEST)


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'manage_editUserSettings')
    def manage_editUserSettings(self, oldpassword=None, password=None,
                                sndpassword=None, roles=None, groups=None,
                                domains=None, REQUEST=None, **kw):
        """Update user settings.
        """
        # get the user object; return if no user
        user = self.acl_users.getUser(self.id)
        if not user:
            user = self.getPhysicalRoot().acl_users.getUser(self.id)
        if not user:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'User %s not found.' % self.id,
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return

        # update only email and page size if true
        outOfTurnUpdate = False
        # Verify existing password
        curuser = self.getUser().getId()
        if not oldpassword or not self.ZenUsers.authenticateCredentials(curuser, oldpassword):
            if REQUEST:
                reqSettings = REQUEST.form
                if str(self.defaultPageSize) == reqSettings['defaultPageSize'] and \
                    self.email == reqSettings['email']:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        'Confirmation password is empty or invalid. Please'+
                        ' confirm your password for security reasons.',
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                else:
                    outOfTurnUpdate = True
            else:
                raise ValueError("Current password is incorrect.")

        # update role info
        roleManager = self.acl_users.roleManager
        origRoles = filter(rolefilter, user.getRoles())

        if not self.has_role('Manager') and roles and 'Manager' in roles:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'Only Managers can make more Managers.',
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return

        if not self.has_role('Manager') and origRoles and \
            'Manager' in origRoles:

            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'Only Managers can modify other Managers.',
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else:
                return

        # if there's a change, then we need to update
        # TODO: Record all the non-password values.
        #updates = dict((k,v) for k,v in kw.items() if 'password' not in k.lower())
        updates = {}

        # update user roles
        if roles is None:
            roles = ()
        origRolesSet = set(origRoles)
        rolesSet = set(roles)
        if rolesSet != origRolesSet and self.isManager():
            # get roles to remove and then remove them
            removeRoles = origRolesSet - rolesSet
            for role in removeRoles:
                try:
                    roleManager.removeRoleFromPrincipal(role, self.id)
                except KeyError:
                    # User doesn't actually have that role; ignore
                    pass
            # get roles to add and then add them
            addRoles = rolesSet - origRolesSet
            for role in addRoles:
                roleManager.assignRoleToPrincipal(role, self.id)
            updates['roles'] = roles

        # update group info
        if groups is None:
            groups = ()
        groupManager = self.acl_users.groupManager
        origGroupsSet = set(groupManager.getGroupsForPrincipal(user))
        groupsSet = set(groups)
        # if there's a change, then we need to update
        if groupsSet != origGroupsSet and self.isManager():
            # get groups to remove and then remove them
            removeGroups = origGroupsSet - groupsSet
            for groupid in removeGroups:
                groupManager.removePrincipalFromGroup(user.getId(), groupid)
            # get groups to add and then add them
            addGroups = groupsSet - origGroupsSet
            for groupid in addGroups:
                try:
                    groupManager.addPrincipalToGroup(user.getId(), groupid)
                except KeyError:
                    # This can occur if the group came from an external source.
                    pass
            updates['groups'] = groups

        # we're not managing domains right now
        if domains:
            msg = 'Zenoss does not currently manage domains for users.'
            raise NotImplementedError(msg)

        # update Zenoss user folder settings
        if REQUEST:
            kw = REQUEST.form
        if outOfTurnUpdate:
            settings = {}
            for key in ['defaultPageSize', 'email']:
                setting = kw.get(key)
                if setting:
                    settings[key] = setting
            self.manage_changeProperties(**settings)
        else:
            self.manage_changeProperties(**kw)

        # update password info
        userManager = self.acl_users.userManager
        if password:
            if password.find(':') >= 0:
                if REQUEST:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        'Passwords cannot contain a ":". Password not updated.',
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                else:
                    raise ValueError("Passwords cannot contain a ':' ")
            elif not re.match(PASSWD_COMPLEXITY, password):
                if REQUEST:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        'Password must contain 8 or more characters'
                        ' that are of at least one number, and one uppercase and lowercase letter.',
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
            elif password != sndpassword:
                if REQUEST:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        'Passwords did not match. Password not updated.',
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                else:
                    raise ValueError("Passwords don't match")
            elif self.id == "admin" and curuser != "admin":
                if REQUEST:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        '{0} cannot update admin password. Password not updated.'.format(curuser),
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                else:
                    raise ValueError("You cannot update admin password")
            else:
                try:
                    userManager.updateUserPassword(self.id, password)
                    # for admin we need to update both zport.acl_users and app.acl_users since he exists in both
                    if self.id == 'admin':
                        userManager = self.getPhysicalRoot().acl_users.userManager
                        userManager.updateUserPassword(self.id, password)
                    updates['password'] = '****'
                except KeyError:
                    self.getPhysicalRoot().acl_users.userManager.updateUserPassword(
                                    self.id, password)
                if REQUEST:
                    loggedInUser = REQUEST['AUTHENTICATED_USER']
                    # we only want to log out the user if it's *their* password
                    # they've changed, not, for example, if the admin user is
                    # changing another user's password
                    if loggedInUser.getUserName() == self.id:
                        self.acl_users.logout(REQUEST)

        # finish up
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Settings Saved',
                "Saved At: %s" % self.getCurrentUserNowString()
            )
            audit('UI.User.Edit', username=self.id, data_=updates)
            return self.callZenScreen(REQUEST)
        else:
            return user

    security.declareProtected(ZEN_CHANGE_ALERTING_RULES, 'manage_addActionRule')
    @deprecated
    def manage_addActionRule(self, id=None, REQUEST=None):
        """Add an action rule to this object.
        """
        if id:
            ar = ActionRule(id)
            self._setObject(id, ar)
            ar = self._getOb(id)
            user = getSecurityManager().getUser()   # current user
            userid = user.getId()
            if userid != self.id:            # if we are not the current user
                userid = self.id
                user = self.getUser(userid)
                ar.changeOwnership(user)     # make us the owner of it
                ar.manage_setLocalRoles(userid, ("Owner",))
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def getActionRules(self):
        return self.objectValues(spec=ActionRule.meta_type)

    security.declareProtected(ZEN_CHANGE_EVENT_VIEWS,
        'manage_addCustomEventView')
    @deprecated
    def manage_addCustomEventView(self, id=None, REQUEST=None):
        """Add a custom event view to this object.
        """
        if id:
            ar = CustomEventView(id)
            self._setObject(id, ar)
            ar = self._getOb(id)
            user = getSecurityManager().getUser()
            userid = user.getId()
            if userid != self.id:
                userid = self.id
                user = self.getUser(userid)
                ar.changeOwnership(user)
                ar.manage_setLocalRoles(userid, ("Owner",))
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_ADMIN_OBJECTS,
        'manage_addAdministrativeRole')
    @validate_csrf_token
    def manage_addAdministrativeRole(self, name=None, type='device', role=None,
                                     guid=None, uid=None, REQUEST=None):
        "Add a Admin Role to the passed object"
        unused(role)
        mobj = None
        if guid or uid:
            # look up our object by either guid or uid
            if guid:
                manager = IGUIDManager(self.dmd)
                mobj = manager.getObject(guid)
            elif uid:
                mobj = self.unrestrictedTraverse(uid)
        else:
            # use magic to look up our object
            if not name:
                name = REQUEST.deviceName
            if type == 'device':
                mobj =self.getDmdRoot("Devices").findDevice(name)
            else:
                try:
                    root = type.capitalize()+'s'
                    if type == "deviceClass":
                        mobj = self.getDmdRoot("Devices").getOrganizer(name)
                    else:
                        mobj = self.getDmdRoot(root).getOrganizer(name)
                except KeyError: pass
        if not mobj:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    "%s %s not found"%(type.capitalize(),name),
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else: return
        roleNames = [ r.id for r in mobj.adminRoles() ]
        if self.id in roleNames:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    (("Administrative Role for %s %s "
                     "for user %s already exists.") % (type, name, self.id)),
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
            else: return
        mobj.manage_addAdministrativeRole(self.id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Role Added',
                ("Administrative Role for %s %s for user %s added" %
                    (type, name, self.id))
            )
            audit('UI.User.AddAdministrativeRole', username=self.id,
                  data_={mobj.meta_type:mobj.getPrimaryId()})
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_ADMIN_OBJECTS,
        'manage_editAdministrativeRoles')
    @validate_csrf_token
    def manage_editAdministrativeRoles(self, ids=(), role=(), REQUEST=None):
        """Edit list of admin roles."""
        if isinstance(ids, basestring):
            ids = [ids]
            role = [role]
        else:
            ids = list(ids)
        for admin_role in self.adminRoles():
            managed_object = admin_role.managedObject()
            try:
                i = ids.index(managed_object.getPrimaryDmdId())
            except ValueError:
                continue
            managed_object = managed_object.primaryAq()
            managed_object.manage_editAdministrativeRoles(self.id, role[i])

            if REQUEST:
                audit('UI.User.EditAdministrativeRole', username=self.id,
                      data_={
                          managed_object.meta_type:
                              managed_object.getPrimaryId()
                      },
                      role=role[i])
        if REQUEST:
            if ids:
                messaging.IMessageSender(self).sendToBrowser(
                    'Roles Updated',
                    "Administrative roles were updated."
                )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_ADMIN_OBJECTS,
        'manage_deleteAdministrativeRole')
    @validate_csrf_token
    def manage_deleteAdministrativeRole(self, delids=(), REQUEST=None):
        """Delete admin roles of objects."""
        if isinstance(delids, basestring):
            delids = [delids]
        else:
            delids = list(delids)
        for admin_role in self.adminRoles():
            managed_object = admin_role.managedObject()
            if managed_object.getPrimaryDmdId() not in delids:
                continue
            managed_object = managed_object.primaryAq()
            managed_object.manage_deleteAdministrativeRole(self.id)
            if REQUEST:
                audit('UI.User.DeleteAdministrativeRole', username=self.id,
                      data_={
                          managed_object.meta_type:
                              managed_object.getPrimaryId()
                      })
        if REQUEST:
            if delids:
                messaging.IMessageSender(self).sendToBrowser(
                    'Roles Deleted',
                    "Administrative roles were deleted."
                )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'getAllAdminGuids')
    def getAllAdminGuids(self, returnChildrenForRootObj=False):
        """
        Return all guids user has permissions to.
        """
        guids = []
        rootOrganizers = (
                        '/zport/dmd/Devices',
                        '/zport/dmd/Locations',
                        '/zport/dmd/Groups',
                        '/zport/dmd/Systems'
        )
        ars = self.getAllAdminRoles()
        if not returnChildrenForRootObj:
            guids.extend(IGlobalIdentifier(ar.managedObject()).getGUID() for ar in ars)
        else:
            for ar in ars:
                if ar.managedObject().getPrimaryId() in rootOrganizers:
                    guids.extend(IGlobalIdentifier(child).getGUID() for child in ar.managedObject().children())
                else:
                    guids.append(IGlobalIdentifier(ar.managedObject()).getGUID())

        return guids


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'getAllAdminRoles')
    def getAllAdminRoles(self):
        """Return all admin roles for this user and its groups
        """
        ars = self.adminRoles()
        for group in self.getUser().getGroups():
            gs = self.getGroupSettings(group)
            ars.extend(gs.adminRoles())
        return ars


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'manage_emailTest')
    def manage_emailTest(self, REQUEST=None):
        ''' Send a test email to the given userid.
        '''
        destSettings = self.getUserSettings(self.getId())
        destAddresses = destSettings.getEmailAddresses()
        msg = None
        if destAddresses:
            fqdn = self.dmd.zenossHostname
            thisUser = self.getUser()
            srcId = thisUser.getId()
            self.getUserSettings(srcId)
            srcAddress = self.dmd.getEmailFrom()
            # Read body from file probably
            body = ('This is a test message sent by %s' % srcId +
                    ' from the Zenoss installation on %s.' % fqdn)
            emsg = MIMEText(body)
            emsg['Subject'] = 'Zenoss Email Test'
            emsg['From'] = srcAddress
            emsg['To'] = ', '.join(destAddresses)
            emsg['Date'] = DateTime().rfc822()
            result, errorMsg = Utils.sendEmail(emsg, self.dmd.smtpHost,
                                self.dmd.smtpPort,
                                self.dmd.smtpUseTLS, self.dmd.smtpUser,
                                self.dmd.smtpPass)
            if result:
                msg = 'Test email sent to %s' % ', '.join(destAddresses)
            else:
                msg = 'Test failed: %s' % errorMsg
                audit('UI.User.EmailTest', username=self.id,
                  errorMsg=msg)
        else:
            msg = 'Test email not sent, user has no email address.'
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Email Test',
                msg.replace("'", "\\'")
            )
            return self.callZenScreen(REQUEST)
        else:
            return msg


    security.declareProtected(ZEN_CHANGE_SETTINGS, 'manage_pagerTest')
    def manage_pagerTest(self, REQUEST=None):
        ''' Send a test page
        '''
        destSettings = self.getUserSettings(self.getId())
        destPagers = [ x.strip() for x in
            (destSettings.getPagerAddresses() or []) ]
        msg = None
        fqdn = socket.getfqdn()
        srcId = self.getUser().getId()
        testMsg = ('Test sent by %s' % srcId +
                ' from the Zenoss installation on %s.' % fqdn)
        for destPager in destPagers:
            result, errorMsg = Utils.sendPage(destPager, testMsg,
                                    self.dmd.pageCommand)
            if result:
                msg = 'Test page sent to %s' % ', '.join(destPagers)
            else:
                msg = 'Test failed: %s' % errorMsg
                break
        if not destPagers:
            msg = 'Test page not sent, user has no pager number.'
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Pager Test', msg)
            return self.callZenScreen(REQUEST)
        else:
            return msg

    def exportXmlHook(self, ofile, ignorerels):
        """patch to export all user configuration
        """
        for o in self.objectValues():
            if hasattr(aq_base(o), 'exportXml'):
                o.exportXml(ofile, ignorerels)

    def getPagerAddresses(self):
        if self.pager and self.pager.strip():
            return [self.pager.strip()]
        return []

    def getEmailAddresses(self):
        if self.email and self.email.strip():
            return [self.email]
        return []

    def isLoggedInUser(self):
        loggedinUser = self.ZenUsers.getUserSettings()
        return loggedinUser.id == self.id

    def getDotNetSession(self):
        """
        Use the Zenoss.net credentials associated with this user to log in to a
        Zenoss.net session.
        """
        session = DotNetCommunication.getDotNetSession(
                                        self.zenossNetUser,
                                        self.zenossNetPassword)
        return session

    def removeAdminRoles(self):
        """
        Call before deleting a user or group this will
        remove this user/group from the list of admin objects for
        everything that the object administered before. This
        prevents broken relationships
        """
        for role in self.getAllAdminRoles():
            obj = role.managedObject().primaryAq()
            obj.manage_deleteAdministrativeRole(self.id)

class GroupSettings(UserSettings):
    implements(IProvidesEmailAddresses, IProvidesPagerAddresses)
    meta_type = 'GroupSettings'

    factory_type_information = (
        {
            'immediate_view' : 'editGroupSettings',
            'actions'        :
            (
                {'name'         : 'Edit',
                'action'        : 'editGroupSettings',
                'permissions'   : (ZEN_CHANGE_SETTINGS,),
                },
                {'name'         : 'Administered Objects',
                'action'        : 'administeredDevices',
                'permissions'   : (ZEN_CHANGE_ADMIN_OBJECTS,)
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def iseditable(self):
        """Can the current user edit this settings object.
        """
        currentUser = getSecurityManager().getUser()
        return currentUser.has_role("Manager") or currentUser.has_role("ZenManager")

    def _getG(self):
        return self.zport.acl_users.groupManager


    def hasNoGlobalRoles(self):
        """This is a group we never have roles. This is set to false so that
        functionality that would normally be taken away for a restricted user is
        left in.
        """
        return False


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addUsersToGroup')
    @validate_csrf_token
    def manage_addUsersToGroup( self, userids, REQUEST=None ):
        """ Add user to this group
        """
        if isinstance(userids, basestring):
            userids = [userids]
        for userid in userids:
            # see if this group's already exists in the ZODB group manager.
            # if it doesn't - add it.
            group_ids = self._getG().listGroupIds()
            if self.id not in group_ids:
                self._getG().addGroup(self.id)
            self._getG().addPrincipalToGroup(userid, self.id)
            if REQUEST:
                audit('UI.User.AddToGroup', username=userid, group=self.id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Users Added',
                'Added %s to Group %s' % (','.join(userids), self.id)
            )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteUserFromGroup')
    def manage_deleteUserFromGroup( self, userid ):
        self._getG().removePrincipalFromGroup( userid, self.id )

    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteUsersFromGroup')
    @validate_csrf_token
    def manage_deleteUsersFromGroup(self, userids=(), REQUEST=None ):
        """ Delete users from this group
        """
        for userid in userids:
            self.manage_deleteUserFromGroup(userid)
            if REQUEST:
                audit('UI.User.RemoveFromGroup', username=userid, group=self.id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Users Removed',
                'Deleted users from Group %s' % self.id
            )
            return self.callZenScreen(REQUEST)

    def getMemberUserSettings(self):
        """
        Returns a list of UserSetting instances that are members of this group.
        """
        members = set()
        # We must using reverse mapping of all users to their groups rather
        # than going directly to the group's assigned principals because
        # some group backends don't support listAssignedPrincipals.
        [ members.add(u) for u in self.ZenUsers.getAllUserSettings()
            if self.id in u.getUserGroupSettingsNames() ]

        # make sure we get everyone assigned directly to this group (incase they appear in
        # another acl_users as is the case with admin)
        [ members.add(self.getUserSettings(u[0]))
          for u in self._getG().listAssignedPrincipals(self.id) if self.ZenUsers.getUser(u[0]) ]
        return members

    def getMemberUserIds(self):
        """
        Returns a list of user ids that are members of this group.
        """
        return [ u.id for u in self.getMemberUserSettings() ]

    def printUsers(self):
        try:
            userIds = self.getMemberUserIds()
        except LocalAndLDAPUserEntries as ex:
            return str(ex)

        return ", ".join(userIds)

    def getEmailAddresses(self):
        try:
            userIds = self.getMemberUserIds()
        except LocalAndLDAPUserEntries:
            return []

        result = []
        for username in userIds:
            result.extend(self.getUserSettings(username).getEmailAddresses())
        return result

    def getPagerAddresses(self):
        try:
            userIds = self.getMemberUserIds()
        except LocalAndLDAPUserEntries:
            return []

        result = []
        for username in userIds:
            result.extend(self.getUserSettings(username).getPagerAddresses())
        return result


InitializeClass(UserSettingsManager)
InitializeClass(UserSettings)
