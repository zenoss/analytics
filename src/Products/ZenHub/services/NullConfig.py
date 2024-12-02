##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""NullConfig

Provides a blank configuration to send no proxies to the remote
collector.
"""

from Products.ZenCollector.services.config import NullConfigService


class NullConfig(NullConfigService):
    pass
