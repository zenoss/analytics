##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
"""
This module allows the override of arguments to the memcache.Client initializer.

The RelStorage initializer allows specification of a module, which is used to
construct a Client object for the purposes of connection to memcached.  There
is no mechanism for overriding the arguments to the Client initializer.

The solution is to dynamically create a module which wraps the memcache client
module, replacing the Client class with one which binds the initializer arguments.
"""

import memcache
import sys
import types

def createModule(moduleName, **kwargs):
    """
    Create a module wrapping the memcache module.

    Given a module name and a set of keyword arguments, dynamically create a
    module with that name which overrides the memcache module's Client
    initializer arguments with the keyword arguments.
    """
    # Prevent overriding an existing module
    if moduleName in sys.modules:
        raise ValueError("Duplicate module name", moduleName)

    # Create a subclass of memcache.Client which overrides the __init__ function
    def init(self, *_args, **_kwargs):
        _kwargs = dict(kwargs, **_kwargs)
        memcache.Client.__init__(self, *_args, **_kwargs)
    clientClass = type('Client', (memcache.Client,), {'__init__': init})

    # Create a new module containing the new Client class
    module = types.ModuleType(moduleName)
    module.Client = clientClass
    sys.modules[moduleName] = module
