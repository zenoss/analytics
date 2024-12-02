##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.ShardedBTree import ShardedBTree, DEFAULT_N_SHARDS, default_hash_func

class TestShardedBTree(BaseTestCase):

    def bad_hash_func(self):
        return 0

    def test_creation(self):
        default_tree = ShardedBTree()
        self.assertEqual(len(default_tree.shards), DEFAULT_N_SHARDS)
        self.assertEqual(default_tree.n_shards, DEFAULT_N_SHARDS)
        self.assertEqual(default_tree.hash_func, default_hash_func)

        n_shards = 3
        tree = ShardedBTree(n_shards=n_shards, hash_func=self.bad_hash_func)
        self.assertEqual(len(tree.shards), n_shards)
        self.assertEqual(tree.n_shards, n_shards)
        self.assertEqual(tree.hash_func, self.bad_hash_func)

    def test_hashing(self):
        data = "this should always be hashed to the same value"
        hashed = default_hash_func(data)
        for i in xrange(100):
            self.assertEqual(hashed, default_hash_func(data))

    def _get_fake_data(self, n_elements=1000):
        data = {}
        tree = ShardedBTree()
        for i in xrange(n_elements):
            key = "key_{}".format(i)
            value = "value_{}".format(i)
            tree[key] = value
            data[key] = value
        return data, tree

    def test_resize(self):
        data, tree = self._get_fake_data()
        sizes = [ 10, 100, 15, 250, 1500 ]
        for size in sizes:
            tree.resize(size)
            self.assertTrue(len(tree) == len(data))
            self.assertEqual(tree.n_shards, size)
            self.assertEqual(len(tree.shards), size)
            for key, val in data.iteritems():
                self.assertEqual(tree[key], val)

    def test_dict_ops(self):
        """ Test the dict-like operations """
        n_elements = 1000
        # get fake data
        data, tree = self._get_fake_data(n_elements)
        # __len__
        self.assertEqual(len(tree), len(data))
        # __setitem__ and __getitem__
        for key, val in data.iteritems():
            self.assertEqual(tree[key], val)
        tree[None] = 42
        self.assertEqual(tree[None], None)
        # get
        a_key = data.iterkeys().next()
        self.assertTrue(tree.has_key(a_key))
        self.assertFalse(tree.has_key("bad_key")) 
        self.assertFalse(tree.has_key(None))
        self.assertEqual(tree.get(a_key), data[a_key])
        self.assertEqual(tree.get("bad_key"), None)
        self.assertEqual(tree.get(None), None)
        self.assertEqual(tree.get("bad_key", "default value"), "default value")
        self.assertEqual(tree.get(None, "default value"), "default value")
        # __delitem__ and has_key
        a_key = data.iterkeys().next()
        self.assertTrue(tree.has_key(a_key))
        del tree[a_key]
        self.assertFalse(tree.has_key(a_key))
        del data[a_key]
        self.assertEqual(len(tree), len(data))
        del tree[None]
        # keys, values and items
        self.assertEqual(set(data.keys()), set(tree.keys()))
        self.assertEqual(set(data.values()), set(tree.values()))
        self.assertEqual(set(data.items()), set(tree.items()))
        # iterkeys, itervalues and iteritems
        self.assertEqual(set(data.iterkeys()), set(tree.iterkeys()))
        self.assertEqual(set(data.itervalues()), set(tree.itervalues()))
        self.assertEqual(set(data.iteritems()), set(tree.iteritems()))
        # __contains__
        another_key = data.iterkeys().next()
        self.assertTrue(another_key in tree)
        # __iter__
        for key in tree:
            self.assertTrue(data.has_key(key))
        # update
        new_data = { "hello": "world", "hola": "mundo" }
        tree.update(new_data)
        for k in new_data:
            self.assertTrue(tree.has_key(k))
            self.assertEqual(tree[k], new_data[k])
        as_expected = False
        try:
            tree.update("this thing doesnt have iteritems")
        except TypeError:
            as_expected = True
        self.assertTrue(as_expected)
        # clear
        tree.clear()
        self.assertEqual(len(tree), 0)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestShardedBTree))
    return suite

