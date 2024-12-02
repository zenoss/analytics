##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import collections

from itertools import chain, count, cycle

import enum
import six

from zope.component import getUtility

from Products.Zuul.interfaces import IDataRootFactory

from .config import priorities as _priorities
from .utils import UNSPECIFIED as _UNSPECIFIED

__all__ = (
    "ModelingPaused",
    "PrioritySelection",
    "ServiceCallPriority",
    "servicecall_priority_map",
)

_priority_names = _priorities["names"]
_priority_servicecall_map = _priorities["servicecall_map"]


class PrioritySelection(collections.Iterator):
    """Implements an iterator that produces priority values.

    Higher priority values are produced more frequently than lower
    priority values.

    This iterator behaves as if it's iterating over an infinite sequence.

    The optional 'exclude' function can also be used, at run time, control
    which priorities are iterated over.  If an exclude function is provided,
    it returns a sequence of priorities that should be excluded from
    iteration.  This call is made every time the 'available' and 'next'
    methods are invoked.  The exclude function may vary its return value
    over time.  An empty sequence is returned to exclude no priorities.
    """

    def __init__(self, priorities, exclude=None):
        """Initialize a PrioritySelection object.

        :param priorities: The priorities to iterate over.
        :type priorities: Sequence[T]
        :param exclude: Determines which priorities are ignored.
        :type exclude: Callable[[], Sequence[T]]
        """
        self.__exclude = exclude if exclude is not None else lambda: []
        self.__priorities = tuple(priorities)

        # Build a priority selection sequence for all priorities
        self.__selection = _build_weighted_list(self.__priorities)
        # Use a cycle iterator over the priority sequence
        self.__iter = cycle(self.__selection)

    @property
    def priorities(self):
        """Return all the priorities that can be selected.

        :rtype: Tuple[T]
        """
        return self.__priorities

    @property
    def available(self):
        """Return all the currently selectable priorities.

        If PrioritySelection was initialized with an exclude function,
        the priorities returned from this function will not include
        priorities specified by that exclude function.

        :rtype: Tuple[T]
        """
        excluded = self.__exclude()
        return tuple(p for p in self.__priorities if p not in excluded)

    def next(self):  # noqa: A003
        excluded = self.__exclude()
        return next(p for p in self.__iter if p not in excluded)


class ModelingPaused(object):
    """A predicate that reports whether modeling is paused.

    ModelingPaused instances can be used as predicates due to their return
    values having boolean properties.  When modeling is paused, i.e. the
    predicate is true, then

        paused = ModelingPaused(dmd, Priority.MODELING, 60)
        assert bool(paused()) is True
        assert [Priority.MODELING] == paused()

    will run successfully.

    When modeling is paused, applyDataMaps service calls are not run.
    """

    def __init__(self, modeling_priority, modeling_pause_timeout):
        """Initialize a ModelingPaused instance.

        :param modeling_priority: Priority for modeling calls
        :param float modeling_pause_timeout: Duration of modeling pause
        """
        self.__dmd = getUtility(IDataRootFactory)()
        self.__modeling_pause_timeout = modeling_pause_timeout
        self.__priority = getattr(ServiceCallPriority, modeling_priority)

    def __call__(self):
        """Return the modeling priority value when paused.

        Returns an empty list if modeling is not paused.

        :rtype: Union[Sequence[ServiceCallPriority], []]
        """
        if self.__dmd.getPauseADMLife() <= self.__modeling_pause_timeout:
            return [self.__priority]
        return []


def _build_weighted_list(data):
    """Generate and return a weighted sequence based on the given data.

    Given a set of sortable elements, return an immutable sequence that
    reflects each element's sort position by some weight evenly distributed
    throughout the returned sequence.

    >>> data = ['a', 'b', 'c']
    >>> _build_weighted_list(data)
    ('a', 'a', 'b', 'a', 'a', 'b', 'c', 'a', 'a', 'b', 'a')

    The element that sorts to the first position has highest weight, so
    'a' will have the highest weight.  Each subsequence element will have
    less weight.  The element that sorts to the end has the lowest weight.

    The weight algorithm is 2^(len(p) - n) - 1, where len(p) is the number
    of elements and n is the element's position in the sorted sequence.
    """
    # Sort the data
    elements = tuple(sorted(data))

    # Generate a series of weights.  The first element should have the
    # highest weight.
    weights = [(2 ** n) - 1 for n in range(len(elements), 0, -1)]

    # Build a list of element lists where each element list has a length
    # matching their weight. E.g. given elements ('a', 'b') and weights
    # [3, 1], the result is [['a', 'a', 'a'], ['b']].
    weighted_series = (
        [element] * weight for element, weight in zip(elements, weights)
    )

    # Give each series element an index between 0 and 1. E.g. given
    #    [['a', 'a', 'a'],
    #     ['b']]
    # then the 'indexed' sequence would be
    #    [[(0.25, 'a'), (0.5, 'a'), (0.75, 'a')],
    #     [(0.5, 'b')]]
    indexed = (
        zip(
            count(
                start=1.0 / (len(series) + 1),
                step=1.0 / (len(series) + 1),
            ),
            series,
        )
        for series in weighted_series
    )

    # Flatten the indexed series, e.g. converts
    #    [[(0.25, 'a'), (0.5, 'a'), (0.75, 'a')], [(0.5, 'b')]]
    # to
    #    [(0.25, 'a'), (0.5, 'a'), (0.75, 'a'), (0.5, 'b')]
    flattened = chain.from_iterable(indexed)

    # Sort the indexed element values, e.g. converts
    #    [(0.25, 'a'), (0.5, 'a'), (0.75, 'a'), (0.5, 'b')]
    # to
    #    [(0.25, 'a'), (0.5, 'a'), (0.5, 'b'), (0.75, 'a')]
    sorted_by_index = sorted(flattened)

    # Return the indexed sorted elements minus the index values,
    # e.g. converts
    #    [(0.25, 'a'), (0.5, 'a'), (0.5, 'b'), (0.75, 'a')]
    # to
    #    ('a', 'a', 'b', 'a')
    # and returns it as a tuple.
    return tuple(v for _, v in sorted_by_index)


class IntEnumFactory(object):
    """Builds an IntEnum class.

    For example:

        priorities = ("high", "middle", "low")
        SimplePriority = IntEnumFactory.build("SimplePriority", priorities)

    creates a SimplePriority class defined as if it had been written like:

        class SimplePriority(enum.IntEnum):
            HIGH = 1
            MIDDLE = 2
            LOW = 3

    Note that IntEnum based enumerations are convertable to int values which
    can be sorted.
    """

    @staticmethod
    def build(name, values):
        return enum.IntEnum(
            name,
            " ".join(value.upper() for value in values),
            module=__name__,  # necessary to support pickling
        )


# A priority class defined by the priorities defined in the config module.
ServiceCallPriority = IntEnumFactory.build(
    "ServiceCallPriority", _priority_names
)


class ServiceCallPriorityMap(collections.Mapping):
    """Maps service calls to a priority value."""

    def __init__(self, mapping, prioritycls):
        """Initialize a ServiceCallPriorityMap instance.

        Note that a mapping must contain a key value of "*:*" to
        define a default priority.  If "*:*" is not specified, a ValueError
        exception is raised.

        :param mapping: Maps service calls to priority name
        :type mapping: Mapping[str, str]
        :param prioritycls: Enumeration of priorities
        :type prioritycls: IntEnum
        """
        services = set()
        methods = set()
        priorityMap = {}

        for descriptor, priorityName in mapping.items():
            serviceName, methodName = descriptor.split(":")
            services.add(serviceName)
            methods.add(methodName)
            priority = getattr(prioritycls, priorityName)
            priorityMap[descriptor] = priority

        if "*:*" not in priorityMap:
            raise ValueError("Missing required '*:*' priority mapping")

        self.__services = services
        self.__methods = methods
        self.__map = priorityMap

    def get(self, key, default=_UNSPECIFIED):
        """Return the priority value mapped by key.

        If no specific mapping exists for key and 'default' is unspecified,
        then the default mapping (i.e. key is ('*', '*')) is returned.
        If 'default' is specified, that value is returned when no
        specific mapping exists for the given key.

        :param key: (service-name, method-name)
        :type key: Sequence[str, str]
        :rtype: int
        """
        key = self.__makekey(key)
        if key == "*:*" and default is not _UNSPECIFIED:
            return default
        return self.__map[key]

    def __getitem__(self, key):
        """Return the priority value mapped by key.

        If no specific mapping exists for key, the default mapping (i.e.
        key is ('*', '*')) is returned.

        :param key: (service-name, method-name)
        :type key: Sequence[str, str]
        :rtype: int
        """
        key = self.__makekey(key)
        return self.__map[key]

    def __iter__(self):
        return iter(self.__map)

    def __len__(self):
        return len(self.__map)

    def __makekey(self, key):
        if isinstance(key, six.string_types):
            key = str(key).split(":")
        service, method = key
        if service not in self.__services:
            service = "*"
        if method not in self.__methods:
            method = "*"
        key = "{}:{}".format(service, method)
        if key in self.__map:
            return key
        key = "{}:*".format(service)
        if key in self.__map:
            return key
        key = "*:{}".format(method)
        if key in self.__map:
            return key
        return "*:*"


# Global map of service calls to priority, as defined in the config module.
servicecall_priority_map = ServiceCallPriorityMap(
    _priority_servicecall_map, ServiceCallPriority
)
