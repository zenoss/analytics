##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from copy import deepcopy
from toposort import toposort_flatten
from Products.ZenUtils.zenpack import topo_prioritize

class TestTopoPrioritize(unittest.TestCase):
    """Test topo_prioritize routine."""

    def testSimple(self):
        graph = {1: set(),
                 2: set()}
        expected = deepcopy(graph)
        expected[1].add(2)
        topo_prioritize(2, graph)
        self.assertEquals(graph, expected)
        sorted = toposort_flatten(graph)
        self.assertEqual(toposort_flatten(graph), [2, 1])


    def testAlreadyPrioritized(self):
        graph = {1: set([2]),
                 2: set()}
        expected = deepcopy(graph)
        topo_prioritize(2, graph)
        self.assertEquals(graph, expected)
        sorted = toposort_flatten(graph)
        self.assertEqual(toposort_flatten(graph), [2, 1])

    def testAvoidCircularReference(self):
        graph = {1: set(),
                 2: set([1])}
        expected = deepcopy(graph)
        topo_prioritize(2, graph)
        self.assertEquals(graph, expected)
        sorted = toposort_flatten(graph)
        self.assertEqual(toposort_flatten(graph), [1, 2])

    def testMiddle(self):
        #
        graph = {1: set(),
                 2: set([3]),
                 3: set()}
        expected = deepcopy(graph)
        expected[1].add(2)
        topo_prioritize(2, graph)
        self.assertEquals(graph, expected)
        self.assertEqual(toposort_flatten(graph), [3, 2, 1])

    def testComplex(self):
        # 1, 2->3->4->5, 2->5, (6,7)->8,
        graph = {1: set(),
                 2: set([3,5]),
                 3: set([4]),
                 4: set([5]),
                 5: set(),
                 6: set([8]),
                 7: set([8]),
                 8: set(),
        }
        expected = deepcopy(graph)
        for i in (1,6,7,8):
            expected[i].add(2)
        topo_prioritize(2, graph)
        self.assertEquals(graph, expected)
        sorted = toposort_flatten(graph)
        for i in (1,6,7,8):
            self.assertLess(sorted.index(2), sorted.index(i))
        for i in (3,4,5):
            self.assertLess(sorted.index(i), sorted.index(2))


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestTopoPrioritize),))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
