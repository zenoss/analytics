##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import re
import yaml

from Products.ZenHub import XML_RPC_PORT, PB_PORT
from zope.interface import implementer

from .interface import IHubServerConfig

log = logging.getLogger("zen.zenhub.server.config")

_default_spec = "Products.ZenHub.server.executors:WorkerPoolExecutor"


@implementer(IHubServerConfig)
class ModuleObjectConfig(object):
    """API for retrieving server related configuration data."""

    def __init__(self, config):
        self.__config = config

    @property
    def legacy_metric_priority_map(self):
        return self.__config.legacy_metric_priority_map

    @property
    def priorities(self):
        return self.__config.priorities

    @property
    def pools(self):
        return self.__config.pools

    @property
    def executors(self):
        return self.__config.executors

    @property
    def routes(self):
        return self.__config.routes

    @property
    def modeling_pause_timeout(self):
        return self.__config.modeling_pause_timeout

    @property
    def task_max_retries(self):
        return self.__config.task_max_retries

    @property
    def pbport(self):
        return self.__config.pbport

    @property
    def xmlrpcport(self):
        return self.__config.xmlrpcport


_spec_pattern = re.compile(r"^(?:[a-zA-Z]\w*\.)+[a-zA-Z]\w*:[a-zA-Z]\w*$")


def _validate_spec(spec):
    if _spec_pattern.match(spec) is None:
        raise ValueError("Invalid format for 'spec': %s" % (spec,))


_call_pattern = re.compile(
    r"^(?:\*|(?:[a-zA-Z]\w*\.)*[a-zA-Z]\w*):(?:\*|[a-zA-Z]\w*)$",
)


def _validate_call(call):
    if _call_pattern.match(call) is None:
        raise ValueError("Invalid format for 'routes' call: %s" % (call,))


class ServerConfig(object):
    """Load zenhub server configuration from a file."""

    @classmethod
    def from_file(cls, filename):
        try:
            with open(filename, "r") as f:
                config = yaml.load(f, Loader=yaml.SafeLoader)
            return cls(config)
        except Exception as e:
            log.error(
                "Couldn't load zenhub-server.yaml configuration, "
                "using default settings: %s",
                e,
            )
            return cls({})

    def __init__(self, config):
        """Initialize a ZenHubServerConfig instance.
        The config dict is expected to have the following structure:
            <executor-id>: {
                "spec": "<module-path>:<class-name>",
                "worklist": "<worklist-name>"
                "routes": [
                    "<service-name>:<method-name>",
                    ...
                ]
            }
        where <executor-id> are the keys in the config parameter.
        :type config: dict
        """
        routes = {}
        executors = {}
        pools = {}
        for executor, config in config.items():
            spec = config.get("spec", _default_spec)
            _validate_spec(spec)
            executors[executor] = spec
            poolid = config.get("worklist")
            # WorkerPoolExecutor requires a pool, so set if the
            # worklist value is missing.
            if poolid is None and spec.endswith("WorkerPoolExecutor"):
                poolid = executor
            if poolid:
                pools[poolid] = executor
            calls = config.get("routes")
            if calls:
                for call in calls:
                    _validate_call(call)
                    routes[call] = executor
        self.__routes = routes
        self.__executors = executors
        self.__pools = pools

    @property
    def pools(self):
        return self.__pools

    @property
    def executors(self):
        return self.__executors

    @property
    def routes(self):
        return self.__routes


##############################################################################
# NOTE
#
# The main.py module is dependent on the contents this module (config.py).
# Specfically, if the 'executors' dict is changed, then main.py
# must also be updated with a corresponding change.
##############################################################################


# Declares the executors where work can be sent.
# "executor-id" : "module-path:class-name"
executors = {
    "event": "Products.ZenHub.server.executors:SendEventExecutor",
    "adm": _default_spec,
    "default": _default_spec,
}

# Declares which executor a service call is sent to.
routes = {
    "EventService:sendEvent": "event",
    "EventService:sendEvents": "event",
    "*:applyDataMaps": "adm",
    "*:*": "default",
}

# Declares worker pools and maps the pool to an executor.
# "pool-id": "executor-id"
pools = {
    "default": "default",
    "adm": "adm",
}

priorities = {
    # Declares service call priorities.  The order is from highest priority
    # to lowest priority.  Higher priority service calls are executed much
    # more frequently than lower priority service calls.
    "names": (
        "EVENTS",
        "SINGLE_MODELING",
        "OTHER",
        "CONFIG",
        "MODELING",
    ),
    # Associates service calls with priorities.
    # The ("*:*") mapping must be defined.
    "servicecall_map": {
        "EventService:sendEvent": "EVENTS",
        "EventService:sendEvents": "EVENTS",
        "*:singleApplyDataMaps": "SINGLE_MODELING",
        "*:*": "OTHER",
        "*:getDeviceConfigs": "CONFIG",
        "*:getDeviceConfig": "CONFIG",
        "*:applyDataMaps": "MODELING",
    },
    # Identifies the priority associated with modeling.
    # This is used to pause applyDataMaps processing.
    "modeling": "MODELING",
}


legacy_metric_priority_map = {
    "zenhub.eventWorkList": "EVENTS",
    "zenhub.admWorkList": "MODELING",
    "zenhub.otherWorkList": "OTHER",
    "zenhub.singleADMWorkList": "SINGLE_MODELING",
}

# Limit the number of times ZenHub will retry a task before
# returning it as an error.
task_max_retries = 3


class defaults(object):
    """Default values for options."""

    modeling_pause_timeout = 3600
    xmlrpcport = XML_RPC_PORT
    pbport = PB_PORT


# Maximum number of seconds to pause modeling
# during ZenPack install/upgrade/removal
modeling_pause_timeout = defaults.modeling_pause_timeout

# Port to use for XML-based Remote Procedure Calls (RPC)
xmlrpcport = defaults.xmlrpcport

# Port to use for Twisted's pb service
pbport = defaults.pbport
