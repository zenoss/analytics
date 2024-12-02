##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import six

from json import (
    loads as json_loads,
    dumps as json_dumps,
    JSONDecoder,
)

from kombu.utils.encoding import bytes_t

__all__ = ("without_unicode",)


def _process_list(seq):
    stack = [seq]
    while stack:
        lst = stack.pop()
        for idx, item in enumerate(lst):
            if isinstance(item, six.text_type):
                lst[idx] = str(item)
            if isinstance(item, list):
                stack.append(item)
    return seq


def _decode_hook(*args, **kw):
    result = {}
    for n, i in enumerate(args):
        for pair in i:
            k, v = pair
            if isinstance(v, six.text_type):
                v = str(v)
            elif isinstance(v, list):
                v = _process_list(v)
            result.update({str(k): v})
    return result


class _WithoutUnicode(JSONDecoder):
    def __init__(self, *args, **kw):
        super(_WithoutUnicode, self).__init__(
            object_pairs_hook=_decode_hook, *args, **kw
        )

    def decode(self, s):
        if isinstance(s, bytes_t):
            s = s.decode("utf-8")
        return super(_WithoutUnicode, self).decode(s)


def _without_unicode_loads(s, **kw):
    return json_loads(s, cls=_WithoutUnicode, **kw)


class without_unicode(object):
    dump = staticmethod(json_dumps)
    load = staticmethod(_without_unicode_loads)
