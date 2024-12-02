##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import transaction

from Products.Five.browser import BrowserView

from Products.Zuul.interfaces import IAuthorizationTool

ZAUTH_HEADER_ID = "X-ZAuth-Token"


class Authorization(BrowserView):
    """
    This view acts as a namespace so the client requests are
    /authorization/login and /authorization/validate.
    """

    def __getitem__(self, index):
        if index == "login":
            return Login(self.context, self.request)
        if index == "validate":
            return Validate(self.context, self.request)
        raise Exception("Invalid authorization view %s" % index)


class Login(BrowserView):
    """
    Validates the credentials supplied and creates a new authorization token.
    """

    def __call__(self, *args, **kwargs):
        """
        Extract login/password credentials, test authentication,
        and create a token.
        """

        # test for uuid
        if self.uuid is None:
            self.request.response.setStatus(503)
            self.request.response.write(
                "System uninitialized - please execute setup wizard"
            )
            transaction.abort()
            return

        authorization = IAuthorizationTool(self.context.context)
        credentials = authorization.extractCredentials(self.request)

        login = credentials.get("login", None)
        password = credentials.get("password", None)

        # no credentials to test authentication
        if login is None or password is None:
            self.request.response.setStatus(401)
            self.request.response.write("Missing Authentication Credentials")
            transaction.abort()
            return

        # test authentication
        if not authorization.authenticateCredentials(login, password):
            self.request.response.setStatus(401)
            self.request.response.write("Failed Authentication")
            transaction.abort()
            return

        # create the session data
        token = authorization.createAuthToken(self.request)
        self.request.response.setHeader("X-ZAuth-TokenId", token["id"])
        self.request.response.setHeader(
            "X-ZAuth-TokenExpiration", token["expires"]
        )
        self.request.response.setHeader("X-ZAuth-TenantId", self.uuid)
        return json.dumps(token)

    @property
    def dmd(self):
        return self.context.context.zport.dmd

    @property
    def uuid(self):
        return self.dmd.uuid


class Validate(BrowserView):
    """
    Assert token id exists in session data and token id hasn't expired
    """

    def __call__(self, *args, **kwargs):
        """
        extract token id, test token expiration, and return token
        """
        # test for uuid
        if self.uuid is None:
            self.request.response.setStatus(503)
            self.request.response.write(
                "System uninitialized - please execute setup wizard"
            )
            return

        tokenId = self.request.get("id", None)
        if tokenId is None:
            tokenId = self.request.getHeader(ZAUTH_HEADER_ID)

        # missing token id
        if tokenId is None:
            self.request.response.setStatus(401)
            self.request.response.write("Missing Token Id")
            return

        authorization = IAuthorizationTool(self.context.context)

        # Grab token to handle edge case, when expiration happens after
        # expiration test.
        tokenId = tokenId.strip('"')
        token = authorization.getToken(tokenId)
        if authorization.tokenExpired(tokenId):
            self.request.response.setStatus(401)
            self.request.response.write("Token Expired")
            return

        self.request.response.setHeader("X-ZAuth-TokenId", token["id"])
        self.request.response.setHeader(
            "X-ZAuth-TokenExpiration", token["expires"]
        )
        self.request.response.setHeader("X-ZAuth-TenantId", self.uuid)
        return json.dumps(token)

    @property
    def dmd(self):
        return self.context.context.zport.dmd

    @property
    def uuid(self):
        return self.dmd.uuid
