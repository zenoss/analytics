##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import re

from collections import Mapping

from zope.interface import implementer

from Products.ZenEvents.ZenEventClasses import Error
from Products.ZenHub.interfaces import (
    ICollectorEventTransformer,
    TRANSFORM_CONTINUE,
    TRANSFORM_DROP,
)

log = logging.getLogger("zen.zensyslog.transformer")

_rule_error_event = {
    "device": "127.0.0.1",
    "eventClass": "/App/Zenoss",
    "severity": Error,
    "eventClassKey": "",
    "summary": "Syslog Message Filter processing issue",
    "component": "zensyslog",
}


@implementer(ICollectorEventTransformer)
class SyslogMsgFilter(object):
    """
    Interface used to perform filtering of events at the collector.
    This could be used to drop events, transform event content, etc.

    These transformers are run sequentially before a fingerprint is generated
    for the event, so they can set fields which are used by an
    ICollectorEventFingerprintGenerator.

    The priority of the event transformer (the transformers are executed in
    ascending order using the weight of each filter).
    """

    weight = 1

    def __init__(self, rules, counters):
        self._rules = rules
        self._counters = counters

    def transform(self, event):
        """
        Performs any transforms of the specified event at the collector.

        @param event: The event to transform.
        @type event: dict
        @return: Returns TRANSFORM_CONTINUE if this event should be forwarded
            on to the next transformer in the sequence, TRANSFORM_STOP if no
            further transformers should be performed on this event, and
            TRANSFORM_DROP if the event should be dropped.
        @rtype: int
        """
        relevant_rules = (
            (k, v) for k, v in self._rules.iteritems() if k in event
        )
        for name, matchers in relevant_rules:
            value = event.get(name)
            for idx, matcher in enumerate(matchers):
                matched = matcher.search(value)
                if not matched:
                    continue
                log.debug(
                    "drop syslog message! "
                    "EventFieldName:%r "
                    "EventFieldValue:%r "
                    "FilterRuleNumber:%s "
                    "FilterRuleExpression:%r",
                    name,
                    value,
                    idx,
                    matcher.pattern,
                )
                self._counters["eventFilterDroppedCount"] += 1
                return TRANSFORM_DROP
        else:
            return TRANSFORM_CONTINUE


class FilterRules(Mapping):
    """
    Rules for syslog message filtering.
    """

    def __init__(self, app):
        self._app = app
        self._rules = {}

    def __getitem__(self, key):
        return self._rules[key]

    def __iter__(self):
        return iter(self._rules)

    def __len__(self):
        return len(self._rules)

    def update(self, source):
        rules = {}
        for name, ruledefs in source.iteritems():
            for idx, ruledef in enumerate(ruledefs):
                try:
                    compiledRule = re.compile(ruledef, re.DOTALL)
                except Exception as ex:
                    msg = (
                        "Syslog Message Filter configuration for the "
                        "{!r} event field could not compile rule #{!r}"
                        " with the expression of {!r}. Error {!r}".format(
                            name, idx, ruledef, ex
                        )
                    )
                    log.warn(msg)
                    self._send_error_event(
                        message=msg,
                        eventKey="SyslogMessageFilter.{}.{}".format(name, idx),
                    )
                else:
                    rules.setdefault(name, []).append(compiledRule)
        self._rules = rules

    def _send_error_event(self, **kwargs):
        """
        Build an Event dict from parameters.n
        """
        if kwargs:
            event = _rule_error_event.copy()
            event.update(kwargs)
        else:
            event = _rule_error_event
        self._app.sendEvent(event)
