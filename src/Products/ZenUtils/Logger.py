##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging
import time
import types

FATAL = 5
CRITICAL = 4
WARNING = 3
INFORMATION = 2
DEBUG = 1

severities = ("NONE", "DEBUG", "WARNING", "CRITICAL", "FATAL")


def logger(level, message):
    """logger(level, message) -> log message with levl and time"""
    print(time.asctime() + " " + severities[level] + ": " + message)


class HtmlFormatter(logging.Formatter):
    """
    Formatter for the logging class
    """

    def __init__(self):
        logging.Formatter.__init__(
            self,
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

    def formatException(self, exc_info):
        """
        Format a Python exception
        @param exc_info: Python exception containing a description of
            what went wrong
        @type exc_info: Python exception class
        @return: formatted exception
        @rtype: string
        """
        exc = logging.Formatter.formatException(self, exc_info)
        return """%s""" % exc


def setWebLoggingStream(stream):
    """
    Setup logging to log to a browser using a request object.
    @param stream: IO stream
    @type stream: stream class
    @return: logging handler
    @rtype: logging handler
    """
    handler = logging.StreamHandler(stream)
    handler.setFormatter(HtmlFormatter())
    rlog = logging.getLogger()
    rlog.addHandler(handler)
    rlog.setLevel(logging.ERROR)
    zlog = logging.getLogger("zen")
    zlog.setLevel(logging.INFO)
    return handler


def clearWebLoggingStream(handler):
    """
    Clear our web logger.
    @param handler: logging handler
    @type handler: logging handler
    """
    rlog = logging.getLogger()
    rlog.removeHandler(handler)


def setLogLevel(level=logging.DEBUG, loggerName=None):
    """
    Change the logging level to allow for more insight into the
    in-flight mechanics of Zenoss.
    @parameter level: logging level at which messages display (eg logging.INFO)
    @type level: integer
    """
    # set the specified logger to level
    if loggerName:
        logging.getLogger(loggerName).setLevel(level)
    log = logging.getLogger()
    log.setLevel(level)
    # set root handlers to be able to log at given level
    for handler in log.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(level)


def getLogger(app, cls=None):
    """Return the logger object named "zen.<app>.<cls name>".

    E.g. given,
        logger = getLogger("zenhub", Products.ZenHub.services.ModelerService)
    then 'logger' will have the name "zen.zenhub.ModelerService".
    If an object is passed in rather than a class, the object's class is used.
    Modules are handled as if a class were passed in.
    """
    segments = ["zen", app]
    if cls is not None:
        if hasattr(cls, "__class__"):
            if isinstance(cls, types.InstanceType):
                cls = cls.__class__
            elif isinstance(cls, types.ModuleType):
                pass  # Avoid matching the next elif statement.
            elif not isinstance(cls, types.TypeType):
                cls = type(cls)
        segments.append(cls.__name__.split(".")[-1])
    name = ".".join(segments)
    return logging.getLogger(name)
