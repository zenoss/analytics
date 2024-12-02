##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import requests
import json

from Products.ZenUtils.GlobalConfig import globalConfToDict
from Products.ZenUtils.controlplane.application import getConnectionSettings
from Products.ZenUtils.controlplane.client import getCCVersion

_ZPROXY_URL = 'http://127.0.0.1:8080'
_ZAUTH_LOGIN_URI = '/zauth/api/login'
_CC_LOGIN_URI = '/login'
_ELASTIC_URI = '/api/controlplane/elastic'

log = logging.getLogger("zen.elastic.client")


class ElasticClientException(Exception):
    pass

class ElasticClient(object):
    """
    A very simple client for talking to Control Center's elastic DB.
    Tested against Elastic 1.3.
    """

    def __init__(self):
        """
        Initialize a session object for the client to use.  The session will be
        used across all requests that the client makes.
        """
        self.session = None

        self._hothOrNewer = False if getCCVersion() == '1.1.X' else True
        if not self._hothOrNewer:
            self.ccURL = 'https://127.0.0.1'
        else:
            self.ccURL = 'http://127.0.0.1:443'
        self.login()

    def login(self):
        """
        Perform a login.  This actually logs us in to both zauth (so that we can
        use zproxy) and CC (so that we can hit elastic).  Note that a new session
        is created here.
        """
        self.session = requests.Session()
        gConf = globalConfToDict()
        # log into zauth
        if not (gConf.get('zauth-username', None) and gConf.get('zauth-password', None)):
            raise ElasticClientException('Unable to determine zauth credentials')
        resp = self.session.post(_ZPROXY_URL + _ZAUTH_LOGIN_URI, auth=(gConf['zauth-username'], gConf['zauth-password']))
        if resp.status_code != 200:
            raise ElasticClientException('Unable to authenticate with zauth')
        if not resp.headers.get('X-Zauth-Tokenid', None):
            raise ElasticClientException ('Did not recieve X-Zauth-Tokenid, cannot authenticate')
        self.session.headers['X-Zauth-Token'] = resp.headers['X-Zauth-Tokenid']
        # log into CC (for elastic quesries)
        connSettings = getConnectionSettings()
        if not all(param in connSettings for param in ('user', 'password')):
            raise ElasticClientException('Unable to determine Control Center credentials')
        ccLoginBody = json.dumps(
            {'username': connSettings['user'],
             'password': connSettings['password']
             }
        )
        self.session.verify = False
        resp = self.session.post( self.ccURL + _CC_LOGIN_URI, data=ccLoginBody)
        if resp.status_code != 200:
            raise ElasticClientException('Unable to authenticate with Control Center', resp)

    def _handleResponse(self, resp):
        """
        Handle the response to a requests.Request.  Assume JSON in the response
        and return it using the JSON loader.
        """
        if resp.status_code != 200:
            raise ElasticClientException('Error response (%s) from request' % resp.status_code, resp)
        return resp.json()

    def _doRequest(self, uri, method='GET', **kwargs):
        """
        A general method for making requests to elastic.
        Assume nothing about the expected response.
        Accepts all kwargs that a requests.Session.request() call would.
        Returns the JSON body data as a python object using json.loads()
        """
        if not self._hothOrNewer:
            return self._handleResponse(
                self.session.request(method, _ZPROXY_URL + _ELASTIC_URI + uri, **kwargs)
            )
        else:
            return self._handleResponse(
                self.session.request(method, self.ccURL + _ELASTIC_URI + uri, **kwargs)
            )
    def getIndexes(self):
        """
        Return a dictionary of indexes and their aliases.  It will be of the form:
            {
                'index-1': {'aliases': {}},
                'index-2': {'aliases': {}}
            }
        """
        return self._doRequest('/_aliases')

    def doSearchURI(self, index_string, query, **kwargs):
        """
        Do a simple URI search.

        @param index_string
        A comma-separated list of the indexes to search
        @param query
        The query string, sans '?q='.  For example:
            query = 'service:(applesauce)&size=666'
        """
        return self._doRequest('/' + index_string + '/_search?q=' + query, **kwargs)

    def doCount(self, index_string, query):
        """
        Count the documents that a query matches

        @param index_string
        A comma-separated list of the indexes to search
        @param query
        The query string, sans '?q='.  For example:
            query = 'service:(applesauce)&size=666'
        """
        return self._doRequest('/' + index_string + '/_count?q=' + query)['count']

    def doScrollURI(self, query):
        """
        Scroll through the matched documents

        @param query
        The query string, sans '?q='.  For example:
            query = 'service:(applesauce)&size=666'
        """
        return self._doRequest('/_search/scroll?' + query)


# Define the names to export via 'from client import *'.
__all__ = (
    "ElasticClient",
    "ElasticClientException"
)
