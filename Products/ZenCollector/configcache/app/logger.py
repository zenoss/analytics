##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import argparse
import copy
import logging
import logging.config
import logging.handlers
import os
import signal

from Products.ZenUtils.path import zenPath

_default_config_template = {
    "version": 1,
    "disable_existing_loggers": True,
    "filters": {},
    "formatters": {
        "main": {
            "format": (
                "%(asctime)s.%(msecs)03d %(levelname)s %(name)s: "
                "%(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "main": {
            "formatter": "main",
            "class": "cloghandler.ConcurrentRotatingFileHandler",
            "filename": None,
            "maxBytes": None,
            "backupCount": None,
            "mode": "a",
            "filters": [],
        }
    },
    "loggers": {
        "": {"level": logging.WARN},
        "zen": {"level": logging.NOTSET},
    },
    "root": {
        "handlers": ["main"],
    },
}


def setup_logging(config):
    """Create formatting for log entries and set default log level."""
    logconfig = copy.deepcopy(_default_config_template)
    loglevel = config["log-level"]
    logconfig["loggers"]["zen"]["level"] = loglevel
    logconfig["handlers"]["main"]["filename"] = config["log-filename"]
    logconfig["handlers"]["main"]["maxBytes"] = (
        config["log-max-file-size"] * 1024
    )
    logconfig["handlers"]["main"]["backupCount"] = config["log-max-file-count"]
    logging.config.dictConfig(logconfig)


def setup_debug_logging(config):
    # Allow the user to dynamically lower and raise the logging
    # level without restarts.
    try:
        signal.signal(
            signal.SIGUSR1,
            lambda x, y: _debug_logging_switch(config["log-level"], x, y),
        )
    except ValueError:
        # If we get called multiple times, this will generate an exception:
        # ValueError: signal only works in main thread
        # Ignore it as we've already set up the signal handler.
        pass


def _debug_logging_switch(default_level, signum, frame):
    zenlog = logging.getLogger("zen")
    currentlevel = zenlog.getEffectiveLevel()
    if currentlevel == logging.DEBUG:
        if currentlevel == default_level:
            return
        zenlog.setLevel(default_level)
        logging.getLogger().setLevel(logging.WARN)
        zenlog.info(
            "restored logging level back to %s (%d)",
            logging.getLevelName(default_level) or "unknown",
            default_level,
        )
    else:
        zenlog.setLevel(logging.NOTSET)
        logging.getLogger().setLevel(logging.DEBUG)
        zenlog.info(
            "logging level set to %s (%d)",
            logging.getLevelName(logging.DEBUG),
            logging.DEBUG,
        )


def _level_as_int(v):
    try:
        return int(v)
    except ValueError:
        return logging.getLevelName(v.upper())


def _add_log_suffix(v):
    if not v.endswith(".log"):
        if not os.path.basename(v):
            raise ValueError("no filename for log file given")
        return v + ".log"
    return v


class LogLevel(argparse.Action):
    """Define a 'logging level' action for argparse."""

    def __init__(
        self,
        option_strings,
        dest,
        nargs=None,
        const=None,
        default="info",
        type=None,
        choices=None,
        help="Default logging severity level",
        **kwargs
    ):
        if nargs is not None:
            raise ValueError("'nargs' not supported for LogLevel action")
        if type is not None:
            raise ValueError("'type' not supported for LogLevel action")
        if const is not None:
            raise ValueError("'const' not supported for LogLevel action")
        choices = tuple(
            value
            for pair in sorted(
                (level_id, level_name.lower())
                for level_id, level_name in logging._levelNames.items()
                if isinstance(level_id, int) and level_id != 0
            )
            for value in pair
        )
        super(LogLevel, self).__init__(
            option_strings,
            dest,
            default=default,
            type=_level_as_int,
            choices=choices,
            help=help,
            **kwargs
        )

    def __call__(self, parser, namespace, values=None, option_string=None):
        setattr(namespace, self.dest, values)


def add_logging_arguments(parser):
    group = parser.add_argument_group("Logging Options")
    group.add_argument("-v", "--log-level", action=LogLevel)
    filename = "-".join(parser.prog.split(" ")[:-1]) + ".log"
    dirname = zenPath("log")
    group.add_argument(
        "--log-filename",
        default=os.path.join(dirname, filename),
        type=_add_log_suffix,
        help="Pathname of the log file.  If a directory path is not "
        "specified, the log file is save to {}".format(dirname),
    )
    group.add_argument(
        "--log-max-file-size",
        default=10240,
        type=int,
        help="Maximum size of log file in KB before starting a new file",
    )
    group.add_argument(
        "--log-max-file-count",
        default=3,
        type=int,
        help="Maximum number of archival log files to keep",
    )
