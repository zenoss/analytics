##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase
from mock import Mock, patch, sentinel, create_autospec

from ..xmlrpc import AuthXmlRpcService

PATH = {"src": "Products.ZenHub.server.xmlrpc"}


class AuthXmlRpcServiceTest(TestCase):
    """Test the AuthXmlRpcService class."""

    def setUp(t):
        t.dmd = Mock(name="dmd", spec_set=["ZenEventManager"])
        t.checker = Mock(name="checker", spec_set=["requestAvatarId"])

        t.axrs = AuthXmlRpcService(t.dmd, t.checker)

    @patch("{src}.XmlRpcService.__init__".format(**PATH), autospec=True)
    def test___init__(t, XmlRpcService__init__):
        dmd = sentinel.dmd
        checker = sentinel.checker

        axrs = AuthXmlRpcService(dmd, checker)

        XmlRpcService__init__.assert_called_with(axrs, dmd)
        t.assertEqual(axrs.checker, checker)

    @patch("{src}.XmlRpcService.render".format(**PATH), autospec=True)
    def test_doRender(t, render):
        request = sentinel.request

        result = t.axrs.doRender("unused arg", request)

        render.assert_called_with(t.axrs, request)
        t.assertEqual(result, render.return_value)

    @patch("{src}.xmlrpc".format(**PATH), name="xmlrpc", autospec=True)
    def test_unauthorized(t, xmlrpc):
        request = sentinel.request
        t.axrs._cbRender = create_autospec(t.axrs._cbRender)

        t.axrs.unauthorized(request)

        xmlrpc.Fault.assert_called_with(t.axrs.FAILURE, "Unauthorized")
        t.axrs._cbRender.assert_called_with(xmlrpc.Fault.return_value, request)

    @patch("{src}.server".format(**PATH), name="server", autospec=True)
    @patch(
        "{src}.credentials".format(**PATH),
        name="credentials",
        autospec=True,
    )
    def test_render(t, credentials, server):
        request = Mock(name="request", spec_set=["getHeader"])
        auth = Mock(name="auth", spec_set=["split"])
        encoded = Mock(name="encoded", spec_set=["decode"])
        encoded.decode.return_value.split.return_value = ("user", "password")
        auth.split.return_value = ("Basic", encoded)

        request.getHeader.return_value = auth

        ret = t.axrs.render(request)

        request.getHeader.assert_called_with("authorization")
        encoded.decode.assert_called_with("base64")
        encoded.decode.return_value.split.assert_called_with(":")
        credentials.UsernamePassword.assert_called_with("user", "password")
        t.axrs.checker.requestAvatarId.assert_called_with(
            credentials.UsernamePassword.return_value,
        )
        deferred = t.axrs.checker.requestAvatarId.return_value
        deferred.addCallback.assert_called_with(t.axrs.doRender, request)

        t.assertEqual(ret, server.NOT_DONE_YET)
