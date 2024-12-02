##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.ZenUtils.MultiPathIndex import MultiPathIndex

class Dummy:

    meta_type="foo"

    def __init__( self, path):
        if isinstance(path, basestring):
            path = (path,)
        finalpath = []
        for p in path:
            if not p.startswith('/zport/dmd'):
                p = '/zport/dmd/' + p.lstrip('/')
            finalpath.append(p)
        self.path = finalpath

    def __str__( self ):
        return '<Dummy: %s>' % self.path

    __repr__ = __str__


class MultiPathIndexTests(BaseTestCase):
    """ Test MultiPathIndex objects """

    def afterSetUp(self):
        super(MultiPathIndexTests, self).afterSetUp()
        self._index = MultiPathIndex( 'path' )
        self._values = {
          1 : Dummy("/aa/aa/aa/1.html"),
          2 : Dummy("/aa/aa/bb/2.html"),
          3 : Dummy("/aa/aa/cc/3.html"),
          4 : Dummy("/aa/bb/aa/4.html"),
          5 : Dummy("/aa/bb/bb/5.html"),
          6 : Dummy("/aa/bb/cc/6.html"),
          7 : Dummy("/aa/cc/aa/7.html"),
          8 : Dummy("/aa/cc/bb/8.html"),
          9 : Dummy("/aa/cc/cc/9.html"),
          10 : Dummy("/bb/aa/aa/10.html"),
          11 : Dummy("/bb/aa/bb/11.html"),
          12 : Dummy("/bb/aa/cc/12.html"),
          13 : Dummy("/bb/bb/aa/13.html"),
          14 : Dummy("/bb/bb/bb/14.html"),
          15 : Dummy("/bb/bb/cc/15.html"),
          16 : Dummy("/bb/cc/aa/16.html"),
          17 : Dummy("/bb/cc/bb/17.html"),
          18 : Dummy("/bb/cc/cc/18.html"),
          19 : Dummy(["/bb/cc/cc/19.html",
                     "/aa/cc/cc/19.html"])
        }

    def _populateIndex(self):
        for k, v in self._values.items():
            self._index.index_object( k, v )

    def testEmpty(self):
        self.assertEqual(self._index.numObjects() ,0)
        self.assertEqual(self._index.getEntryForObject(1234), None)
        self._index.unindex_object( 1234 ) # nothrow
        self.assertEqual(self._index._apply_index({"suxpath":"xxx"}), None)

    def testUnIndex(self):
        self._populateIndex()
        self.assertEqual(self._index.numObjects(), 19)

        for k in self._values.keys():
            self._index.unindex_object(k)

        self.assertEqual(self._index.numObjects(), 0)
        self.assertEqual(len(self._index._index), 0)
        self.assertEqual(len(self._index._unindex), 0)

    def testReindex(self):
        self._populateIndex()
        self.assertEqual(self._index.numObjects(), 19)

        o = Dummy('/foo/bar')
        self._index.index_object(20, o)
        self.assertEqual(self._index.numObjects(), 20)
        self._index.index_object(20, o)
        self.assertEqual(self._index.numObjects(), 20)

    def testUnIndexError(self):
        self._populateIndex()
        # this should not raise an error
        self._index.unindex_object(-1)

        # nor should this
        self._index._unindex[1] = set(["/broken/thing"])
        self._index.unindex_object(1)

    def testRoot(self):

        self._populateIndex()
        tests = ( ("/",0, range(1,20)), )

        for comp,level,results in tests:
            path = '/'
            res = self._index._apply_index(
                {"path":{'query':path,"level":level}})
            lst = list(res[0].keys())
            self.assertEqual(lst,results)

        for comp,level,results in tests:
            path = '/'
            res = self._index._apply_index(
                {"path":{'query':( (path,level),)}})
            lst = list(res[0].keys())
            self.assertEqual(lst,results)

    def testSimpleTests(self):

        self._populateIndex()
        tests = [
            ("/zport/dmd/aa", 0, [1,2,3,4,5,6,7,8,9,19]),
            ("/zport/dmd/bb", 0, [10,11,12,13,14,15,16,17,18,19]),
            ("/zport/dmd/bb/cc", 0, [16,17,18,19] ),
            ("/zport/dmd/bb/aa", 0, [10,11,12] ),
        ]

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':path,"level":level}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)

        for comp,level,results in tests:
            for path in [comp,"/"+comp,"/"+comp+"/"]:
                res = self._index._apply_index(
                                    {"path":{'query':( (path,level),)}})
                lst = list(res[0].keys())
                self.assertEqual(lst,results)

    def testQueryPathReturnedInResult(self):

        index = self._index
        index.index_object(1, Dummy("/ff"))
        index.index_object(2, Dummy("/ff/gg"))
        index.index_object(3, Dummy("/ff/gg/3.html"))
        index.index_object(4, Dummy("/ff/gg/4.html"))
        res = index._apply_index({'path': {'query': '/zport/dmd/ff/gg'}})
        lst = list(res[0].keys())
        self.assertEqual(lst, [2, 3, 4])
    
    def testAddingPathsIndividually(self):
        index = self._index
        index.index_object(1, Dummy("/ff"))
        index.index_object(2, Dummy("/ff/gg"))
        index.index_object(3, Dummy("/ff/gg/3.html"))
        index.index_object(4, Dummy("/ff/gg/4.html"))
        index.index_paths(4, ('/zport/dmd/aa/bb/4.html','/zport/dmd/ff'))
        res1 = index._apply_index({'path': {'query': '/zport/dmd/aa/bb'}})
        res2 = index._apply_index({'path': {'query': '/zport/dmd/ff/gg'}})
        res3 = index._apply_index({'path': {'query': '/zport/dmd/ff'}})
        self.assertEqual(list(res1[0].keys()), [4]);
        self.assertEqual(list(res2[0].keys()), [2, 3, 4]);
        self.assertEqual(list(res3[0].keys()), [1, 2, 3, 4]);

        # res = index._apply_index({'path': {'query': '/zport/dmd', 'depth':1}})
        # self.assertEqual(list(res[0].keys()), [1, 4]);
        res = index._apply_index({'path': {'query': '/zport/dmd/ff', 'depth':0}})
        self.assertEqual(list(res[0].keys()), [4]);
        # res = index._apply_index({'path': {'query': '/zport/dmd/ff', 'depth':1}})
        # self.assertEqual(list(res[0].keys()), [2]);
        # res = index._apply_index({'path': {'query': '/zport/dmd/ff', 'depth':2}})
        # self.assertEqual(list(res[0].keys()), [2, 3, 4]);

    def testUnindexIndividualPaths(self):
        index = self._index
        index.index_object(1, Dummy("/ff"))
        index.index_paths(1, ('/zport/dmd/a/b/c', '/zport/dmd/a/b/b'))
        index.unindex_paths(1, ('/zport/dmd/a/b/c',))
        res = index._apply_index({'path':{'query':'/zport/dmd/a/b/c'}})[0].keys()
        self.assertEqual(list(res), [])
        res = index._apply_index({'path':{'query':'/zport/dmd/a/b/b'}})[0].keys()
        self.assertEqual(list(res), [1])
        res = index._apply_index({'path':{'query':'/zport/dmd/ff'}})[0].keys()
        self.assertEqual(list(res), [1])

    def testUnindexIndividualPathError(self):
        index = self._index
        index.index_object(1, Dummy("/ff"))
        # This should not throw an error
        index.unindex_paths(1, ('/zport/dmd/a/b/c',))

    def testNoStalePathsAfterUnindex(self):
        index = self._index
        index.index_object(1, Dummy('/ff'))
        index.index_object(1, Dummy('/aa'))
        self.assertEqual(list(index._unindex[1]), ['/zport/dmd/aa'])

    def testSimilarPaths(self):
        index = self._index
        index.index_object(1, Dummy('/zport/dmd/Devices/VMware/devices/MyDevice'))
        index.index_object(2, Dummy(['/zport/dmd/Manufacturers/VMware/vmware-tools/MyDevice2',
                                    '/zport/dmd/Devices/Server/devices/MyDevice2']))
        res = index._apply_index({'path':{'query':'/zport/dmd/Devices/VMware'}})[0].keys()
        self.assertEqual(list(res), [1])


def test_suite():
    return unittest.makeSuite(MultiPathIndexTests)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
