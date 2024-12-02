##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.FunctionCache import FunctionCache, _compose_key
import cPickle as pickle


class FunctionCacheTest(BaseTestCase):
    """ Tests the FunctionCache decorator"""

    decorated_function_call_count = 0

    def testCache(self):
        self.assertEqual(1, 1)

        cache_key = "test_function_cache"

        @FunctionCache(cache_key, cache_miss_marker=-1, default_timeout=5)
        def decorated_function(argument):
            FunctionCacheTest.decorated_function_call_count += 1
            return argument

        test_argument = 100
        hashKey = _compose_key(cache_key, [test_argument], {})

        client, timeout = FunctionCache(cache_key, -1, 5).getCacheClient()

        if client is None:
            # alas. no applicationcache or zodb-cacheservers configured
            return

        # cache is as of yet unused, ergo ...
        self.assertEqual(None, client.get(hashKey))
        self.assertEqual(0, FunctionCacheTest.decorated_function_call_count)
        # make sure we have a valid memcached connection before we fail on asserts
        if not client.stats:            
            return
        
        # on first call of decorated_function(), cache should miss so
        # decorated_function_call_count should increment.
        decorated_function(test_argument)
        self.assertEqual(test_argument, pickle.loads(client.get(hashKey)))
        self.assertEqual(1, FunctionCacheTest.decorated_function_call_count)

        # on second call of decorated_function(), cache should hit so
        # decorated_function_call_count should not increment.
        decorated_function(test_argument)
        self.assertEqual(test_argument, pickle.loads(client.get(hashKey)))
        self.assertEqual(1, FunctionCacheTest.decorated_function_call_count)

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(FunctionCacheTest),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
