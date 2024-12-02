##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from itertools import islice
from string import Formatter


def parse_atoms(template):
    """
    Returns the named placeholders from a template string.
    """
    return tuple(nm for _, nm, _, _ in Formatter().parse(template) if nm)


def extract_atoms(value, sep, count):
    """
    Returns the last `count` values from the string `value`.
    """
    return tuple(value.rsplit(sep, count)[1:])


# Adapted from docs.python.org/3.11/library/itertools.html
def batched(iterable, n):
    """
    Batch data into tuples of length `n`.  The last batch may be shorter.

    >>> list(batched('ABCDEFG', 3))
    [('A', 'B', 'C'), ('D', 'E', 'F'), ('G',)]
    """
    if n < 1:
        raise ValueError("n must be greater than zero")
    itr = iter(iterable)
    while True:
        batch = tuple(islice(itr, n))
        if not batch:
            break
        yield batch
    #
    # Note: In Python 3.7+, the above loop would be written as
    #     while (batch := tuple(islice(itr, n))):
    #         yield batch
