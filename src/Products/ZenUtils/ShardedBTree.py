##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from BTrees.OOBTree import OOBTree
from OFS.SimpleItem import SimpleItem
from itertools import chain
from zlib import adler32

import logging
log = logging.getLogger('zen.ShardedBTree')

DEFAULT_N_SHARDS = 127


def default_hash_func(data):
    """
    adler32 chosen as hashing mechanism since we dont need a cryptographic hashing
    crc32 and murmur speeds are similar to adler32
    """
    # In python < 3.0 adler32 returns a signed value
    return adler32(data) & 0xffffffff


class ShardedBTree(SimpleItem):
    """
    Sharded BTree to reduce the number of ConflictErrors
    """
    def __init__(self, n_shards=DEFAULT_N_SHARDS, hash_func=default_hash_func):
        """ """
        super(ShardedBTree, self).__init__()
        self.n_shards = n_shards
        self.hash_func = hash_func
        self.shards = self._build_shards(self.n_shards)

    def _build_shards(self, n_shards):
        shards = list()
        for _ in xrange(n_shards):
            shards.append(OOBTree())
        return shards

    def resize(self, new_n_shards):
        if new_n_shards != self.n_shards:
            new_shards = self._build_shards(new_n_shards)
            for k, v in self.iteritems():
                shard_id = self.hash_func(k) % new_n_shards
                new_shards[shard_id][k] = v
            self.n_shards = new_n_shards
            self.shards = new_shards

    def _get_shard_id(self, key):
        s_id = -1
        if key:
            try:
                s_id = self.hash_func(key) % self.n_shards
            except Exception:
                log.warn("Could not hash key: %s", key)
        return s_id

    def _get_shard(self, key):
        shard = None
        shard_id = self._get_shard_id(key)
        if shard_id >= 0:
            shard = self.shards[shard_id]
        return shard

    def __setitem__(self, key, item):
        shard = self._get_shard(key)
        if shard is not None:
            shard[key] = item

    def __getitem__(self, key):
        shard = self._get_shard(key)
        if shard is not None:
            return shard[key]

    def __len__(self):
        total = 0
        for shard in self.shards:
            total += len(shard)
        return total

    def __delitem__(self, key):
        shard = self._get_shard(key)
        if shard is not None:
            del shard[key]

    def __contains__(self, key):
        return self.has_key(key)

    def __iter__(self):
        return self.iterkeys()

    def get(self, key, default=None):
        shard = self._get_shard(key)
        if shard is not None:
            return shard.get(key, default)
        return default

    def clear(self):
        for shard in self.shards:
            shard.clear()

    def has_key(self, key):
        shard = self._get_shard(key)
        if shard is None:
            return False
        return shard.has_key(key) > 0

    def keys(self):
        all_keys = []
        for shard in self.shards:
            all_keys.extend(shard.keys())
        return all_keys

    def values(self):
        all_values = []
        for shard in self.shards:
            all_values.extend(shard.values())
        return all_values

    def items(self):
        all_items = []
        for shard in self.shards:
            all_items.extend(shard.items())
        return all_items
        
    def iterkeys(self):
        return chain.from_iterable(shard.iterkeys() for shard in self.shards)

    def itervalues(self):
        return chain.from_iterable(shard.itervalues() for shard in self.shards)
        
    def iteritems(self):
        return chain.from_iterable(shard.iteritems() for shard in self.shards)

    def update(self, thing):
        if not hasattr(thing, "iteritems"):
            raise TypeError("Can't create ShardedBTree from {}".format(thing.__class__))
        for k, v in thing.iteritems():
            self[k] = v

    def stats(self):
        stats = {}
        lengths = []
        for shard in self.shards:
            lengths.append(len(shard))
        values = self.values()
        stats["number of shards"] = self.n_shards
        stats["number of keys"] = len(self)
        stats["Min keys per shard"] = min(lengths)
        stats["Max keys per shard"] = max(lengths)
        stats["Avg keys per shard"] = float(sum(lengths)) / float(self.n_shards)
        return stats
