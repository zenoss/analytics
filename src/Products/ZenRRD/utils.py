##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

"""utils

RRD utility functions
"""

import math
import time

from Acquisition import aq_chain

from .Exceptions import RRDObjectNotFound, TooManyArgs


def loadargs(obj, args):
    """
    Load data into a RRD Object

    @param obj: RRD object
    @type obj: RRD object
    @param args: arguments
    @type args: list of strings
    """
    import string

    arglen = len(args)
    if arglen > len(obj._properties):
        raise TooManyArgs("Too many args")
    i = 0
    for arg in args:
        if i > arglen:
            break
        arg = arg.strip()
        att = obj._properties[i]["id"]
        try:
            if arg != "":
                if obj._properties[i]["type"] == "lines":
                    value = map(string.strip, arg.split(","))
                    att = "_" + att
                elif obj._properties[i]["type"] == "int":
                    value = int(arg)
                elif obj._properties[i]["type"] == "long":
                    value = long(arg)
                elif obj._properties[i]["type"] == "float":
                    value = float(arg)
                elif obj._properties[i]["type"] == "boolean":
                    value = eval(arg)
                else:
                    value = arg
                if value is not None:
                    setattr(obj, att, value)
        except Exception:
            print("att = %s value = %s" % (att, arg))
            raise
        i += 1


def prefixid(idprefix, id):
    """
    See if prefix needs to be added to id

    @param idprefix: prefix
    @type idprefix: string
    @param id: identifier
    @type id: string
    @return: add the prefix with a '-' in between
    @rtype: string
    """
    if id.find(idprefix) != 0:
        id = idprefix + "-" + id
    return id


def rootid(idprefix, id):
    """
    See if prefix needs to be removed from id

    @param idprefix: prefix
    @type idprefix: string
    @param id: identifier
    @type id: string
    @return: remove the prefix with a '-' in between or return None
    @rtype: string or None
    """
    if idprefix[-1] != "-":
        idprefix += "-"
    if id.find(idprefix) == 0:
        return id[len(idprefix) :]


def walkupconfig(context, name):
    """
    Given a Zope context, try to find the rrdconfig object
    for the name.
    Raises RRDObjectNotFound if not found.

    @param context: Zope context
    @type context: Zope context object
    @param name: RRDView name
    @type name: string
    @return: rrdconfig object or None
    @rtype: rrdconfig object
    """
    if not name:
        return
    while 1:
        if hasattr(context, "rrdconfig") and hasattr(context.rrdconfig, name):
            return getattr(context.rrdconfig, name)
        context = context.aq_parent
        if context.id == "dmd":
            raise RRDObjectNotFound(
                "Object %s not found in context %s"
                % (name, context.getPrimaryUrlPath())
            )


def templateNames(context):
    """
    Return template names in the given context

    @param context: Zope context
    @type context: Zope context object
    @return: names of the templates
    @rtype: set of strings
    """
    names = set()
    for obj in aq_chain(context):
        rrdconfig = getattr(obj, "rrdconfig", None)
        if rrdconfig:
            names = names.union(rrdconfig.objectIds(spec="RRDTargetType"))
    return names


def getRRDView(context, name):
    """
    Lookup an RRDView based on its name

    @param context: Zope context
    @type context: Zope context object
    @param name: RRDView name
    @type name: string
    @return: rrdconfig object or None
    @rtype: rrdconfig object
    """
    return walkupconfig(context, "RRDView-" + name)


def getRRDTargetType(context, name):
    """
    Lookup an rrdtargettype based on its name

    @param context: Zope context
    @type context: Zope context object
    @param name: RRDView name
    @type name: string
    @return: rrdconfig object or None
    @rtype: rrdconfig object
    """
    return walkupconfig(context, "RRDTargetType-" + name)


def getRRDDataSource(context, name):
    """
    Lookup an rrddatasource based on its name

    @param context: Zope context
    @type context: Zope context object
    @param name: RRDView name
    @type name: string
    @return: rrdconfig object or None
    @rtype: rrdconfig object
    """
    return walkupconfig(context, "RRDDataSource-" + name)


class rpnStack(object):

    NAN = 1e5000 - 1e5000
    INF = 1e5000

    def __init__(self, value):
        self.stack = [float(value)]

    def sanitizePop(self):
        x = self.stack.pop()
        return 0 if x != x else x

    def process(self, count, proc):
        args = []
        stack = self.stack
        for i in range(count):
            args.append(stack.pop())
        stack.append(proc(*args))

    # Note:  0 does not pollute.  Sorry.
    def polluteProcess(self, count, condition, proc):
        stack = self.stack
        args = []
        polluted = False
        for i in range(count):
            x = stack.pop()
            if condition(x):
                polluted = x
            args.append(x)
        args.insert(0, polluted)
        stack.append(proc(*args))

    def dynamicProcess(self, proc):
        count = int(self.stack.pop())
        args = self.stack[-count:]
        self.stack = self.stack[0:-count]
        self.stack.extend(proc(args))

    def isSpecial(self, x):
        return math.isinf(x) or x != x

    def lt(self):
        self.polluteProcess(
            2,
            self.isSpecial,
            lambda p, y, x: 1.0 if not (p) and x < y else 0.0,
        )

    def le(self):
        self.polluteProcess(
            2,
            self.isSpecial,
            lambda p, y, x: 1.0 if not (p) and x <= y else 0.0,
        )

    def gt(self):
        self.polluteProcess(
            2,
            self.isSpecial,
            lambda p, y, x: 1.0 if not (p) and x > y else 0.0,
        )

    def ge(self):
        self.polluteProcess(
            2,
            self.isSpecial,
            lambda p, y, x: 1.0 if not (p) and x >= y else 0.0,
        )

    def eq(self):
        self.polluteProcess(
            2,
            self.isSpecial,
            lambda p, y, x: 1.0 if not (p) and x == y else 0.0,
        )

    def ne(self):
        self.polluteProcess(
            2,
            self.isSpecial,
            lambda p, y, x: 1.0 if not (p) and x != y else 0.0,
        )

    def un(self):
        self.process(1, lambda x: 1.0 if x != x else 0.0)

    def isInf(self):
        self.process(1, lambda x: 1.0 if math.isinf(x) else 0.0)

    def if_(self):
        self.process(3, lambda y, x, c: x if c != 0.0 else y)

    def min_(self):
        self.polluteProcess(
            2, lambda x: x != x, lambda p, y, x: p if p else min(x, y)
        )

    def max_(self):
        self.polluteProcess(
            2, lambda x: x != x, lambda p, y, x: p if p else max(x, y)
        )

    def limit(self):
        self.polluteProcess(
            3,
            self.isSpecial,
            lambda p, y, x, v: v
            if not (p) and (x <= v and v <= y or x >= v and v >= y)
            else self.NAN,
        )

    def mul(self):
        self.process(2, lambda y, x: x * y)

    def div(self):
        self.process(2, lambda y, x: self.NAN if y == 0 else x / y)

    def add(self):
        self.process(2, lambda y, x: x + y)

    def sub(self):
        self.process(2, lambda y, x: x - y)

    def mod(self):
        self.process(2, lambda y, x: self.NAN if y == 0 else math.fmod(x, y))

    def addNaN(self):
        x = self.sanitizePop()
        y = self.sanitizePop()
        self.stack.append(x + y)

    def sin(self):
        self.process(1, lambda x: math.sin(x))

    def cos(self):
        self.process(1, lambda x: math.cos(x))

    def log(self):
        self.process(1, lambda x: math.log(x))

    def exp(self):
        self.process(1, lambda x: math.exp(x))

    def sqrt(self):
        self.process(1, lambda x: math.sqrt(x))

    def atan(self):
        self.process(1, lambda x: math.atan(x))

    def atan2(self):
        self.process(2, lambda y, x: math.atan2(x, y))

    def floor(self):
        self.process(1, lambda x: math.floor(x))

    def ceil(self):
        self.process(1, lambda x: math.ceil(x))

    def deg2rad(self):
        self.process(1, lambda x: math.radians(x))

    def rad2deg(self):
        self.process(1, lambda x: math.degrees(x))

    def abs(self):
        self.process(1, lambda x: abs(x))

    def sort(self):
        # uses None returned by sort to do in-place sort
        self.dynamicProcess(lambda a: a.sort() or a)

    def rev(self):
        # uses None returned by reverse to do in-place reverse
        self.dynamicProcess(lambda a: a.reverse() or a)

    def avg(self):
        def average(a):
            total = count = 0
            for x in a:
                if not (math.isnan(x)):
                    count += 1
                    total += x
            return [total / count] if count > 0 else [self.NAN]

        self.dynamicProcess(average)

    def unkn(self):
        self.stack.append(self.NAN)

    def inf(self):
        self.stack.append(self.INF)

    def neginf(self):
        self.stack.append(-self.INF)

    def time_(self):
        self.stack.append(time.time())

    def dup(self):
        stack = self.stack
        stack.append(stack[-1])

    def pop(self):
        self.stack.pop()

    def exc(self):
        stack = self.stack
        stack[-1], stack[-2] = stack[-2], stack[-1]

    opcodes = {
        "LT": lt,
        "LE": le,
        "GT": gt,
        "GE": ge,
        "EQ": eq,
        "NE": ne,
        "UN": un,
        "ISINF": isInf,
        "IF": if_,
        "MIN": min_,
        "MAX": max_,
        "LIMIT": limit,
        "+": add,
        "-": sub,
        "*": mul,
        "/": div,
        "%": mod,
        "ADDNAN": addNaN,
        "SIN": sin,
        "COS": cos,
        "LOG": log,
        "EXP": exp,
        "SQRT": sqrt,
        "ATAN": atan,
        "ATAN2": atan2,
        "FLOOR": floor,
        "CEIL": ceil,
        "DEG2RAD": deg2rad,
        "RAD2DEG": rad2deg,
        "ABS": abs,
        "SORT": sort,
        "REV": rev,
        "AVG": avg,
        "UNKN": unkn,
        "INF": inf,
        "NEGINF": neginf,
        "TIME": time_,
        "DUP": dup,
        "POP": pop,
        "EXC": exc,
    }

    def step(self, op):
        if op in self.opcodes:
            self.opcodes[op](self)
        else:
            self.stack.append(float(op))

    def result(self):
        return self.stack.pop()


# This is ONLY for the doctests of rpneval.  If you need to do serious floating
# point nearness checking, consult someone who knows IEEE-754 in detail.  This
# one blows up, sometimes subtlely.
def close(x, y):
    return (abs(x - y) / y) < 1e-15


def rpneval(value, rpn):
    """
    Simulate RPN evaluation as per
    http://oss.oetiker.ch/rrdtool/doc/rrdgraph_rpn.en.html
    Note:  because we only have one value, we won't support the entire API.
    >>> rpneval(2, '2,*')
    4.0
    >>> rpneval(7, '2,3,*,*')
    42.0
    >>> close(rpneval(19, '9,5,/,*,32,+'), 66.2)
    True
    >>> rpneval(1, '*')
    -1.0
    >>> rpneval(2, '-8,-')
    10.0
    >>> rpneval(3, '2,%')
    1.0
    >>> rpneval(1e5000 - 1e5000, 'UN')
    1.0
    >>> rpneval(70, '71,LT')
    1.0
    >>> rpneval(69, '69,LT')
    0.0
    >>> rpneval(68, 'inf,LT')
    0.0
    >>> rpneval(67, '67,LE')
    1.0
    >>> rpneval(66, '0,LE')
    0.0
    >>> rpneval(65, 'inf,LE')
    0.0
    >>> rpneval(64, '60,GT')
    1.0
    >>> rpneval(63, '63,GT')
    0.0
    >>> rpneval(63, 'neginf,GT')
    0.0
    >>> rpneval(61, '100,GE')
    0.0
    >>> rpneval(60, '60,GE')
    1.0
    >>> rpneval(59, 'neginf,GE')
    0.0
    >>> rpneval(58, '137,EQ')
    0.0
    >>> rpneval(57, '57,EQ')
    1.0
    >>> rpneval(56, 'inf,EQ')
    0.0
    >>> rpneval(55, '55,NE')
    0.0
    >>> rpneval(-1e5000, 'neginf,EQ')
    0.0
    >>> rpneval(1e5000 - 1e5000, 'unkn,EQ')
    0.0
    >>> rpneval(1e5000 - 1e5000, 'unkn,NE')
    0.0
    >>> rpneval(1e5000, 'inf,NE')
    0.0
    >>> rpneval(51, '51,NE')
    0.0
    >>> rpneval(50, ' 42    ,      NE ')
    1.0
    >>> rpneval(49, 'UN')
    0.0
    >>> rpneval(-1e5000, 'isINF')
    1.0
    >>> rpneval(1e5000, 'IsInF')
    1.0
    >>> rpneval(46, 'ISINF')
    0.0
    >>> rpneval(0, '1,2,if')
    2.0
    >>> rpneval(44, '1,2,if')
    1.0
    >>> rpneval(1e5000, '1,2,IF')
    1.0
    >>> rpneval(1e5000 - 1e5000, '1,2,iF')
    1.0
    >>> rpneval(41, '5,min')
    5.0
    >>> rpneval(40, 'neginf,min') == -1e5000
    True
    >>> rpneval(39, 'unkn,min')
    nan
    >>> rpneval(38, 'neginf,max')
    38.0
    >>> rpneval(37, 'inf,max') == 1e5000
    True
    >>> math.isnan(rpneval(36, 'unkn,max'))
    True
    >>> math.isnan(rpneval(35, '30,neginf,limit'))
    True
    >>> math.isnan(rpneval(34, '30,30.5,limit'))
    True
    >>> rpneval(33, '30,35,limit')
    33.0
    >>> rpneval(32, '464,+')
    496.0
    >>> rpneval(31, '5,-')
    26.0
    >>> rpneval(37, '18,*')
    666.0
    >>> close(rpneval(29, '5,/'), 5.8)
    True
    >>> math.isnan(rpneval(28, '0,/'))
    True
    >>> rpneval(27, '11,%')
    5.0
    >>> math.isnan(rpneval(26, '0,%'))
    True
    >>> rpneval(25, '0,0,/,addnan')
    25.0
    >>> close(rpneval(math.pi / 6, 'sin'), 0.5)
    True
    >>> close(rpneval(math.pi / 3, 'cos'), 0.5)
    True
    >>> rpneval(math.e, 'log') == 1
    True
    >>> rpneval(1, 'exp') == math.e
    True
    >>> rpneval(1.44, 'sqrt')
    1.2
    >>> rpneval(1, 'atan') == math.pi / 4
    True
    >>> rpneval(1, '0,atan2') == math.pi / 2
    True
    >>> rpneval(17.9, 'floor')
    17.0
    >>> rpneval(16.3, 'ceil')
    17.0
    >>> rpneval(15, 'deg2rad') == 15 * math.pi / 180
    True
    >>> rpneval(14, 'rad2deg') == 14 * 180 / math.pi
    True
    >>> rpneval(-13,'abs')
    13.0
    >>> rpneval(12, '5,7,3,sort,-,-')
    10.0
    >>> rpneval(11, '3,4,3,rev,-,+')
    -4.0
    >>> rpneval(10, '5,4,2,4,avg')
    5.25
    >>> rpneval(9, 'unkn')
    nan
    >>> rpneval(8, 'inf')
    inf
    >>> rpneval(7, 'neginf')
    -inf
    >>> rpneval(6, 'time') != 6
    True
    >>> rpneval(5, 'dup,-')
    0.0
    >>> rpneval(2, 'pop')
    -1.0
    >>> rpneval(4, '5,exc,-')
    1.0
    >>> rpneval(None, '2,*')
    None
    """
    if not all([value, rpn]):
        return value
    rpnOps = [op.strip().upper() for op in rpn.split(",")]
    stack = rpnStack(value)
    try:
        for op in rpnOps:
            stack.step(op)
        return stack.result()
    except IndexError:
        return -1.0
