##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from collections import defaultdict

import zope.interface

from Products.ZenUtils.Utils import convToUnits

UNAVAILABLE = "N/A"


def percent(partial, total):
    if partial is None or total is None:
        return None
    if not total:
        return None
    return partial * 100 / total


def percentString(n, decimals=0):
    if n is None:
        return UNAVAILABLE
    return "%*.*f" % (2, decimals, n)


class Record(object):
    zope.interface.implements(zope.interface.Interface)
    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, **kw):
        self.values = kw.copy()

    def __str__(self):
        return str(self.values)

    def __repr__(self):
        return repr(self.values)

    def __getitem__(self, name):
        return self.values[name]

    def __getattr__(self, name):
        return self.values.get(name)

    def percent(self, partial, total):
        return percent(partial, total)

    def percentString(self, n, decimals=0):
        return percentString(n, decimals)

    def humanBytes(self, value, scale=1, unitstr="B"):
        if value is None:
            return UNAVAILABLE
        return convToUnits(value * scale, unitstr=unitstr)

    def humanBits(self, value, scale=1, unitstr="b"):
        if value is None:
            return UNAVAILABLE
        return convToUnits(value * scale, 1000, unitstr=unitstr)

    def fmt(self, fmt, value):
        if value is None:
            return UNAVAILABLE
        return fmt % value


def nested_defaultdict(n, typ):
    """create a nested defaultdict n-levels deep, with type typ leaf values"""
    fact = typ
    i = 1
    while i < n:
        fact = lambda f=fact: defaultdict(f)  # noqa E371
        i += 1
    return defaultdict(fact)
