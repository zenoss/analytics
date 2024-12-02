##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2011, 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from twisted.internet import defer

from .config import ConfigChecksums

log = logging.getLogger("zen.zensyslog.configloader")


class ConfigLoader(object):
    """Handles retrieving additional dynamic configs for daemon from ZODB"""

    def __init__(self, servicefactory, parsers, processor, rules):
        self._servicefactory = servicefactory
        self._parsers = parsers
        self._processor = processor
        self._rules = rules
        self._checksums = ConfigChecksums()

    @defer.inlineCallbacks
    def task(self):
        """
        Contact zenhub and gather configuration data.
        """
        log.debug("retrieving zensyslog configuration")
        try:
            service = yield self._servicefactory()
            updates = yield service.callRemote("getConfig", self._checksums)
        except Exception:
            log.exception("failed to retrieve syslog configuration")
        else:
            log.debug("zensyslog configuration retrieved")
            self._process_priorty(updates)
            self._process_parsers(updates)
            self._process_use_summary(updates)
            self._process_rules(updates)
            log.debug("applied zensyslog configuration changes")

    def _process_priorty(self, updates):
        if updates.checksums.priority is None:
            return
        state = "updated" if self._checksums.priority else "initial"
        log.info("received %s default event priority", state)
        self._checksums.priority = updates.checksums.priority
        self._processor.priority = updates.priority

    def _process_use_summary(self, updates):
        if updates.checksums.use_summary is None:
            return
        state = "disable" if not updates.use_summary else "enable"
        log.info("%s using syslog event summary as event message ", state)
        self._checksums.use_summary = updates.checksums.use_summary
        self._processor.use_summary = updates.use_summary

    def _process_parsers(self, updates):
        if updates.checksums.parsers is None:
            return
        state = "updated" if self._checksums.parsers else "initial"
        log.info("received %s syslog event parsers", state)
        self._checksums.parsers = updates.checksums.parsers
        self._parsers.update(updates.parsers)

    def _process_rules(self, updates):
        if updates.checksums.rules is None:
            return
        state = "updated" if self._checksums.rules else "initial"
        log.info("received %s event field filter rules", state)
        self._checksums.rules = updates.checksums.rules
        self._rules.update(updates.rules)
