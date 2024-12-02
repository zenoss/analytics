##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Tests for Products.ZenUtils.Redactor module."""

import unittest

from Products.ZenUtils import Redactor


class TestRedactor(unittest.TestCase):
    def test_redact_simple_object_returns_object2(self):
        subj = "hello"
        tr = Redactor.redact(subj)
        self.assertEqual(tr, subj, "redact simple object should return object")

    def test_simple_list2(self):
        subj = ["hello", 1, 2, 3, "password"]
        tr = Redactor.redact(subj)
        self.assertEqual(tr, subj, "redact list should return list")

    def test_simple_dict_no_match2(self):
        subj = {"foo": "bar", "baz": 1, "bletch": "a thing"}
        tr = Redactor.redact(subj)
        self.assertEqual(tr, subj,
                         "redact nonmatching dict should return dict")

    def test_redact_complicated_object2(self):
        subj = [
            "foo",
            {
                "bar": "baz",
                "A": 1,
                "B": [1, 2, 'ABC']
            },
            ["sublist", 1, 2, "password"],
        ]
        tr = Redactor.redact(subj)
        self.assertEqual(tr, subj, "complicated object should return same")

    def test_redact_simple_dict2(self):
        subj = {"foo": "something", "bar": 25, "password": "it is a secret"}
        expected = {"foo": "something", "bar": 25, "password": "<REDACTED>"}
        tr = Redactor.redact(subj, "password")
        self.assertEqual(tr, expected,
                         "password should be redacted in simple dictionary")

    def test_redact_complicated_obj2(self):
        subj = [
            "foo",
            {
                "bar": "baz",
                "password": "itsasecret",
                "A": 1,
                "B": [1, 2, 'ABC']
            },
            ["sublist", 1, 2],
        ]
        expected = [
            "foo",
            {
                "bar": "baz",
                "password": "<REDACTED>",
                "A": 1,
                "B": [1, 2, 'ABC']
            },
            ["sublist", 1, 2],
        ]
        tr = Redactor.redact(subj, "password")
        self.assertEqual(tr, expected,
                         "password should be redacted in complex object")

    def test_redact_multimatch2(self):
        subj = [
            "foo",
            {
                "bar": "baz",
                "password": "itsasecret",
                "A": 1,
                "B": [1, 2, 'ABC']
            },
            {
                "la": "la",
                "password": "anotherone",
                "blah": "blah value"
            },
            ["sublist", 1, 2],
        ]
        expected = [
            "foo",
            {
                "bar": "baz",
                "password": "<REDACTED>",
                "A": 1,
                "B": [1, 2, 'ABC']
            },
            {
                "la": "la",
                "password": "<REDACTED>",
                "blah": "blah value"
            },
            ["sublist", 1, 2],
        ]
        tr = Redactor.redact(subj, "password")
        self.assertEqual(tr, expected,
                         "password should be redacted in complex object")

    def test_redact_multimatch_multitarget2(self):
        subj = [
            "foo",
            {
                "bar": "baz",
                "password": "itsasecret",
                "A": 1,
                "B": [1, 2, 'ABC']
            },
            {
                "la": "la",
                "password": "anotherone",
                "blah": "blah value"
            },
            ["sublist", 1, 2],
        ]
        expected = [
            "foo",
            {
                "bar": "baz",
                "password": "<REDACTED>",
                "A": 1,
                "B": "<REDACTED>"
            },
            {
                "la": "la",
                "password": "<REDACTED>",
                "blah": "blah value"
            },
            ["sublist", 1, 2],
        ]
        tr = Redactor.redact(subj, ["password", "B"])
        self.assertEqual(tr, expected,
                         "password should be redacted in complex object")

    def test_sample_case2(self):
        subj = [
            {
                "mapLDAPGroupsToZenossRoles": "True",
                "managerDN": "cn=admin,dc=zenoss-testing,dc=zenoss,dc=loc",
                "defaultUserRoles": [
                    "ZenUser"
                ],
                "userBaseDN": "dc=Users",
                "activeDirectory": "True",
                "managerPassword": "mypassword",
                "servers": [
                    {
                        "ssl": "False",
                        "host": "test-ldap-1.zenoss.loc",
                        "port": "389",
                        "self_signed_cert": "False"
                    }
                ],
                "loginNameAttr": "cn",
                "newId": "test-ldap-1.zenoss.loc",
                "extraUserFilter": "(cn=Organization.blah)",
                "extraGroupFilter": "(cn=something)",
                "schemaMappings": [
                    {
                        "friendlyName": "Canonical Name",
                        "ldapMapToName": "",
                        "ldapattr": "cn",
                        "multivalued": "False"
                    },
                    {
                        "friendlyName": "Email Address",
                        "ldapMapToName": "email",
                        "ldapattr": "mail",
                        "multivalued": "False"
                    },
                    {
                        "friendlyName": "Last Name",
                        "ldapMapToName": "",
                        "ldapattr": "sn",
                        "multivalued": "False"
                    }
                ],
                "groupMappings": [],
                "groupBaseDN": "dc=zenoss",
                "id": "test-ldap-1.zenoss.loc"
            }
        ]
        expected = [
            {
                "mapLDAPGroupsToZenossRoles": "True",
                "managerDN": "cn=admin,dc=zenoss-testing,dc=zenoss,dc=loc",
                "defaultUserRoles": [
                    "ZenUser"
                ],
                "userBaseDN": "dc=Users",
                "activeDirectory": "True",
                "managerPassword": "<REDACTED>",
                "servers": [
                    {
                        "ssl": "False",
                        "host": "test-ldap-1.zenoss.loc",
                        "port": "389",
                        "self_signed_cert": "False"
                    }
                ],
                "loginNameAttr": "cn",
                "newId": "test-ldap-1.zenoss.loc",
                "extraUserFilter": "(cn=Organization.blah)",
                "extraGroupFilter": "(cn=something)",
                "schemaMappings": [
                    {
                        "friendlyName": "Canonical Name",
                        "ldapMapToName": "",
                        "ldapattr": "cn",
                        "multivalued": "False"
                    },
                    {
                        "friendlyName": "Email Address",
                        "ldapMapToName": "email",
                        "ldapattr": "mail",
                        "multivalued": "False"
                    },
                    {
                        "friendlyName": "Last Name",
                        "ldapMapToName": "",
                        "ldapattr": "sn",
                        "multivalued": "False"
                    }
                ],
                "groupMappings": [],
                "groupBaseDN": "dc=zenoss",
                "id": "test-ldap-1.zenoss.loc"
            }
        ]
        tr = Redactor.redact(subj, "managerPassword")
        self.assertEqual(tr, expected,
                         "password should be redacted in object from real life")


if __name__ == '__main__':
    unittest.main()
