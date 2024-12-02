##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, 2023 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""SyslogConfig

Provides configuration for syslog message to Zenoss event conversions.
"""

from __future__ import absolute_import, print_function

import logging

from hashlib import md5

from Products.ZenHub.HubService import HubService
from Products.ZenEvents.zensyslog.config import ConfigUpdates

log = logging.getLogger("zen.hub.services.syslogconfig")


class SyslogConfig(HubService):
    def remote_getConfig(self, checksums):
        result = ConfigUpdates()

        priority = self.zem.defaultPriority
        priority_checksum = _checksum(priority)
        if checksums.priority != priority_checksum:
            result.priority = priority
            result.checksums.priority = priority_checksum

        use_summary = self.zem.syslogSummaryToMessage
        use_summary_checksum = _checksum(use_summary)
        if checksums.use_summary != use_summary_checksum:
            result.use_summary = use_summary
            result.checksums.use_summary = use_summary_checksum

        parsers = self.zem.syslogParsers
        parsers_checksum = _checksum(parsers)
        if checksums.parsers != parsers_checksum:
            result.parsers = parsers
            result.checksums.parsers = parsers_checksum

        rules = self.zem.syslogMsgEvtFieldFilterRules
        rules_checksum = _checksum(rules)
        if checksums.rules != rules_checksum:
            result.rules = rules
            result.checksums.rules = rules_checksum

        return result


def _checksum(value):
    return md5(str(value)).hexdigest()  # noqa: S324
