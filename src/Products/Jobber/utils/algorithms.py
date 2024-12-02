##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function


def partition(source, predicate):
    """Separates the items in the source into one of two lists.

    The first list contains all the items for which the predicate return True
    and the second list contains the items for which the predicate returned
    False.  The relative order of the items is preserved.

    :param source: The source of items for paritioning
    :type source: Iterable[Any]
    :param predicate: A function the selects the list.
    :type predicate: Function[Any] -> Boolean
    :rtype: Tuple[List[Any], List[Any]]
    """
    first, second = [], []
    for item in source:
        (first if predicate(item) else second).append(item)
    return (first, second)
