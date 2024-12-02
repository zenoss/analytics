##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

EMPTY_FROZEN_SET = frozenset()

class KeyedSet(set):
    """
    Works like a regular set, but also maintains an index of the member elements
    based on their "keys". The method for determining each item's key must be
    provided when the KeyedSet is created. This allows some extra functionality
    based on the keys.

    Note: Not thread-safe.

    Example:
    >>> def first_element(item): item[0]
    >>> ks = KeyedSet(first_element, [(1,1),(1,2),(1,3),(2,2),(3,4)])
    >>> ks.subset_by_key(1)
    frozenset([(1,1),(1,2),(1,3)])
    >>> ks.pop_by_key(1)
    (1,1)
    >>> ks
    KeyedSet([(1,2),(1,3),(2,2),(3,4)])
    >>> ks.discard_by_key(1)
    frozenset([(1,2),(1,3)])
    >>> ks
    KeyedSet([(2,2),(3,4)])
    >>> ks.subset_by_key(1)
    >>> frozenset([])
    """


    def __init__(self, key_reader, *args, **kwargs):
        super(KeyedSet, self).__init__(*args, **kwargs)
        self._key_reader = key_reader
        self._keyed = {}
        for item in self: self._index(item)

    def keys(self):
        return self._keyed.keys()

    def iterkeys(self):
        return self._keyed.iterkeys()

    def has_key(self, key):
        return key in self._keyed
        
    def subset_by_key(self, key):
        key_set = self._keyed.get(key, False)
        if key_set:
            return frozenset(key_set)
        else:
            return EMPTY_FROZEN_SET

    def pop_by_key(self, key):
        key_set = self._keyed.get(key, False)
        if key_set:
            item = key_set.pop()
            if not key_set:
                del self._keyed[key]
            super(KeyedSet, self).remove(item)
            return item
        else:
            return set().pop()

    def discard_by_key(self, key):
        key_set = self._keyed.get(key, False)
        if key_set:
            del self._keyed[key]
            discard = super(KeyedSet, self).discard
            for item in key_set:
                discard(item)
            return frozenset(key_set)
        else:
            return EMPTY_FROZEN_SET

    def _index(self, item):
        key = self._key_reader(item)
        if key not in self._keyed:
            self._keyed[key] = set()
        self._keyed[key].add(item)

    def _unindex(self, item):
        key = self._key_reader(item)
        key_set = self._keyed.get(key, False)
        if key_set and item in key_set:
            key_set.remove(item)
            if not key_set:
                del self._keyed[key]

    def add(self, item):
        self._index(item)
        return super(KeyedSet, self).add(item)

    def remove(self, item):
        self._unindex(item)
        return super(KeyedSet, self).remove(item)

    def discard(self, item):
        self._unindex(item)
        return super(KeyedSet, self).discard(item)

    def pop(self):
        item = super(KeyedSet, self).pop()
        self._unindex(item)
        return item

    def clear(self):
        self._keyed.clear()
        return super(KeyedSet, self).clear()

    def copy(self):
        result = super(KeyedSet, self).copy()
        result._key_reader = self._key_reader
        result._keyed = {}
        for key, key_set in self._keyed.iteritems():
          result._keyed[key] = key_set.copy()
        return result

    def __iand__(self, other):
        if len(self) == 0: return self
        other = set(other)
        removed = [item for item in self if item not in other]
        for item in removed:
            self.remove(item)
        return self

    def __ior__(self, other):
        added = [item for item in other if item not in self]
        for item in added:
            self.add(item)
        return self

    def __isub__(self, other):
        for item in other:
            if len(self) == 0: break
            if item in self:
                self.remove(item)
        return self

    def __ixor__(self, other):
        other = set(other)
        removed = [item for item in self if item in other]
        added = [item for item in other if item not in self]
        for item in removed:
            self.remove(item)
        for item in added:
            self.add(item)
        return self

    def __and__(self, other):
        result = self.copy()
        result.__iand__(other)
        return result

    def __or__(self, other):
        result = self.copy()
        result.__ior__(other)
        return result

    def __sub__(self, other):
        result = self.copy()
        result.__isub__(other)
        return result

    def __xor__(self, other):
        result = self.copy()
        result.__ixor__(other)
        return result

    __rand__ = __and__
    __ror__  = __or__
    __rxor__ = __xor__

    def __rsub__(self, other):
        return KeyedSet(self._key_reader, other).__sub__(self)

    def difference(self, *others):
        result = self.copy()
        for other in others:
            result.__isub__(other)
        return result

    def difference_update(self, *others):
        for other in others:
            self.__isub__(other)

    def intersection(self, *others):
        result = self.copy()
        for other in others:
            result.__iand__(other)
        return result

    def intersection_update(self, *others):
        for other in others:
            self.__iand__(other)

    symmetric_difference = __xor__

    def symmetric_difference_update(self, other):
        self.__ixor__(other)

    def union(self, *others):
        result = self.copy()
        for other in others:
            result.__ior__(other)
        return result

    def update(self, *others):
        for other in others:
            self.__ior__(other)
