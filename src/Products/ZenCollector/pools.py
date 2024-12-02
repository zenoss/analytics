##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""pool

Pool resources and provide an infrastructure for interacting with them.

"""


class ResourcePool(object):
    """
    Container object for allocating shared resources.
    """

    def __init__(self, name):
        self.name = name
        self.minCount = None
        self.maxCount = None
        self._resources = {}


# Manage all pools
globalAllocater = {}


def getResourcePool(name, factory=ResourcePool):
    return getPool(name, factory)


def getPool(name, factory=None):
    """
    Return the named pool.
    If the factory is None, a simple dictionary is created and returned.

    @parameter name: name of the pool
    @type name: string
    @parameter factory: class to use to construct the resource pool or None
    @type factory: class that takes only one argument as a constructor
        (the name)
    """
    if name not in globalAllocater:
        if factory is None:
            globalAllocater[name] = {}
        else:
            globalAllocater[name] = factory(name)
    return globalAllocater[name]
