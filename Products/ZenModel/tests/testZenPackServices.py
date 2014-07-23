# #
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
# 
import functools
import os
import json
import cStringIO

from contextlib import contextmanager

import Globals
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.ZenPack import ZenPack, DirectoryConfigContents
import Products.ZenModel.ZenPack
import __builtin__

class _MockControlPlaneClient(object):
    def __call__(self, *args, **kwargs):
        return self
    def __init__(self, services=[], **kwargs):
        self._services = services
        self._added, self._deleted = [], []
    def queryServices(self, query):
        return self._services
    def deployService(self, parent, service):
        self._added.append((parent, service))
        svcDict = json.loads(service)
        self._services.append(_MockService(svcDict['Id'], parent, svcDict['Tags']))
    def deleteService(self, serviceId):
        self._deleted.append(serviceId)
    @property
    def added(self):
        return self._added
    @property
    def deleted(self):
        return self._deleted

class _MockService (object):
    def __init__(self, id, parentId = '', tags=[]):
        self.name = id.upper()
        self.id = id
        self.parentId = parentId
        self.tags = tags
        self.poolId= 'default'
    def toJsonDict(self):
        return dict(Id = self.id,
                    ParentId = self.parentId,
                    Tags = self.tags)

class _MockServiceEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, _MockService):
            return o.toJsonDict()
        return json.JSONEncoder.default(o)

_services = [
    _MockService('zenoss', '', []),
    _MockService('zope', 'zenoss', ['daemon']),
    _MockService('hub1', 'zenoss', ['hub']),
]

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

@contextmanager
def setBuiltinOpen(fileDict):
    try:
        builtin_open = __builtin__.open
        def _open(name, mode='r'):
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
        client = _MockControlPlaneClient(services=_services)
        service = json.dumps(_MockService('id'), cls=_MockServiceEncoder)
        with setControlPlaneClient(client):
            ZenPack("id").installServiceDefinitions(service, "/hub")
        self.assertEquals(client.added, [])

    def testAddSingleService(self):
        client = _MockControlPlaneClient(services=_services)
        service = _MockService('id','pid')
        service.poolId = 'not_default'
        service = json.dumps(service, cls=_MockServiceEncoder)
        with setControlPlaneClient(client), setCurrentService('zope'):
            ZenPack("id").installServiceDefinitions(service, "/hub")
        self.assertEquals(len(client.added), 1)
        parent, added = client.added[0][0], json.loads(client.added[0][1])
        self.assertEquals(added['Id'], 'id')
        self.assertEquals(parent, 'hub1')

    def testAddMultipleServices(self):
        client = _MockControlPlaneClient(services=_services)
        services = [json.dumps(_MockService(i), cls=_MockServiceEncoder)
                    for i in ('id1', 'id2')]
        paths = ['/', '/hub']
        with setControlPlaneClient(client), setCurrentService('zope'):
            ZenPack("id").installServiceDefinitions(services, paths)
        self.assertEquals(len(client.added), 2)
        added = [(i[0], json.loads(i[1])) for i in client.added]
        self.assertEquals(added[0][1]['Id'], 'id1')
        self.assertEquals(added[0][0], 'zenoss')
        self.assertEquals(added[1][1]['Id'], 'id2')
        self.assertEquals(added[1][0], 'hub1')

    def testRemoveNoCurrentServiceId(self):
        moduleName = "Zenpacks.zenoss.Test"
        services = _services + [_MockService('me','hub1',[moduleName])]
        client = _MockControlPlaneClient(services=services)
        with setControlPlaneClient(client):
            ZenPack("id").removeServices(moduleName)
        self.assertEquals(client.deleted, [])

    def testRemoveServices(self):
        tag =  'MyZenPack'
        services = _services + [
            _MockService('alpha', 'zenoss', [tag]),
            _MockService('beta', 'hub1', [tag]),
        ]
        expected = ['alpha', 'beta']
        client = _MockControlPlaneClient(services=services)
        with setControlPlaneClient(client), setCurrentService('zope'):
            ZenPack("id").removeServices(tag)
        self.assertEquals(sorted(client.deleted), sorted(expected))

    def testInstallFromFiles(self):
        tag = 'myZenpack'
        E_KEY = 'expectedParentId'  # for this test only - associates path with service
        P_KEY = 'servicePath'       # key defining path at which to install service
        D_KEY = 'serviceDefinition' # key defining service to be installed
        I_KEY = 'Id'                # key defining ID
        # Mock the filesystem - maps path->json file contents
        fileDict = dict (
            a={P_KEY: '/', D_KEY: {E_KEY:'zenoss', I_KEY:'a'}},
            b={P_KEY: '/hub', D_KEY: {E_KEY:'hub1', I_KEY:'b'}},
            c={P_KEY: '/hub', D_KEY: {E_KEY:'hub1', I_KEY:'c'}},
        )
        client = _MockControlPlaneClient(services=_services)
        with setControlPlaneClient(client), setCurrentService('zope'), setBuiltinOpen(fileDict):
            ZenPack('id').installServicesFromFiles(fileDict.keys(), [{}] * len(fileDict.keys()), tag)
        self.assertEquals(len(fileDict), len(client.added))
        for i,j in ((i[0],json.loads(i[1])) for i in client.added):
            self.assertEquals(i, j[E_KEY])

    def testConfigMap(self):
        tag='myZenpack'
        client = _MockControlPlaneClient(services=_services)
        fileDict = {
            "service.json":{
                'servicePath': '/',
                'serviceDefinition': {
                   'Id': 'svc',
                   'ConfigFiles': {
                       '/opt/zenoss/etc/service.conf': {},
                       '/opt/zenoss/etc/other.conf': {}
                   }
                }
            },
        }
        configMap = {
            '/opt/zenoss/etc/service.conf': "foobar",
            '/opt/zenoss/etc/other.conf': "boofar"
        }
        client = _MockControlPlaneClient(services=_services)
        with setControlPlaneClient(client), setCurrentService('zope'), setBuiltinOpen(fileDict):
            ZenPack('id').installServicesFromFiles(fileDict.keys(),
                                                   [configMap],
                                                   tag)
        self.assertEquals(len(fileDict), len(client.added))
        for i, j in ((i[0], json.loads(i[1])) for i in client.added):
            for key,val in configMap.iteritems():
                self.assertEquals(j['ConfigFiles'][key]['Content'], val)


    def testNormalizeServiceLogConfigs(self):
        sampleLogConfig = {
            'filters': ['supervisord'], 'path': '/opt/zenoss/log/Z2.log', 'type': 'pythondaemon'}
        auditLogConfig = {
            'filters': ['supervisord'], 'path': '/opt/zenoss/log/audit.log', 'type': 'zenossaudit'}
        tests = (
                {},
                {'LogConfigs':[]},
                {'LogConfigs':[auditLogConfig]},
                {'LogConfigs':[sampleLogConfig]},
                {'LogConfigs':[sampleLogConfig, auditLogConfig]},
                {'LogConfigs':[auditLogConfig, sampleLogConfig]}
        )
        for service in tests:
            inputLength = len(service.get('LogConfigs', []))
            if auditLogConfig in service.get('LogConfigs', []):
                LogConfigs = ZenPack.normalizeService(service, {}, '')['LogConfigs']
                self.assertEquals( len(LogConfigs), inputLength)
            else:
                LogConfigs = ZenPack.normalizeService(service, {}, '')['LogConfigs']
                self.assertEquals( len(LogConfigs), inputLength+1)
            self.assertIn(auditLogConfig, LogConfigs)

    def testNormalizeServiceTags(self):
        tag = 'foobar'
        tests = ({},{"Tags": ['some', 'tags']})
        for service in tests:
            tags = ZenPack.normalizeService(service, {}, tag)['Tags']
            self.assertIn(tag, tags)

    def testNormalizeServiceImage(self):
        try:
            image = 'foobar'
            os.environ['SERVICED_SERVICE_IMAGE'] = image
            tests = (({'ImageID':''}, image),
                     ({'ImageID':'xxx'}, 'xxx'))
            for service, expected in tests:
                actual = ZenPack.normalizeService(service, {}, '')['ImageID']
                self.assertEquals(actual, expected)
        finally:
            del os.environ['SERVICED_SERVICE_IMAGE']

    def testNormalizeServiceConfig(self):
        service = {'ConfigFiles': {
            'missing': {},
            'empty': {'Content':''},
            'present': {'Content': 'present Content'}
            }
        }
        configMap = {'missing': 'missing Content', 'empty': 'empty Content'}
        expected = dict(present=service['ConfigFiles']['present']['Content'], **configMap)
        configFiles = ZenPack.normalizeService(service, configMap, '')['ConfigFiles']
        for key, value in configFiles.iteritems():
            self.assertEquals(expected[key], value['Content'])

    def testDirectoryConfigContents(self):
        fileDict = {'/foo/bar/baz/qux': 'barge'}
        with setBuiltinOpen(fileDict):
            dcc = DirectoryConfigContents('/foo/bar')
            self.assertEquals(dcc['/baz/qux'], '"barge"')
            with self.assertRaises(KeyError): dcc['no_such_file']
            with self.assertRaises(KeyError): dcc[1]

    def testNestedInstall(self):
        client = _MockControlPlaneClient(services=_services)
        services = [json.dumps(_MockService(i), cls=_MockServiceEncoder)
                    for i in ('svc1', 'root', 'svc2')]
        paths = ['/=ROOT', '/', '/=ROOT']
        with setControlPlaneClient(client), setCurrentService('zope'):
            ZenPack("id").installServiceDefinitions(services, paths)
        # Confirm that parent is installed before children
        self.assertEquals(len(client.added), len(paths))
        for i,v  in enumerate(('root', 'svc', 'svc')):
            svc = json.loads(client.added[i][1])
            self.assertIn(v, svc['Id'])

    def testNestedRemove(self):
        tag = 'zp'
        _services = [
            _MockService('zenoss', '', []),
            _MockService('zope', 'zenoss', ['daemon']),
            _MockService('svc1', 'root', [tag]),
            _MockService('root', 'zenoss', [tag]),
            _MockService('svc2', 'root', [tag]),
        ]
        client = _MockControlPlaneClient(services=_services)
        with setControlPlaneClient(client), setCurrentService('zope'):
            ZenPack("id").removeServices(tag)
        expected = ['root', 'svc1', 'svc2']
        self.assertEquals(sorted(client.deleted), sorted(expected))
        # Confirm child services deleted before parent
        self.assertLess(client.deleted.index('svc1'), client.deleted.index('root'))
        self.assertLess(client.deleted.index('svc2'), client.deleted.index('root'))


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZenpackServices))
    return suite

