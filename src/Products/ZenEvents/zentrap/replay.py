##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import collections
import cPickle
import glob
import logging

from optparse import OptionValueError

log = logging.getLogger("zen.zentrap.replay")


class PacketReplay(collections.Iterable):
    """
    Returns an iterator that produces previously capture packets.

    The client code can 'replay' these packets in the same order that they
    were captured.
    """

    @staticmethod
    def add_options(parser):
        parser.add_option(
            "--replayFilePrefix",
            dest="replayFilePrefix",
            action="callback",
            callback=_validate_replayfileprefix,
            nargs=1,
            type="str",
            default=[],
            help="Filename prefix containing captured packet data. "
            "Can specify more than once.",
        )

    @classmethod
    def from_options(cls, options):
        """
        Returns a PacketReplay object if the `replayFilePrefix` attribute
        of the `options` parameter is not empty.
        """
        if options.replayFilePrefix:
            return cls(options.replayFilePrefix)

    def __init__(self, fileprefixes):
        self._fileprefixes = fileprefixes

    @property
    def prefixes(self):
        return self._fileprefixes

    @property
    def filenames(self):
        return self._filenames()

    def __iter__(self):
        """
        Replay all captured packets using the files specified in
        the --replayFilePrefix option and then exit.
        """
        return self._packet_generator()

    def _packet_generator(self):
        # Note what you are about to see below is a direct result of optparse
        for name in self._filenames():
            log.debug("loading packet data from '%s'", name)

            try:
                with open(name, "rb") as fp:
                    packet = cPickle.load(fp)
            except (IOError, EOFError):
                log.exception("failed to load packet data from %s", name)
                continue

            yield packet

    def _filenames(self):
        return sorted(
            name
            for prefix in self._fileprefix
            for name in glob.glob(prefix + "*")
        )


def _validate_replayfileprefix(option, optstr, value, parser):
    if getattr(parser.values, "captureFilePrefix", None):
        raise OptionValueError(
            "can't use --replayFilePrefix with --captureFilePrefix"
        )
    prefixes = getattr(parser.values, option.dest)
    prefixes.append(value)
