##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase
from mock import Mock, patch

from ..auth import HubRealm, getCredentialCheckers, pb
from ..avatar import HubAvatar

PATH = {"src": "Products.ZenHub.server.auth"}


class HubRealmTest(TestCase):
    """Test the HubRealm class."""

    def setUp(self):
        self.avatar = Mock(HubAvatar)
        self.realm = HubRealm(self.avatar)

    def test_requestAvatar(self):
        cid = "admin"
        mind = object()
        intfs = [pb.IPerspective]

        actual = self.realm.requestAvatar(cid, mind, *intfs)
        self.assertTrue(len(actual), 3)

        intf, avatar, callback = actual
        self.assertEqual(intf, pb.IPerspective)
        self.assertEqual(avatar, self.avatar)
        self.assertTrue(callable(callback))


class LoadCheckersTest(TestCase):
    """Test the LoadCheckers class."""

    @patch("{src}.checkers".format(**PATH), spec=True)
    def test_getCredentialCheckers(self, checkers):
        pwdfile = "passwordfile"
        checker = checkers.FilePasswordDB.return_value

        expected = [checker]
        actual = getCredentialCheckers(pwdfile)

        checkers.FilePasswordDB.assert_called_with(pwdfile)
        self.assertEqual(actual, expected)
