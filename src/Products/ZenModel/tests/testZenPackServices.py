##############################################################################
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import json
import cStringIO

from contextlib import contextmanager

from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.ZenPack import ZenPack, DirectoryConfigContents
import Products.ZenModel.ZenPack
import __builtin__
import servicemigration


class _MockControlPlaneClient(object):
    def __call__(self, *args, **kwargs):
        return self

    def __init__(self, services=None, **kwargs):
        self._services = services if services else []
        self._added, self._deleted, self._stopped = [], [], []

    def queryServices(self, query):
        return self._services

    def deployService(self, parent, service):
        self._added.append((parent, service))
        svcDict = json.loads(service)
        self._services.append(
            _MockService(svcDict["Id"], parent, svcDict["Tags"])
        )

    def deleteService(self, serviceId):
        self._deleted.append(serviceId)

    def stopService(self, serviceId):
        self._stopped.append(serviceId)

    @property
    def added(self):
        return self._added

    @property
    def deleted(self):
        return self._deleted

    @property
    def stopped(self):
        return self._stopped


class _MockServiceMigrationContext(object):
    def __call__(self, *args, **kwargs):
        return self

    def __init__(self):
        self._added = []

    def _ServiceContext__deployService(self, service, parentid):
        self._added.append((parentid, service))

    def commit(self):
        return

    @property
    def added(self):
        return self._added


class _MockService(object):
    def __init__(self, id, parentId="", tags=None):
        self.name = id.upper()
        self._data = {}
        self.id = id
        self.parentId = parentId
        self.tags = tags if tags else []
        self.poolId = "default"

    def toJsonDict(self):
        return {
            "Id": self.id,
            "Name": self.name,
            "ParentId": self.parentId,
            "Tags": self.tags,
        }


class _MockServiceEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, _MockService):
            return o.toJsonDict()
        return json.JSONEncoder.default(o)


_services = [
    _MockService("zenoss", "", []),
    _MockService("zope", "zenoss", ["daemon"]),
    _MockService("hub1", "zenoss", ["hub"]),
]


@contextmanager
def setServiceMigrationContext(context):
    try:
        save = servicemigration.ServiceContext
        servicemigration.ServiceContext = context
        yield
    finally:
        servicemigration.ServiceContext = save


@contextmanager
def setControlPlaneClient(client):
    try:
        save = Products.ZenModel.ZenPack.ControlPlaneClient
        Products.ZenModel.ZenPack.ControlPlaneClient = client
        yield
    finally:
        Products.ZenModel.ZenPack.ControlPlaneClient = save


@contextmanager
def setCurrentService(id):
    try:
        save = ZenPack.currentServiceId
        ZenPack.currentServiceId = id
        yield
    finally:
        ZenPack.currentServiceId = save


def createMockLoadServiceDefinitions(fileDict):
    def dummyServiceDefinitions(name):
        return json.dumps(fileDict[name])

    return dummyServiceDefinitions


@contextmanager
def setBuiltinOpen(fileDict):
    try:
        builtin_open = __builtin__.open

        def _open(name, mode="r"):
            if name in fileDict:
                return cStringIO.StringIO(json.dumps(fileDict[name]))
            else:
                return builtin_open(name, mode)

        __builtin__.open = _open
        yield
    finally:
        __builtin__.open = builtin_open


class TestZenpackServices(ZenModelBaseTest):
    def testAddNoCurrentServiceId(self):
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        service = json.dumps(_MockService("id"), cls=_MockServiceEncoder)
        with setControlPlaneClient(client), setServiceMigrationContext(
            context
        ):
            ZenPack("id").installServiceDefinitions(service, "/hub")
        self.assertEquals(context.added, [])

    def testAddSingleService(self):
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        service = _MockService("id", "pid")
        service.poolId = "not_default"
        service = json.dumps(service, cls=_MockServiceEncoder)
        with setControlPlaneClient(client), setCurrentService(
            "zope"
        ), setServiceMigrationContext(context):
            ZenPack("id").installServiceDefinitions(service, "/hub")
        self.assertEquals(len(context.added), 1)
        parent, added = context.added[0][0], json.loads(context.added[0][1])
        self.assertEquals(added["Id"], "id")
        self.assertEquals(parent, "hub1")

    def testAddMultipleServices(self):
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        services = [
            json.dumps(_MockService(i), cls=_MockServiceEncoder)
            for i in ("id1", "id2")
        ]
        paths = ["/", "/hub"]
        with setControlPlaneClient(client), setCurrentService(
            "zope"
        ), setServiceMigrationContext(context):
            ZenPack("id").installServiceDefinitions(services, paths)
        self.assertEquals(len(context.added), 2)
        added = [(i[0], json.loads(i[1])) for i in context.added]
        self.assertEquals(added[0][1]["Id"], "id1")
        self.assertEquals(added[0][0], "zenoss")
        self.assertEquals(added[1][1]["Id"], "id2")
        self.assertEquals(added[1][0], "hub1")

    def testAddMultipleServicesRelative(self):
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        services = [
            json.dumps({"Name": n, "Tags": [t]})
            for n, t in zip(
                ["a", "b", "c", "d", "e"], ["1", "2", "3", "4", "5"]
            )
        ]
        paths = ["/hub/..", "/=ZOPE", "/=ZOPE/=b", "/=ZOPE/=b/=c", "/hub/../1"]
        with setControlPlaneClient(client), setCurrentService(
            "zope"
        ), setServiceMigrationContext(context):
            ZenPack("id").installServiceDefinitions(services, paths)
        self.assertEquals(
            [json.loads(a[1]) for a in context.added],
            [
                {
                    "Services": [{"Services": [], "Name": "e", "Tags": ["5"]}],
                    "Name": "a",
                    "Tags": ["1"],
                },
                {
                    "Services": [
                        {
                            "Services": [
                                {"Services": [], "Name": "d", "Tags": ["4"]}
                            ],
                            "Name": "c",
                            "Tags": ["3"],
                        }
                    ],
                    "Name": "b",
                    "Tags": ["2"],
                },
            ],
        )

    def testStopNoCurrentServiceId(self):
        moduleName = "Zenpacks.zenoss.Test"
        services = _services + [_MockService("me", "hub1", [moduleName])]
        client = _MockControlPlaneClient(services=services)
        with setControlPlaneClient(client):
            ZenPack("id").doServiceAction(moduleName, "stop")
        self.assertEquals(client.deleted, [])

    def testRemoveNoCurrentServiceId(self):
        moduleName = "Zenpacks.zenoss.Test"
        services = _services + [_MockService("me", "hub1", [moduleName])]
        client = _MockControlPlaneClient(services=services)
        with setControlPlaneClient(client):
            ZenPack("id").doServiceAction(moduleName, "delete")
        self.assertEquals(client.deleted, [])

    def testStopServices(self):
        tag = "MyZenPack"
        services = _services + [
            _MockService("alpha", "zenoss", [tag]),
            _MockService("beta", "hub1", [tag]),
        ]
        expected = ["alpha", "beta"]
        client = _MockControlPlaneClient(services=services)
        with setControlPlaneClient(client), setCurrentService("zope"):
            ZenPack("id").doServiceAction(tag, "stop")
        self.assertEquals(sorted(client.stopped), sorted(expected))

    def testRemoveServices(self):
        tag = "MyZenPack"
        services = _services + [
            _MockService("alpha", "zenoss", [tag]),
            _MockService("beta", "hub1", [tag]),
        ]
        expected = ["alpha", "beta"]
        client = _MockControlPlaneClient(services=services)
        with setControlPlaneClient(client), setCurrentService("zope"):
            ZenPack("id").doServiceAction(tag, "delete")
        self.assertEquals(sorted(client.deleted), sorted(expected))

    def testInstallFromFiles(self):
        tag = "myZenpack"
        # for this test only - associates path with service
        E_KEY = "expectedParentId"
        P_KEY = "servicePath"  # key defining path at which to install service
        D_KEY = "serviceDefinition"  # key defining service to be installed
        I_KEY = "Id"  # key defining ID
        N_KEY = "Name"  # key defining Name
        # Mock the filesystem - maps path->json file contents
        fileDict = {
            "a": {
                P_KEY: "/",
                D_KEY: {E_KEY: "zenoss", I_KEY: "a", N_KEY: "A"},
            },
            "b": {
                P_KEY: "/hub",
                D_KEY: {E_KEY: "hub1", I_KEY: "b", N_KEY: "B"},
            },
            "c": {
                P_KEY: "/hub",
                D_KEY: {E_KEY: "hub1", I_KEY: "c", N_KEY: "C"},
            },
        }
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        with setControlPlaneClient(client), setCurrentService(
            "zope"
        ), setServiceMigrationContext(context):
            z = ZenPack("id")
            z._loadServiceDefinition = createMockLoadServiceDefinitions(
                fileDict
            )
            z.getDaemonPath = lambda: "bin/foo"
            z.installServicesFromFiles(
                fileDict.keys(), [{}] * len(fileDict.keys()), tag
            )
        self.assertEquals(len(fileDict), len(context.added))
        for i, j in ((i[0], json.loads(i[1])) for i in context.added):
            self.assertEquals(i, j[E_KEY])

    def testConfigMap(self):
        tag = "myZenpack"
        fileDict = {
            "service.json": {
                "servicePath": "/",
                "serviceDefinition": {
                    "Name": "Svc",
                    "Id": "svc",
                    "ConfigFiles": {
                        "/opt/zenoss/etc/service.conf": {},
                        "/opt/zenoss/etc/other.conf": {},
                    },
                },
            },
        }
        configMap = {
            "/opt/zenoss/etc/service.conf": "foobar",
            "/opt/zenoss/etc/other.conf": "boofar",
        }
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        with setControlPlaneClient(client), setCurrentService(
            "zope"
        ), setServiceMigrationContext(context):
            z = ZenPack("id")
            z._loadServiceDefinition = createMockLoadServiceDefinitions(
                fileDict
            )
            z.getDaemonPath = lambda: "bin/foo"
            z.installServicesFromFiles(fileDict.keys(), [configMap], tag)
        self.assertEquals(len(fileDict), len(context.added))
        for _, j in ((i[0], json.loads(i[1])) for i in context.added):
            for key, val in configMap.iteritems():
                self.assertEquals(j["ConfigFiles"][key]["Content"], val)

    def testNormalizeServiceLogConfigs(self):
        sampleLogConfig = {
            "filters": ["supervisord"],
            "path": "/opt/zenoss/log/Z2.log",
            "type": "pythondaemon",
        }
        auditLogConfig = {
            "filters": ["supervisord"],
            "path": "/opt/zenoss/log/audit.log",
            "type": "zenossaudit",
        }
        tests = (
            {},
            {"LogConfigs": []},
            {"LogConfigs": [auditLogConfig]},
            {"LogConfigs": [sampleLogConfig]},
            {"LogConfigs": [sampleLogConfig, auditLogConfig]},
            {"LogConfigs": [auditLogConfig, sampleLogConfig]},
        )
        for service in tests:
            inputLength = len(service.get("LogConfigs", []))
            if auditLogConfig in service.get("LogConfigs", []):
                LogConfigs = ZenPack.normalizeService(service, {}, "")[
                    "LogConfigs"
                ]
                self.assertEquals(len(LogConfigs), inputLength)
            else:
                LogConfigs = ZenPack.normalizeService(service, {}, "")[
                    "LogConfigs"
                ]
                self.assertEquals(len(LogConfigs), inputLength + 1)
            self.assertIn(auditLogConfig, LogConfigs)

    def testNormalizeServiceTags(self):
        tag = "foobar"
        tests = ({}, {"Tags": ["some", "tags"]})
        for service in tests:
            tags = ZenPack.normalizeService(service, {}, tag)["Tags"]
            self.assertIn(tag, tags)

    def testNormalizeServiceImage(self):
        try:
            image = "foobar"
            os.environ["SERVICED_SERVICE_IMAGE"] = image
            tests = (({"ImageID": ""}, image), ({"ImageID": "xxx"}, "xxx"))
            for service, expected in tests:
                actual = ZenPack.normalizeService(service, {}, "")["ImageID"]
                self.assertEquals(actual, expected)
        finally:
            del os.environ["SERVICED_SERVICE_IMAGE"]

    def testNormalizeServiceConfig(self):
        service = {
            "ConfigFiles": {
                "missing": {},
                "empty": {"Content": ""},
                "present": {"Content": "present Content"},
            }
        }
        configMap = {"missing": "missing Content", "empty": "empty Content"}
        expected = dict(
            present=service["ConfigFiles"]["present"]["Content"], **configMap
        )
        configFiles = ZenPack.normalizeService(service, configMap, "")[
            "ConfigFiles"
        ]
        for key, value in configFiles.iteritems():
            self.assertEquals(expected[key], value["Content"])

    def testDirectoryConfigContents(self):
        fileDict = {"/foo/bar/baz/qux": "barge"}
        with setBuiltinOpen(fileDict):
            dcc = DirectoryConfigContents("/foo/bar")
            self.assertEquals(dcc["/baz/qux"], '"barge"')
            with self.assertRaises(KeyError):
                dcc["no_such_file"]
            with self.assertRaises(KeyError):
                dcc[1]

    def testNestedInstall(self):
        context = _MockServiceMigrationContext()
        client = _MockControlPlaneClient(services=_services)
        services = [
            json.dumps(_MockService(i), cls=_MockServiceEncoder)
            for i in ("svc1", "root", "svc2")
        ]
        paths = ["/=ROOT", "/", "/=ROOT"]
        with setControlPlaneClient(client), setCurrentService(
            "zope"
        ), setServiceMigrationContext(context):
            ZenPack("id").installServiceDefinitions(services, paths)
        root = json.loads(context.added[0][1])
        self.assertEquals(root["Name"], "ROOT")
        self.assertIn("SVC1", [s["Name"] for s in root["Services"]])
        self.assertIn("SVC2", [s["Name"] for s in root["Services"]])

    def testNestedStop(self):
        tag = "zp"
        _services = [
            _MockService("zenoss", "", []),
            _MockService("zope", "zenoss", ["daemon"]),
            _MockService("svc1", "root", [tag]),
            _MockService("root", "zenoss", [tag]),
            _MockService("svc2", "root", [tag]),
        ]
        client = _MockControlPlaneClient(services=_services)
        with setControlPlaneClient(client), setCurrentService("zope"):
            ZenPack("id").doServiceAction(tag, "stop")
        expected = ["root", "svc1", "svc2"]
        self.assertEquals(sorted(client.stopped), sorted(expected))
        # Confirm child services stopped before parent
        self.assertLess(
            client.stopped.index("svc1"), client.stopped.index("root")
        )
        self.assertLess(
            client.stopped.index("svc2"), client.stopped.index("root")
        )

    def testNestedRemove(self):
        tag = "zp"
        _services = [
            _MockService("zenoss", "", []),
            _MockService("zope", "zenoss", ["daemon"]),
            _MockService("svc1", "root", [tag]),
            _MockService("root", "zenoss", [tag]),
            _MockService("svc2", "root", [tag]),
        ]
        client = _MockControlPlaneClient(services=_services)
        with setControlPlaneClient(client), setCurrentService("zope"):
            ZenPack("id").doServiceAction(tag, "delete")
        expected = ["root", "svc1", "svc2"]
        self.assertEquals(sorted(client.deleted), sorted(expected))
        # Confirm child services deleted before parent
        self.assertLess(
            client.deleted.index("svc1"), client.deleted.index("root")
        )
        self.assertLess(
            client.deleted.index("svc2"), client.deleted.index("root")
        )


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestZenpackServices))
    return suite
