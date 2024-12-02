##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from .deviceconfig import build_device_config
from .oidmap import build_oidmap

__all__ = ("build_device_config", "build_oidmap")
