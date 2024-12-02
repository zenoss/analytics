##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from twisted.cred import credentials
from twisted.internet.endpoints import serverFromString
from twisted.web import server, xmlrpc
from zope.component import getUtility

from Products.ZenHub.XmlRpcService import XmlRpcService

from .interface import IHubServerConfig
from .utils import TCPDescriptor, getLogger


class XmlRpcManager(object):
    """Manages the XMLRPC server."""

    def __init__(self, dmd, authenticator):
        """Initialize an XmlRpcManager instance."""
        service = AuthXmlRpcService(dmd, authenticator)
        self.__site = server.Site(service)

    def start(self, reactor):
        config = getUtility(IHubServerConfig)
        descriptor = TCPDescriptor.with_port(config.xmlrpcport)
        xmlrpc_server = serverFromString(reactor, descriptor)
        xmlrpc_server.listen(self.__site)


class AuthXmlRpcService(XmlRpcService):
    """Extends XmlRpcService to provide authentication."""

    def __init__(self, dmd, checker):
        """Initialize an AuthXmlRpcService instance.

        @param dmd {DMD} A /zport/dmd reference
        @param checker {ICredentialsChecker} Used to authenticate clients.
        """
        XmlRpcService.__init__(self, dmd)
        self.checker = checker
        self.__log = getLogger(self)

    def doRender(self, unused, request):
        """Call the inherited render engine after authentication succeeds."""
        return XmlRpcService.render(self, request)

    def unauthorized(self, request):
        """Render an XMLRPC error indicating an authentication failure.

        @type request: HTTPRequest
        @param request: the request for this xmlrpc call.
        @return: None
        """
        self._cbRender(xmlrpc.Fault(self.FAILURE, "Unauthorized"), request)

    def render(self, request):
        """Unpack the authorization header and check the credentials.

        @type request: HTTPRequest
        @param request: the request for this xmlrpc call.
        @return: NOT_DONE_YET
        """
        auth = request.getHeader("authorization")
        if not auth:
            self.unauthorized(request)
        else:
            try:
                authtype, encoded = auth.split()
                if authtype not in ("Basic",):
                    self.unauthorized(request)
                else:
                    user, passwd = encoded.decode("base64").split(":")
                    c = credentials.UsernamePassword(user, passwd)
                    d = self.checker.requestAvatarId(c)
                    d.addCallback(self.doRender, request)

                    def error(unused, request):
                        self.unauthorized(request)

                    d.addErrback(error, request)
            except Exception:
                self.__log.exception(
                    "[render] Exception caught; assuming unauthorized",
                )
                self.unauthorized(request)
        return server.NOT_DONE_YET
