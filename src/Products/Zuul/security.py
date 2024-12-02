from zope.interface import implements

from App.config import getConfiguration
from Products.Zuul.interfaces import IAuthorizationTool
from Products.PluggableAuthService import interfaces
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from collective.beaker.interfaces import ISession

import logging
log = logging.getLogger('zen.Security')

import time

class AuthorizationTool(object):
    implements(IAuthorizationTool)

    def __init__(self, context):
        self.context = context

    def authenticateCredentials(self, login, password):
        """
        Call the ZenUsers authenication method.
        """
        ZenUsers = self.context.zport.dmd.ZenUsers
        return ZenUsers.authenticateCredentials(login, password)

    def extractCredentials(self, request):
        """
        Iterate through the zope extraction plugins to identify login and password credentials.
        If extraction plugins fails to identify credentials, look in the request object.
        This method returns None for both login and password when credentials do not exist.
        """
        acl_users = self.context.zport.acl_users

        type = interfaces.plugins.IExtractionPlugin
        plugins = acl_users.plugins.listPlugins(type)

        # look in the extraction plugins for the credentials
        for (extractor_id, extractor) in plugins:
            creds = extractor.extractCredentials(request)
            if 'login' in creds and 'password' in creds:
                return creds

        # look in the request headers for the creds
        login = request.get('login', None)
        password = request.get('password', None)
        return {'login': login, 'password': password}

    def extractGlobalConfCredentials(self):
        conf = getGlobalConfiguration()
        login = conf.get('zauth-username', None)
        password = conf.get('zauth-password', None)
        return {'login':login, 'password':password}

    def extractSessionCredentials(self):
        session = self.context.REQUEST.SESSION
        login = session.get( '__ac_name', None)
        password = session.get( '__ac_password', None)
        return {'login':login, 'password':password}

    def createAuthToken(self, request, expires=None):
        """
        Creates an authentication token. Since zauth tokens are currently stored in the session
        the expires can be no further than ( now + session time out).
        TODO: Allow a config option for default expires.
        @param request
        @return: dictionary with the token id and expiration
        """
        if expires is None:
            expires = self._getSessionTimeout()
        tokenId = request.SESSION.getId()
        token = dict(id=tokenId, expires=expires)
        request.SESSION.set(tokenId, token)
        return token

    def getToken(self, sessionId):
        """
        @param sessionId:
        @return:
        """
        sessionData = self._getSessionData(sessionId)
        if sessionData:
            return sessionData.get(sessionId, None)
        return None

    def tokenExpired(self, sessionId):
        token = self.getToken(sessionId)
        if token is None:
            log.debug("Token is None for sessionid %s", sessionId)
            return True
        log.debug("Token is %s for sessionid %s", token, sessionId)
        newexp = self._getSessionTimeout()
        token['expires'] = newexp

        expired = time.time() >= token['expires']
        log.debug("Token expired = %s", expired)
        return expired

    def _getSessionData(self, id):
        # For some reason Products.BeakerSessionDataManager doesn't support getSessionDataByKey
        #sess = self.context.session_data_manager.getSessionDataByKey(sessionId)
        session = ISession(self.context.REQUEST)
        return session.get_by_id(id)

    def _getSessionTimeout(self):
        expires = time.time() + 60 * getConfiguration().session_timeout_minutes
        return expires
