##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component import getUtilitiesFor


def load_utilities(utility_class):
    """
    Loads ZCA utilities of the specified class.

    @param utility_class: The type of utility to load.
    @return: A list of utilities, sorted by their 'weight' attribute.
    """
    utilities = (f for n, f in getUtilitiesFor(utility_class))
    return sorted(utilities, key=lambda f: getattr(f, "weight", 100))
