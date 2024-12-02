##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from collections import namedtuple
import functools
import unittest

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.controlplane import application
from Products.ZenUtils.controlplane.application import (
    DeployedApp, DeployedAppConfig, DeployedAppLog, DeployedAppLookup
)


def _getTenantId():
    return "abc123"

application.getTenantId = _getTenantId

class _TestDeployedAppLookup(DeployedAppLookup):
    def getTenantId(self):
        return _getTenantId()

class _MockClient(object):

    def __init__(self, **kwargs):
        self._data = kwargs.get('data', {})

    def queryServices(self, name=None, tags=None, tenantID=None):
        tags = tags if tags else ()
        keys = self._data.keys()
        for tag in tags:
            for keyId, keyTags in list(keys):
                if tag.startswith('-'):
                    if tag in keyTags:
                        keys.remove((keyId, keyTags))
                else:
                    if tag not in keyTags:
                        keys.remove((keyId, keyTags))
        if name:
            keys = [k for k in keys if k[0] == name]
        return [self._data[key] for key in keys]

    def getService(self, name):
        result = [k[0] for k in self._data if k[0] == name]
        return self._data.get(result[0]) if result else None


Service = namedtuple(
    "Service",
    [
        "configFiles",
        "description",
        "desiredState",
        "id",
        "launch",
        "logResourceId",
        "name",
        "resourceId",
        "tags"
    ]
)

service1 = Service(
    id="ace45020c",
    name="Service One",
    resourceId="/services/ace45020c",
    description="This is a service",
    configFiles={},
    desiredState="",
    launch="",
    logResourceId="",
    tags=["daemon"],
)


class DeployedAppTest(BaseTestCase):
    """
    """
    def test001(self):
        _TestDeployedAppLookup.clientClass = _MockClient
        lookup = _TestDeployedAppLookup()
        result = lookup.query()
        self.assertEqual(result, ())

    def test002(self):
        data = {
            (service1.id, tuple(service1.tags)): service1,
        }
        _TestDeployedAppLookup.clientClass = functools.partial(_MockClient, data=data)
        lookup = _TestDeployedAppLookup()
        result = lookup.query()
        self.assertEqual(len(result), 1)
        app = result[0]
        self.assertTrue(isinstance(app, DeployedApp))
        self.assertEqual(app.id, service1.id)
        self.assertEqual(app.name, service1.name)
        self.assertEqual(app.description, service1.description)


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(DeployedAppTest),))


if __name__ == "__main__":
    unittest.main(default="test_suite")
