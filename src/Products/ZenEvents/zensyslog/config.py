##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2011, 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from twisted.spread import pb


class ConfigChecksums(pb.Copyable, pb.RemoteCopy):
    """
    Object for requesting zensyslog config data.

    Each field is a token returned from zenhub.  For the first request,
    the fields should be None.
    """

    __slots__ = ("priority", "parsers", "use_summary", "rules")

    def __init__(
        self, priority=None, parsers=None, use_summary=None, rules=None
    ):
        self.priority = priority
        self.parsers = parsers
        self.use_summary = use_summary
        self.rules = rules

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(
                "{}={}".format(name, getattr(self, name))
                for name in self.__slots__
            ),
        )


pb.setUnjellyableForClass(ConfigChecksums, ConfigChecksums)


class ConfigUpdates(pb.Copyable, pb.RemoteCopy):
    """
    Configuration for zensyslog.
    """

    __slots__ = ("priority", "parsers", "use_summary", "rules", "checksums")

    def __init__(
        self, priority=None, parsers=None, use_summary=None, rules=None
    ):
        self.priority = priority
        self.parsers = parsers
        self.use_summary = use_summary
        self.rules = rules
        self.checksums = ConfigChecksums()


pb.setUnjellyableForClass(ConfigUpdates, ConfigUpdates)
