##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import unittest
from Products.ZenUtils.keyedset import KeyedSet

def firstLetter(s):
    return s[0].lower()

class KeyedSetTest(unittest.TestCase):
    """Tests KeyedSet methods"""

    def testKeys(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        self.assertEqual(sorted(ks.keys()), ["a","b"])


    def testIterkeys(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        keys = []
        for key in ks.iterkeys():
            keys.append(key)
        self.assertEqual(sorted(keys), ["a","b"])


    def testHasKey(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        self.assertTrue(ks.has_key("a"))
        self.assertTrue(ks.has_key("b"))
        self.assertFalse(ks.has_key("c"))


    def testSubsetByKey(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        self.assertEqual(ks.subset_by_key('a'), set(['apple','avocado']))
        self.assertEqual(ks.subset_by_key('b'), set(['banana']))
        self.assertEqual(ks.subset_by_key('c'), set())


    def testPopByKey(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        popped = []
        popped.append(ks.pop_by_key('a'))
        popped.append(ks.pop_by_key('a'))
        self.assertEqual(sorted(popped), ['apple','avocado'])
        self.assertEqual(ks.subset_by_key('a'), set())
        self.assertEqual(ks, set(['banana']))
        self.assertEqual(ks.pop_by_key('b'), 'banana')
        self.assertTrue(not ks)
        try:
            ks.pop_by_key('a')
        except KeyError:
            self.assertTrue(True)
        except Exception:
            self.assertTrue(False)
        else:
            self.assertTrue(False)


    def testDiscardByKey(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        discarded = ks.discard_by_key('a')
        self.assertEqual(discarded, set(['apple','avocado']))
        self.assertEqual(ks.subset_by_key('a'), set())
        self.assertEqual(ks, set(['banana']))
        self.assertEqual(ks.discard_by_key('b'), set(['banana']))
        self.assertTrue(not ks)
        try:
            self.assertEqual(ks.discard_by_key('a'), set())
        except Exception:
            self.assertTrue(False)


    def testAdd(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        for item in ["apple", "acacia", "cheese"]:
            ks.add(item)
        self.assertEqual(ks, set(["apple", "avocado", "banana", "acacia", "cheese"]))

        # Proper key sets
        self.assertEqual(sorted(ks.keys()), ['a','b','c'])
        self.assertEqual(ks.subset_by_key("a"), set(["apple", "avocado", "acacia"]))
        self.assertEqual(ks.subset_by_key("b"), set(["banana"]))
        self.assertEqual(ks.subset_by_key("c"), set(["cheese"]))
        self.assertEqual(ks.subset_by_key("d"), set())


    def testRemove(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        for item in ["apple", "banana"]:
            ks.remove(item)
        for item in ["acacia", "cheese"]:
            try:
                ks.remove(item)
            except KeyError:
                self.assertTrue(True)
            except Exception:
                self.assertTrue(False)
            else:
                self.assertTrue(False)
        self.assertEqual(ks, set(["avocado"]))

        # Proper key sets
        self.assertEqual(ks.keys(), ['a'])
        self.assertEqual(ks.subset_by_key("a"), set(["avocado"]))
        self.assertEqual(ks.subset_by_key("b"), set())
        self.assertEqual(ks.subset_by_key("c"), set())


    def testDiscard(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        for item in ["apple", "acacia", "banana", "cheese"]:
            ks.discard(item)
        self.assertEqual(ks, set(["avocado"]))

        # Proper key sets
        self.assertEqual(ks.keys(), ['a'])
        self.assertEqual(ks.subset_by_key("a"), set(["avocado"]))
        self.assertEqual(ks.subset_by_key("b"), set())
        self.assertEqual(ks.subset_by_key("c"), set())


    def testPop(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        popped = []
        while ks:
            popped.append(ks.pop())
        self.assertEqual(sorted(popped), ["apple", "avocado", "banana"])
        self.assertEqual(ks.subset_by_key("a"), set())
        self.assertEqual(ks.subset_by_key("b"), set())


    def testClear(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        self.assertFalse(not ks)
        self.assertEqual(len(ks), 3)
        ks.clear()
        self.assertEqual(len(ks), 0)
        self.assertTrue(not ks)
        self.assertEqual(ks.subset_by_key("a"), set())
        self.assertEqual(ks.subset_by_key("b"), set())


    def testCopy(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        ks2 = ks.copy()
        self.assertEqual(sorted(ks), ["apple", "avocado", "banana"])
        self.assertEqual(sorted(ks2), ["apple", "avocado", "banana"])
        self.assertEqual(sorted(ks.keys()), ["a","b"])
        self.assertEqual(sorted(ks2.keys()), ["a","b"])
        ks2.add("acacia")
        ks2.add("cheese")
        ks2.remove("banana")
        self.assertEqual(sorted(ks), ["apple", "avocado", "banana"])
        self.assertEqual(sorted(ks2), ["acacia", "apple", "avocado", "cheese"])
        self.assertEqual(sorted(ks.keys()), ["a","b"])
        self.assertEqual(sorted(ks2.keys()), ["a","c"])
        self.assertEqual(ks2.subset_by_key("a"), set(["acacia", "apple", "avocado"]))
        self.assertEqual(ks2.subset_by_key("b"), set())
        self.assertEqual(ks2.subset_by_key("c"), set(["cheese"]))


    def testIntersection(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        ks2 = KeyedSet(firstLetter, ["apple", "acacia", "banana", "cheese"])
        more = ["apple", "cheese", "durian"]
        result = ks.intersection(ks2, more)
        self.assertEqual(result, set(["apple"]))

        # No side-effects
        self.assertEqual(ks, set(["apple", "avocado", "banana"]))
        self.assertEqual(ks2, set(["apple", "acacia", "banana", "cheese"]))
        self.assertEqual(more, ['apple', 'cheese', 'durian'])
        
        # Proper key sets
        self.assertEqual(sorted(result.keys()), ['a'])
        self.assertEqual(result.subset_by_key("a"), set(["apple"]))
        self.assertEqual(result.subset_by_key("b"), set())
        self.assertEqual(result.subset_by_key("c"), set())
        self.assertEqual(result.subset_by_key("d"), set())

        # _update
        copy = ks.copy()
        copy.intersection_update(ks2, more)

        # No unintended side-effects
        self.assertEqual(ks2, set(["apple", "acacia", "banana", "cheese"]))
        self.assertEqual(more, ['apple', 'cheese', 'durian'])

        self.assertEqual(result, copy)
        self.assertEqual(sorted(result.keys()), sorted(copy.keys()))
        for key in result.keys():
            self.assertEqual(result.subset_by_key(key), copy.subset_by_key(key))


    def testUnion(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        ks2 = KeyedSet(firstLetter, ["apple", "acacia"])
        more = ['apple', 'cheese']
        result = ks.union(ks2,more)
        self.assertEqual(result, set(["apple", "avocado", "banana", "acacia", "cheese"]))

        # No side-effects
        self.assertEqual(ks, set(["apple", "avocado", "banana"]))
        self.assertEqual(ks2, set(["apple", "acacia"]))
        self.assertEqual(more, ['apple', 'cheese'])
        
        # Proper key sets
        self.assertEqual(sorted(result.keys()), ['a','b','c'])
        self.assertEqual(result.subset_by_key("a"), set(["apple", "avocado", "acacia"]))
        self.assertEqual(result.subset_by_key("b"), set(["banana"]))
        self.assertEqual(result.subset_by_key("c"), set(["cheese"]))
        self.assertEqual(result.subset_by_key("d"), set())

        # update
        copy = ks.copy()
        copy.update(ks2, more)
        
        # No unintended side-effects
        self.assertEqual(ks2, set(["apple", "acacia"]))
        self.assertEqual(more, ['apple', 'cheese'])

        self.assertEqual(result, copy)
        self.assertEqual(sorted(result.keys()), sorted(copy.keys()))
        for key in result.keys():
            self.assertEqual(result.subset_by_key(key), copy.subset_by_key(key))


    def testDifference(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        ks2 = KeyedSet(firstLetter, ["apple", "acacia"])
        more = ["banana", "cheese"]
        result = ks.difference(ks2, more)
        self.assertEqual(result, set(["avocado"]))

        # No side-effects
        self.assertEqual(ks, set(["apple", "avocado", "banana"]))
        self.assertEqual(ks2, set(["apple", "acacia"]))
        self.assertEqual(more, ["banana", "cheese"])
        
        # Proper key sets
        self.assertEqual(result.keys(), ['a'])
        self.assertEqual(result.subset_by_key("a"), set(["avocado"]))
        self.assertEqual(result.subset_by_key("b"), set())
        self.assertEqual(result.subset_by_key("c"), set())

        # _update
        copy = ks.copy()
        copy.difference_update(ks2, more)

        # No unintended side-effects
        self.assertEqual(ks2, set(["apple", "acacia"]))
        self.assertEqual(more, ["banana", "cheese"])

        self.assertEqual(result, copy)
        self.assertEqual(sorted(result.keys()), sorted(copy.keys()))
        for key in result.keys():
            self.assertEqual(result.subset_by_key(key), copy.subset_by_key(key))


    def testSymmetricDifference(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana", "cheese"])
        other = ["apple", "acacia", "banana", "durian"]
        result = ks.symmetric_difference(other)
        self.assertEqual(result, set(["acacia", "avocado", "cheese", "durian"]))

        # No side-effects
        self.assertEqual(ks, set(["apple", "avocado", "banana", "cheese"]))
        self.assertEqual(other, ["apple", "acacia", "banana", "durian"])
        
        # Proper key sets
        self.assertEqual(result.keys(), ['a','c','d'])
        self.assertEqual(result.subset_by_key("a"), set(["acacia", "avocado"]))
        self.assertEqual(result.subset_by_key("b"), set())
        self.assertEqual(result.subset_by_key("c"), set(["cheese"]))
        self.assertEqual(result.subset_by_key("d"), set(["durian"]))

        # _update
        copy = ks.copy()
        copy.symmetric_difference_update(other)

        # No unintended side-effects
        self.assertEqual(other, ["apple", "acacia", "banana", "durian"])

        self.assertEqual(result, copy)
        self.assertEqual(sorted(result.keys()), sorted(copy.keys()))
        for key in result.keys():
            self.assertEqual(result.subset_by_key(key), copy.subset_by_key(key))


    def testAnd(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        ks2 = KeyedSet(firstLetter, ["apple", "acacia", "cheese"])
        result = ks & ks2
        self.assertEqual(result, set(["apple"]))

        # No side-effects
        self.assertEqual(ks, set(["apple", "avocado", "banana"]))
        self.assertEqual(ks2, set(["apple", "acacia", "cheese"]))
        
        # Proper key sets
        self.assertEqual(sorted(result.keys()), ['a'])
        self.assertEqual(result.subset_by_key("a"), set(["apple"]))
        self.assertEqual(result.subset_by_key("b"), set())
        self.assertEqual(result.subset_by_key("c"), set())

        # _update
        copy = ks.copy()
        copy &= ks2

        # No unintended side-effects
        self.assertEqual(ks2, set(["apple", "acacia", "cheese"]))

        self.assertEqual(result, copy)
        self.assertEqual(sorted(result.keys()), sorted(copy.keys()))
        for key in result.keys():
            self.assertEqual(result.subset_by_key(key), copy.subset_by_key(key))


    def testOr(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        ks2 = KeyedSet(firstLetter, ["apple", "acacia", "cheese"])
        result = ks | ks2
        self.assertEqual(result, set(["apple", "avocado", "banana", "acacia", "cheese"]))

        # No side-effects
        self.assertEqual(ks, set(["apple", "avocado", "banana"]))
        self.assertEqual(ks2, set(["apple", "acacia", "cheese"]))
        
        # Proper key sets
        self.assertEqual(sorted(result.keys()), ['a','b','c'])
        self.assertEqual(result.subset_by_key("a"), set(["apple", "avocado", "acacia"]))
        self.assertEqual(result.subset_by_key("b"), set(["banana"]))
        self.assertEqual(result.subset_by_key("c"), set(["cheese"]))
        self.assertEqual(result.subset_by_key("d"), set())

        # update
        copy = ks.copy()
        copy |= ks2
        
        # No unintended side-effects
        self.assertEqual(ks2, set(["apple", "acacia", "cheese"]))

        self.assertEqual(result, copy)
        self.assertEqual(sorted(result.keys()), sorted(copy.keys()))
        for key in result.keys():
            self.assertEqual(result.subset_by_key(key), copy.subset_by_key(key))


    def testSub(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana"])
        ks2 = KeyedSet(firstLetter, ["apple", "acacia", "banana", "cheese"])
        result = ks - ks2
        self.assertEqual(result, set(["avocado"]))

        # No side-effects
        self.assertEqual(ks, set(["apple", "avocado", "banana"]))
        self.assertEqual(ks2, set(["apple", "acacia", "banana", "cheese"]))
        
        # Proper key sets
        self.assertEqual(result.keys(), ['a'])
        self.assertEqual(result.subset_by_key("a"), set(["avocado"]))
        self.assertEqual(result.subset_by_key("b"), set())
        self.assertEqual(result.subset_by_key("c"), set())

        # _update
        copy = ks.copy()
        copy -= ks2

        # No unintended side-effects
        self.assertEqual(ks2, set(["apple", "acacia", "banana", "cheese"]))

        self.assertEqual(result, copy)
        self.assertEqual(sorted(result.keys()), sorted(copy.keys()))
        for key in result.keys():
            self.assertEqual(result.subset_by_key(key), copy.subset_by_key(key))


    def testXor(self):
        ks = KeyedSet(firstLetter, ["apple", "avocado", "banana", "cheese"])
        ks2 = KeyedSet(firstLetter, ["apple", "acacia", "banana", "durian"])
        result = ks ^ ks2
        self.assertEqual(result, set(["acacia", "avocado", "cheese", "durian"]))

        # No side-effects
        self.assertEqual(ks, set(["apple", "avocado", "banana", "cheese"]))
        self.assertEqual(ks2, set(["apple", "acacia", "banana", "durian"]))
        
        # Proper key sets
        self.assertEqual(result.keys(), ['a','c','d'])
        self.assertEqual(result.subset_by_key("a"), set(["acacia", "avocado"]))
        self.assertEqual(result.subset_by_key("b"), set())
        self.assertEqual(result.subset_by_key("c"), set(["cheese"]))
        self.assertEqual(result.subset_by_key("d"), set(["durian"]))

        # _update
        copy = ks.copy()
        copy ^= ks2

        # No unintended side-effects
        self.assertEqual(ks2, set(["apple", "acacia", "banana", "durian"]))

        self.assertEqual(result, copy)
        self.assertEqual(sorted(result.keys()), sorted(copy.keys()))
        for key in result.keys():
            self.assertEqual(result.subset_by_key(key), copy.subset_by_key(key))

    # TODO: test __rand__, __ror__, __rxor__, and __rsub__


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(KeyedSetTest),))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
