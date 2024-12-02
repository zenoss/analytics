##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import os

from Products.ZenUtils.GlobalConfig import globalConfToDict

from .data import (
    Host,
    HostFactory,
    ServiceDefinition,
    ServiceDefinitionFactory,
    ServiceInstance,
    ServiceInstanceFactory,
    ServiceJsonDecoder,
    ServiceJsonEncoder,
)
from .client import ControlPlaneClient, ControlCenterError
from .environment import configuration
from .servicetree import ServiceTree


def getConnectionSettings(options=None):
    if options is None:
        o = globalConfToDict()
    else:
        o = options
    settings = {
        "user": o.get("controlplane-user", "zenoss"),
        "password": o.get("controlplane-password", "zenoss"),
    }
    # allow these to be set from the global.conf for development but
    # give preference to the environment variables
    settings["user"] = os.environ.get(
        "CONTROLPLANE_SYSTEM_USER", settings["user"]
    )
    settings["password"] = os.environ.get(
        "CONTROLPLANE_SYSTEM_PASSWORD", settings["password"]
    )
    return settings


__all__ = (
    "ControlCenterError",
    "ControlPlaneClient",
    "Host",
    "HostFactory",
    "ServiceDefinition",
    "ServiceDefinitionFactory",
    "ServiceInstance",
    "ServiceInstanceFactory",
    "ServiceJsonDecoder",
    "ServiceJsonEncoder",
    "ServiceTree",
    "configuration",
)
