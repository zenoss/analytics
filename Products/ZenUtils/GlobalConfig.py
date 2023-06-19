##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import os.path
import re
import sys

from optparse import OptionValueError, BadOptionError

from .config import Config, ConfigLoader
from .path import zenPath
from .Utils import getAllParserOptionsGen

log = logging.getLogger("zen.GlobalConfig")
CONFIG_FILE = zenPath("etc", "global.conf")
_KEYVALUE = re.compile(
    r"^[\s ]*(?P<key>[a-z_]+[a-z0-9_-]*)[\s]+(?P<value>[^\s#]+)", re.IGNORECASE
).search


def globalConfToDict():
    settings = {}
    globalConfFile = zenPath("etc", "global.conf")
    if os.path.exists(globalConfFile):
        with open(globalConfFile, "r") as f:
            for line in f.xreadlines():
                match = _KEYVALUE(line)
                if match:
                    value = match.group("value")
                    if value.isdigit():
                        value = int(value)
                    settings[match.group("key")] = value
    return settings


class GlobalConfig(Config):
    """
    A method for retrieving the global configuration options
    outside of a daemon. This is used to configure the
    AMQP connection in Zope and zenhub

    @todo Add validation for expected keys and values
    """


_GLOBAL_CONFIG = ConfigLoader(CONFIG_FILE, GlobalConfig)


def getGlobalConfiguration():
    return _GLOBAL_CONFIG()


def flagToConfig(flag):
    return flag.trim().lstrip("-").replace("-", "_")


def configToFlag(option):
    return "--" + option.strip().replace("_", "-")


def _convertConfigLinesToArguments(parser, lines):
    """
    Converts configuration file lines of the format:

       myoption 1
       mybooloption False

    to the equivalent command-line arguments for the specified OptionParser.
    For example, the configuration file above would return the argument
    list ['--myoption', '1', '--mybooloption'] if mybooloption has action
    store_false, and ['--myoption', '1'] if mybooloption has action store_true.

    @parameter parser: OptionParser object containing configuration options.
    @type parser: OptionParser
    @parameter lines: List of dictionary object parsed from a configuration
        file. Each option is expected to have 'type', 'key', 'value' entries.
    @type lines: list of dictionaries.
    @return: List of command-line arguments corresponding to the
        configuration file.
    @rtype: list of strings
    """
    # valid key
    #     an option's string without the leading "--"
    #     can differ from an option's destination
    validOpts = {
        opt.get_opt_string() for opt in getAllParserOptionsGen(parser)
    }

    args = []
    for line in lines:
        if line.get("type", None) != "option":
            continue
        optstring = configToFlag(line["key"])
        if optstring in validOpts:
            option = parser.get_option(optstring)
            value = line.get("value", "")
            boolean_value = (
                value.lower() in ("true", "yes", "1") if value else False
            )
            if option.action == "store_true":
                if boolean_value:
                    args.append(optstring)
            elif option.action == "store_false":
                if not boolean_value:
                    args.append(optstring)
            else:
                args.extend(
                    [
                        optstring,
                        line["value"],
                    ]
                )
        else:
            log.debug("Unknown option: %s", optstring)

    return args


class _GlobalConfParserAdapter(object):
    def __init__(self, parser):
        self.parser = parser

    def apply(self):
        self.parser.defaults = self._getGlobalConfigFileDefaults()
        return self.parser

    def _getGlobalConfigFileDefaults(self):
        # TODO: This should be refactored - duplicated code with CmdBase.
        """
        Parse a config file which has key-value pairs delimited by white space,
        and update the parser's option defaults with these values.
        """
        options = self.parser.get_default_values()
        lines = self._loadConfigFile(CONFIG_FILE)
        if lines:
            args = _convertConfigLinesToArguments(self.parser, lines)
            try:
                self.parser._process_args([], args, options)
            except (BadOptionError, OptionValueError):
                # Ignore it, we only care about our own options as defined
                # in the parser.
                pass
        return options.__dict__

    def _loadConfigFile(self, filename):
        # TODO: This should be refactored - duplicated code with CmdBase.
        """
        Parse a config file which has key-value pairs delimited by white space.

        @parameter filename: path to the configuration file
        @type filename: string
        """
        lines = []
        try:
            with open(filename) as file:
                for line in file:
                    if line.lstrip().startswith("#") or line.strip() == "":
                        lines.append({"type": "comment", "line": line})
                    else:
                        try:
                            key, value = line.strip().split(None, 1)
                        except ValueError:
                            lines.append(
                                {
                                    "type": "option",
                                    "line": line,
                                    "key": line.strip(),
                                    "value": None,
                                    "option": None,
                                }
                            )
                        else:
                            option = self.parser.get_option("--%s" % key)
                            lines.append(
                                {
                                    "type": "option",
                                    "line": line,
                                    "key": key,
                                    "value": value,
                                    "option": option,
                                }
                            )
        except IOError as e:
            errorMessage = (
                "WARN: unable to read config file {filename} -- skipping. "
                "({exceptionName}: {exception})".format(
                    filename=filename,
                    exceptionName=e.__class__.__name__,
                    exception=e,
                )
            )
            print(errorMessage, file=sys.stderr)
            return []

        return lines


def applyGlobalConfToParser(parser):
    return _GlobalConfParserAdapter(parser).apply()
