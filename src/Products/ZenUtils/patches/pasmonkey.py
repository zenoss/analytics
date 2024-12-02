##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


'''
This module contains monkey patches we needed to make to PAS when we switched
from native ZODB-managed authentication to pluggable authentication.

This module needs to be imported by ZenUtils/__init__.py.

Related tickets:
  http://dev.zenoss.org/trac/ticket/379
  http://dev.zenoss.org/trac/ticket/402
  http://dev.zenoss.org/trac/ticket/443
  http://dev.zenoss.org/trac/ticket/1042
  http://dev.zenoss.org/trac/ticket/4225
  http://jira.zenoss.com/jira/browse/ZEN-110
'''

import urllib
import urlparse
from uuid import uuid1
from cgi import parse_qs
from Acquisition import aq_base
from AccessControl import AuthEncoding
from AccessControl.SpecialUsers import emergency_user
from AccessControl import ClassSecurityInfo
from zope.event import notify
from ZODB.POSException import POSKeyError
from Products.PluggableAuthService import PluggableAuthService
from Products.PluggableAuthService.PluggableAuthService import \
        _SWALLOWABLE_PLUGIN_EXCEPTIONS, DumbHTTPExtractor
from Products.PluggableAuthService.plugins import (CookieAuthHelper, 
                                                   ZODBUserManager)
from Products.PluggableAuthService.interfaces.authservice import _noroles
from Products.PluggableAuthService.interfaces.plugins import \
        IAuthenticationPlugin, IExtractionPlugin
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.events import UserLoggedInEvent, UserLoggedOutEvent
from Products.ZenUtils.Security import _createInitialUser

from Products.PluggableAuthService.plugins import SessionAuthHelper

from Products.PluggableAuthService.utils import createViewName, createKeywords
from Products.ZenUtils.AccountLocker.AccountLocker import Locked

import logging
log = logging.getLogger('PAS Patches')

# monkey patch PAS to allow inituser files, but check to see if we need to
# actually apply the patch, first -- support may have been added at some point
pas = PluggableAuthService.PluggableAuthService
if not hasattr(pas, '_createInitialUser'):
    pas._createInitialUser =  _createInitialUser

SESSION_RESET_WARNING = """
A Poskey was detected in the session database so we are resetting it. All active sessions will be terminated. This is likely due to a clock issue on the host
"""
# Monkey patch PAS to monitor logouts (credential resets).
# Have to check the request object to determine when we have an actual
# logout instead of 'fake' logout (like the logout of the anonymous user)
_originalResetCredentials = pas.resetCredentials
def _resetCredentials(self, request, response=None):
    audit("UI.Authentication.Logout")
    notify(UserLoggedOutEvent(self.zport.dmd.ZenUsers.getUserSettings()))
    try:
        _originalResetCredentials(self, request, response)
    except (KeyError, POSKeyError):
        # see defect ZEN-2942 If the time changes while the server is running
        # set the session database to a sane state.
        log.warning(SESSION_RESET_WARNING)
        ts = self.unrestrictedTraverse('/temp_folder/session_data')
        ts._reset()
        _originalResetCredentials(self, request, response)


pas.resetCredentials = _resetCredentials


def get_ip(request):
    if "HTTP_X_FORWARDED_FOR" in request.environ:
        # Virtual host
        # This can be a comma-delimited list of IPs but we are fine with
        # logging multiple IPs for auditing at this time.
        ip = request.environ["HTTP_X_FORWARDED_FOR"]
    elif "HTTP_HOST" in request.environ:
        # Non-virtualhost
        ip = request.environ["REMOTE_ADDR"]
    else:
        ip = getattr(request, '_client_addr', 'Unknown')

    return ip


# Monkey patch PAS to audit log successful and failed login attempts
def validate(self, request, auth='', roles=_noroles):
    """
    Here is a run down of how this method is called and where it ends up returning
    in various login situations.

    Failure (admin, local, LDAP, and Active Directory)
       is_top=0, user_ids=[], name=login, if not is_top: return None (outside loop)
       is_top=1, user_ids=[], name=login, return anonymous

   Success (admin)
      is_top=0, user_ids=[], name=login, if not is_top: return (outside loop)
      is_top=1, user_ids=[('admin', 'admin')], name=login, if self._authorizeUser(...): return user

    Success (local, LDAP, and Active Directory)
       is_top=0, user_ids=[('username', 'username')], name=login, if self._authorizeUser(...): return user
    """
    plugins = self._getOb( 'plugins' )
    is_top = self._isTop()
    user_ids = self._extractUserIds(request, plugins)
    accessed, container, name, value = self._getObjectContext(request['PUBLISHED'], request)
    ipaddress = get_ip(request)
    for user_id, login in user_ids:
        user = self._findUser(plugins, user_id, login, request=request)
        if aq_base(user) is emergency_user:
            if is_top:
                return user
            else:
                return None

        if self._authorizeUser(user, accessed, container, name, value, roles):
            if name == 'login':
                audit('UI.Authentication.Valid', ipaddress=ipaddress)
                notify(UserLoggedInEvent(self.zport.dmd.ZenUsers.getUserSettings()))
            return user

    if not is_top:
        return None

    anonymous = self._createAnonymousUser(plugins)
    if self._authorizeUser(anonymous, accessed, container, name, value, roles):
        if name == 'login' and '/authorization/login' not in request.environ.get('PATH_INFO', ''):
            username_ = request.form.get('__ac_name', 'Unknown')
            audit('UI.Authentication.Failed', username_=username_, ipaddress=ipaddress)
        return anonymous

    return None

pas.validate = validate

# monkey patches for the PAS login form

def manage_afterAdd(self, item, container):
    """We don't want CookieAuthHelper setting the login attribute, we we'll
    override manage_afterAdd().

    For now, the only thing that manage_afterAdd does is set the login_form
    attribute, but we will need to check this after every upgrade of the PAS.
    """
    pass

CookieAuthHelper.CookieAuthHelper.manage_afterAdd = manage_afterAdd

def login(self):
    """
    Set a cookie and redirect to the url that we tried to
    authenticate against originally.

    FIXME - I don't think we need this any more now that the EULA is gone -EAD
    """
    request = self.REQUEST
    response = request['RESPONSE']

    login = request.get('__ac_name', '')
    password = request.get('__ac_password', '')
    submitted = request.get('submitted', '')

    pas_instance = self._getPAS()

    if pas_instance is not None:
        try:
            pas_instance.updateCredentials(request, response, login, password)
        except (KeyError, POSKeyError):
            # see defect ZEN-2942 If the time changes while the server is running
            # set the session database to a sane state.
            log.warning(SESSION_RESET_WARNING)
            ts = self.unrestrictedTraverse('/temp_folder/session_data')
            ts._reset()
            # try again and if it fails this time there isn't anything we can do
            pas_instance.updateCredentials(request, response, login, password)

    came_from = request.form.get('came_from') or ''
    if came_from:
        parts = urlparse.urlsplit(came_from)
        querydict = parse_qs(parts[3])
        querydict.pop('terms', None)
        if 'submitted' not in querydict.keys():
            querydict['submitted'] = submitted
        newqs = urllib.urlencode(querydict, doseq=True)
        parts = parts[:3] + (newqs,) + parts[4:]
        came_from = urlparse.urlunsplit(parts)
    else:
        submittedQs = 'submitted=%s' % submitted
        came_from = '/zport/dmd?%s' % submittedQs

    if not self.dmd.acceptedTerms:
        url = "%s/zenoss_terms/?came_from=%s" % (
                    self.absolute_url_path(), urllib.quote(came_from))
    else:
        # get rid of host part of URL (prevents open redirect attacks)
        clean_url = ['', ''] + list(urlparse.urlsplit(came_from))[2:]
        url = urlparse.urlunsplit(clean_url)

    fragment = request.get('fragment', '')
    if fragment:
        fragment = urllib.unquote( fragment)
        if not fragment.startswith( '#'):
            fragment = '#' + fragment
        url += fragment

    if self.dmd.uuid is None:
        self.dmd.uuid = str(uuid1())

    return response.redirect(url)

CookieAuthHelper.CookieAuthHelper.login = login

_originalZODBUserManager_authenticateCredentials = ZODBUserManager.ZODBUserManager.authenticateCredentials
def authenticateCredentials( self, credentials ):
    user_id = credentials.get('session_user_id', '')
    info = credentials.get('session_user_info', '')

    if user_id and self._getPAS().getUserById(user_id):
        return user_id, info

    return _originalZODBUserManager_authenticateCredentials(self, credentials)


ZODBUserManager.ZODBUserManager.authenticateCredentials = authenticateCredentials


def _pw_encrypt( self, password ):
    """Returns the AuthEncoding encrypted password

    If 'password' is already encrypted, it is returned
    as is and not encrypted again.
    """
    if AuthEncoding.is_encrypted(password):
        return password
    return AuthEncoding.pw_encrypt(password, encoding='PBKDF2-SHA256')

ZODBUserManager.ZODBUserManager._pw_encrypt = _pw_encrypt


def extractCredentials(self, request):
    creds = {}

    user_id = request.SESSION.get('__ac_logged_as', '')
    info = request.SESSION.get('__ac_logged_info', '')
    if user_id:
        creds['session_user_id'] = user_id
        creds['session_user_info'] = info

        # Other authorization plugins may requrire this fields.
        creds['login'] = ''
        creds['password'] = ''
    else:
        # Look into the request now
        login_pw = request._authUserPW()

        if login_pw is not None:
            name, password = login_pw
            creds['login'] = name
            creds['password'] = password

    if creds:
        creds['remote_host'] = request.get('REMOTE_HOST', '')

        try:
            creds['remote_address'] = request.getClientAddr()
        except AttributeError:
            creds['remote_address'] = request.get('REMOTE_ADDR', '')

    return creds

SessionAuthHelper.SessionAuthHelper.extractCredentials = extractCredentials

def updateCredentials(self, request, response, login, new_password):
    # PAS sends to this methods all credentials provided by user without
    # checking.  So they need to be validate before session update.

    # `admin` user located in another PAS instance.
    if login == 'admin':
        acl_users = self.getPhysicalRoot().acl_users
    else:
        acl_users = self.getPhysicalRoot().zport.dmd.acl_users

    plugins = acl_users._getOb('plugins')
    try:
        authenticators = plugins.listPlugins(IAuthenticationPlugin)
    except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
        log.debug('Authenticator plugin listing error', exc_info=True)
        authenticators = ()

    credentials = {
        'login': login,
        'password': new_password,
        'extractor': 'sessionAuthHelper'}

    # First try to authenticate against the emergency
    # user and return immediately if authenticated
    user_id, info = acl_users._tryEmergencyUserAuthentication(credentials)

    if user_id is None:
        for authenticator_id, auth in authenticators:
            try:
                uid_and_info = auth.authenticateCredentials(credentials)
                if uid_and_info is None:
                    continue

                user_id, info = uid_and_info

                if auth.acl_users.meta_type == 'LDAPUserFolder':
                    # update zope's user-group assignments based on LDAP server's info (ZEN-24774)
                    updateLdapUserInGroupAssignments(
                        auth,
                        self.getPhysicalRoot().zport.dmd.ZenUsers,
                        user_id)

            except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
                log.debug('AuthenticationPlugin %s error', authenticator_id,
                          exc_info=True)
                continue
            except Locked:
                break

            if user_id is not None:
                break

    if user_id is not None:
        request.SESSION.set('__ac_logged_as', user_id)
        request.SESSION.set('__ac_logged_info', info)

SessionAuthHelper.SessionAuthHelper.updateCredentials = updateCredentials

def _extractUserIds( self, request, plugins ):
    """ request -> [ validated_user_id ]

    o For each set of extracted credentials, try to authenticate
    a user;  accumulate a list of the IDs of such users over all
    our authentication and extraction plugins.
    """
    try:
        extractors = plugins.listPlugins( IExtractionPlugin )
    except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
        log.info('Extractor plugin listing error', exc_info=True)
        extractors = ()

    if not extractors:
        extractors = ( ( 'default', DumbHTTPExtractor() ), )

    try:
        authenticators = plugins.listPlugins( IAuthenticationPlugin )
    except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
        log.info('Authenticator plugin listing error', exc_info=True)
        authenticators = ()

    result = []

    for extractor_id, extractor in extractors:

        try:
            credentials = extractor.extractCredentials( request )
        except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
            log.info('ExtractionPlugin %s error', extractor_id, exc_info=True)
            continue

        if credentials:
            try:
                credentials[ 'extractor' ] = extractor_id # XXX: in key?
                # Test if ObjectCacheEntries.aggregateIndex would work
                items = credentials.items()
                items.sort()
            except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
                log.info('Credentials error: %s', credentials, exc_info=True)
                continue

            # First try to authenticate against the emergency
            # user and return immediately if authenticated
            user_id, name = self._tryEmergencyUserAuthentication(
                                                        credentials )

            if user_id is not None:
                return [ ( user_id, name ) ]

            # Now see if the user ids can be retrieved from the cache
            view_name = createViewName('_extractUserIds', credentials.get('login'))
            keywords = createKeywords(**credentials)
           
            user_ids = None
            account_locker = getattr(self, 'account_locker_plugin', None)
            if not account_locker:
                user_ids = self.ZCacheable_get( view_name=view_name
                                              , keywords=keywords
                                              , default=None
                                              )

            else:
                if account_locker.isLocked(credentials.get('login')):         
                    user_ids = self.ZCacheable_get( view_name=view_name
                                                  , keywords=keywords
                                                  , default=None
                                                  )

            if user_ids is None:
                user_ids = []

                for authenticator_id, auth in authenticators:

                    try:
                        uid_and_info = auth.authenticateCredentials(
                            credentials )

                        if uid_and_info is None:
                            continue

                        user_id, info = uid_and_info

                    except _SWALLOWABLE_PLUGIN_EXCEPTIONS:
                        log.info(
                            'AuthenticationPlugin %s error',
                            authenticator_id,
                            exc_info=True,
                        )
                        continue
                    except Locked:
                        break

                    if user_id is not None:
                        user_ids.append( (user_id, info) )

                if user_ids:
                    self.ZCacheable_set( user_ids
                                       , view_name=view_name
                                       , keywords=keywords
                                       )

            result.extend( user_ids )

    # Emergency user via HTTP basic auth always wins
    user_id, name = self._tryEmergencyUserAuthentication(
            DumbHTTPExtractor().extractCredentials( request ) )

    if user_id is not None:
        return [ ( user_id, name ) ]

    return result

pas._extractUserIds = _extractUserIds

def resetCredentials(self, request, response):
    request.SESSION.set('__ac_logged_as', '')
    request.SESSION.set('__ac_logged_info', '')

SessionAuthHelper.SessionAuthHelper.resetCredentials = resetCredentials


def termsCheck(self):
    """ Check to see if the user has accepted the Zenoss terms.
    """
    request = self.REQUEST
    response = request['RESPONSE']

    acceptStatus = request.form.get('terms') or ''
    url = request.form.get('came_from') or self.absolute_url_path()

    if acceptStatus != 'Accept':
        self.resetCredentials(request, response)
        if '?' in url:
            url += '&'
        else:
            url += '?'
        url += 'terms=Decline'
    else:
        self.dmd.acceptedTerms = True
        self.dmd.uuid = str(uuid1())
    return response.redirect(url)

CookieAuthHelper.CookieAuthHelper.termsCheck = termsCheck


def updateLdapUserInGroupAssignments(auth, user_settings_manager, user_id):
    """ Associate zope's user-group assignments based on the LDAP server's
        information (via the auth object).  (ZEN-24774)
    """
    user = auth.getUser(user_id)
    group_id_list = auth.getGroupsForPrincipal(user)

    log.debug("LDAP> user: [%s]", user_id)
    log.debug("LDAP> user's groups from LDAP: [%s]", ",".join(group_id_list))

    for group_id in group_id_list:
        group_settings = user_settings_manager.getGroupSettings(group_id)
        group_settings.manage_addUsersToGroup([user_id])

