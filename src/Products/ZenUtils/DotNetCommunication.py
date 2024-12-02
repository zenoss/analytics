##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from urllib2 import HTTPCookieProcessor, build_opener, HTTPError
from urllib import quote
from urlparse import urljoin

#BASE_URL = 'http://dotnet.zenoss.loc:8080/ZenossDotNet/'
BASE_URL = 'http://localhost:8081/ZenossDotNet/'

_DotNetSessions = {}

def getDotNetSession(username, password):
    session = _DotNetSessions.get(username, None)
    if not session:
        session = DotNetSession()
        session.login(username, password)
        _DotNetSessions[username] = session
    return session

class DotNetSession(object):
    """
    A cookie-enabled http client that can log in to and retrieve data from
    Zenoss.net.
    """

    def __init__(self):
        """
        Set up the cookie jar.
        """
        import MultipartPostHandler
        self.opener = build_opener(HTTPCookieProcessor(),
                                MultipartPostHandler.MultipartPostHandler)
        self.base_url = BASE_URL

    def open(self, url, params={}):
        """
        Wrapper for the opener that encodes the query string.
        """
        url = urljoin(self.base_url, quote(url))
        try:
            response = self.opener.open(url, params)
        except HTTPError as e:
            print "Unable to access the Zenoss.net url:" + e.geturl()
            return None
        else:
            return response

    def login(self, username, password):
        """
        Log in to Zenoss.net.
        """
        loginUrl = 'login_form'

        # The fields just come from the login_form template
        params = {
            '__ac_name': username,
            '__ac_password': password,
            'came_from':'',
            'form.submitted':1,
            'js_enabled':1,
            'cookies_enabled':1
        }
        # POST the params to the loginUrl. The resulting
        # cookie will be stored in the cookie jar.
        # TODO: What happens on login failure?
        self.open(loginUrl, params)

    def retrieve(self, url, params={}):
        """
        Open a url within the session and return the response data.

        """
        response = self.open(url, params)
        if response:
            data = response.read()
            response.close()
            return data
            #return data.strip()
        else:
            return None
