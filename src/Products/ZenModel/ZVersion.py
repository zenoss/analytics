##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os

VERSION = os.environ.get("ZENOSS_VERSION", "DEV")
BUILD_NUMBER = os.environ.get("BUILD_NUMBER", "DEV")
