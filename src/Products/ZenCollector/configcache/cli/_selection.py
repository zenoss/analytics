##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import enum
import six

__all__ = ("get_message", "confirm")


def get_message(action, monitor, service):
    mon_selection = _Selection.select(monitor)
    svc_selection = _Selection.select(service)
    mesg = _messages.get((mon_selection, svc_selection), _default_message)
    return mesg.format(act=action, mon=monitor, svc=service)


def confirm(mesg):
    response = None
    prompt = "{}. Are you sure (y/N)? ".format(mesg)
    while response not in ["y", "n", ""]:
        response = six.moves.input(prompt).lower()
    return response == "y"


class _Selection(enum.Enum):
    All = "All"
    Some = "Some"
    One = "One"

    @classmethod
    def select(cls, arg):
        return cls.All if arg == "*" else cls.Some if "*" in arg else cls.One


def _build_message_lookup():
    AllMon = AllSvc = _Selection.All
    SomeMon = SomeSvc = _Selection.Some
    OneMon = OneSvc = _Selection.One
    return {
        (AllMon, AllSvc): ("{act} all device configurations"),
        (AllMon, SomeSvc): (
            "{act} all device configurations created by all "
            "services matching '{svc}'"
        ),
        (AllMon, OneSvc): (
            "{act} all device configurations created by the '{svc}' service"
        ),
        (SomeMon, AllSvc): (
            "{act} all configurations for devices monitored by all "
            "collectors matching '{mon}'"
        ),
        (SomeMon, SomeSvc): (
            "{act} all configurations device monitored by all "
            "collectors matching '{mon}' and created by all services "
            "matching '{svc}'"
        ),
        (SomeMon, OneSvc): (
            "{act} all configurations created by the '{svc}' "
            "service for devices monitored by all collectors "
            "matching '{mon}'"
        ),
        (OneMon, AllSvc): (
            "{act} all configurations for devices monitored by the "
            "'{mon}' collector"
        ),
        (OneMon, SomeSvc): (
            "{act} all configurations for devices monitored by the "
            "'{mon}' collector and created by all services matching '{svc}'"
        ),
        (OneMon, OneSvc): (
            "{act} all configurations for devices monitored by the "
            "'{mon}' collector and created by the '{svc}' service"
        ),
    }


_messages = _build_message_lookup()
_default_message = "collector '%s'  service '%s'"
