##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from pprint import pformat

log = logging.getLogger("zen.ZenRRD.CommandParser")


class ParsedResults(object):
    def __init__(self):
        self.events = []  # list of event dictionaries
        self.values = []  # list of (DataPointConfig, value)

    def __repr__(self):
        args = (pformat(self.events), pformat(self.values))
        return "ParsedResults\n  events: %s\n  values: %s}" % args


class CommandParser(object):
    def dataForParser(self, context, datapoint):
        return {}

    def preprocessResults(self, cmd, log):
        """
        Preprocess the results of running a command.

        @type cmd: Products.ZenRRD.zencommand.Cmd
        @param cmd: the results of running a command, with the
        configuration from ZenHub
        @return: None.
        """

        # If the command was echoed back, strip it off
        if cmd.result.output.lstrip().startswith(cmd.command):
            cmd.result.output = cmd.result.output.lstrip()[len(cmd.command) :]

    def processResults(self, cmd, results):
        """
        Process the results of a running a command.

        @type cmd: Products.ZenRRD.zencommand.Cmd

        @param cmd: the results of running a command, with the
        configuration from ZenHub
        @param results: the values and events from the command output
        @return: None.
        """
        raise NotImplementedError

    @property
    def createDefaultEventUsingExitCode(self):
        """
        Property which can control whether events will be created
        based on the exit code of the command if no events are
        generated in the processResults function.
        """
        return True
