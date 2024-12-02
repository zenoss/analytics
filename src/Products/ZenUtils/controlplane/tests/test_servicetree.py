# #
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
# 
import unittest

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.controlplane.servicetree import ServiceTree


class _MockService (object):
    def __init__(self, id, parentId, tags):
        self.name = id.upper()
        self.id = id
        self.parentId = parentId
        self.tags = tags

_services = [
    _MockService('zenoss', '', []),
    _MockService('zope', 'zenoss', ['daemon']),
    _MockService('hub1', 'zenoss', ['hub']),
    _MockService('zenhub', 'hub1', ['daemon', 'hub']),
    _MockService('collector1', 'hub1', ['collector']),
    _MockService('zenping', 'collector1', ['collector', 'daemon']),
    _MockService('collector2', 'hub1', ['collector']),
    _MockService('zencommand', 'collector2', ['collector', 'daemon']),
    _MockService('hub2', 'zenoss', ['hub']),
    _MockService('collector3', 'hub2', ['collector']),
]
# zenoss
#   zope
#   hub1
#       zenhub
#       collector1
#           zenping
#       collector2
#           zencommand
#   hub2
#       collector3
class ServiceTreeTest(BaseTestCase):
    """
    """
    def testGetServices(self):
        tree=ServiceTree(_services)
        for i in _services:
            self.assertEqual(tree.getService(i.id), i)

    def testGetChildren(self):
        _children = (
            ('zenoss', ('zope', 'hub1', 'hub2')),
            ('zope', ()),
            ('hub1', ('zenhub', 'collector1', 'collector2')),
            ('zenhub', ()),
            ('collector1', ('zenping',)),
            ('zenping', ()),
        )
        tree=ServiceTree(_services)
        for service, expectedChildren in (_children):
            children = [i.id for i in tree.getChildren(service)]
            self.assertEqual(sorted(children), sorted(expectedChildren),
                             '%s != %s' %(sorted(children),sorted(expectedChildren)))

    def testMatchPathBadService(self):
        tree=ServiceTree(_services)
        with self.assertRaises(LookupError):
            tree.matchServicePath('BadServiceId', '/')

    def testMatchPathParent(self):
        tree = ServiceTree(_services)
        for i in _services:
            parentId = i.parentId if i.parentId else i.id
            expected = [tree.getService(parentId)]
            result = tree.matchServicePath(i.id, '..')
            self.assertEqual(result, expected)

    def testMatchPathTag(self):
        tests = (
            ('zenoss', 'daemon',('zope',)),
            ('zenoss', 'hub',('hub1','hub2')),
            ('zenoss', 'xxx',()),
        )
        tree = ServiceTree(_services)
        for service, tag, expected in tests:
            result = (i.id for i in tree.matchServicePath(service, tag))
            self.assertEqual (sorted(result), sorted(expected))

    def testMatchPathRoot(self):
        tree = ServiceTree(_services)
        expected = ['zenoss']
        for service in ('zenoss', 'zope', 'zenping'):
            result = [i.id for i in tree.matchServicePath(service, '/')]
            self.assertEqual(result, expected)

    def testMatchPathCwd(self):
        tree = ServiceTree(_services)
        for service in ('zenoss', 'zope', 'zenping'):
            result = [i.id for i in tree.matchServicePath(service, '.')]
            self.assertEqual(result, [service])

    def testMatchPathName(self):
        tests = (
            ('zope', '/=ZOPE', ('zope',)),
            ('zenoss', '=HUB1', ('hub1',)),
            ('zope', '=HUB1', ()),
        )
        tree = ServiceTree(_services)
        for service, tag, expected in tests:
            result = (i.id for i in tree.matchServicePath(service, tag))
            self.assertEqual(sorted(result), sorted(expected))

    def testMatchPathComplex(self):
        tree = ServiceTree(_services)
        tests = (
            ('zenping', '../../hub', ('zenhub',)),
            ('zope', '../hub/collector', ('collector1','collector2', 'collector3')),
            ('hub1', './hub', ('zenhub',)),
            ('zope', '/', ('zenoss',)),
            ('zope', '/hub/collector', ('collector1','collector2', 'collector3')),
            ('zope', '/hub/=COLLECTOR1', ('collector1',)),
            ('zope', '/=HUB1/collector', ('collector1','collector2')),
        )
        for service, path, expected in tests:
            result = (i.id for i in tree.matchServicePath(service, path))
            self.assertEqual (sorted(result), sorted(expected),
                              "cwd:%s path:%s"%(service, path))

    def testFindMatchingServices(self):
        tree = ServiceTree(_services)
        tests = (
            ('zenoss', 'collector', ('zenping', 'collector1', 'zencommand', 'collector2', 'collector3')),
            ('hub1', 'collector', ('zenping', 'collector1', 'zencommand', 'collector2')),
            ('zenoss', '=HUB1', ('hub1',)),
        )
        for service, pattern, expected in tests:
            root = tree.getService(service)
            result = [i.id for i in tree.findMatchingServices(root, pattern)]
            self.assertEqual(sorted(result), sorted(expected))

    def testGetPath(self):
        tree = ServiceTree(_services)
        tests = (('zenoss', '/zenoss'),
                 ('zenping', '/zenoss/hub1/collector1/zenping'))
        for service, expected in tests:
            path = tree.getPath(tree.getService(service))
            actual = '/'+'/'.join(i.id for i in path)
            self.assertEqual(actual, expected)


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ServiceTreeTest),))


if __name__ == "__main__":
    unittest.main(default="test_suite")