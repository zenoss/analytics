##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import cPickle
from functools import wraps
from cStringIO import StringIO
from contextlib import closing
import zlib
from twisted.spread.banana import SIZE_LIMIT as TWISTED_SIZE_LIMIT

__all__ = ["Zipper"]


class _PickleZipper(object):

    def __init__(self, chunk_size):
        self.chunk_size = chunk_size

    def dump(self, obj):
        l = []
        compressed = zlib.compress(cPickle.dumps(obj, protocol=cPickle.HIGHEST_PROTOCOL))
        with closing(StringIO(compressed)) as buffer:
            s = buffer.read(self.chunk_size)
            while s:
                l.append(s)
                s = buffer.read(self.chunk_size)
        return l

    def load(self, str_list):
        return cPickle.loads(zlib.decompress(''.join(str_list)))

    def _dump(self, obj):
        return obj

    def _load(self, obj):
        return obj


Zipper = _PickleZipper(TWISTED_SIZE_LIMIT)


def picklezip(f):
    @wraps(f)
    def inner(*args, **kwargs):
        result = f(*args, **kwargs)
        return Zipper.dump(result)
    return inner
