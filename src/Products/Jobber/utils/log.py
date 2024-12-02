##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import inspect
import logging
import os
import sys

from functools import wraps

import six

from celery._state import get_current_task
from celery.utils.log import (
    LoggingProxy as _LoggingProxy,
    logger_isa as _logger_isa,
    _in_sighandler,
)
from kombu.log import get_logger as _get_logger
from kombu.utils.encoding import safe_str

__all__ = (
    "get_logger",
    "get_task_logger",
    "FormatStringAdapter",
    "TaskFormatter",
    "WorkerFilter",
    "LoggingProxy",
)

_base_logname = "zen.zenjobs"
_base_task_logname = "zen.zenjobs.job"

base_logger = _get_logger(_base_logname)


def get_logger(name=_base_logname):
    """Return the logger for the given name."""
    logger = _get_logger(name)
    if (
        logging.root not in (logger, logger.parent)
        and logger is not base_logger
        and not _logger_isa(logger, base_logger)
    ):
        logger.parent = base_logger
    return logger


task_logger = get_logger(_base_task_logname)


def get_task_logger(name=None):
    """Return the task logger for the given name."""
    name = name.split(".")[-1] if name else ""
    if name:
        name = "%s.%s" % (_base_task_logname, name.lower())
    else:
        name = _base_task_logname
    logger = get_logger(name)
    if not _logger_isa(logger, task_logger):
        logger.parent = task_logger
    return logger


class FormatStringAdapter(logging.LoggerAdapter):
    """This adapter supports the use of '{}' format strings for log messages.

    Usage:

        log = FormatStringAdapter(log.getLogger("zen"))
        log.info("Hello {}!", "world")

        d = {'a': 1234}
        log.info("Value of a -> {0[a]}", d)  # Value of a -> 1234
    """

    # This implementation is based on the StyleAdapter example given in
    # https://docs.python.org/3/howto/logging-cookbook.html

    def __init__(self, logger, extra=None):
        """Initialize an instance of FormatStringAdapter.

        :param Logger logger: The logger to adapt.
        :param extra: Additional context variables to appy to the
            message template string (not the message itself).
        :type extra: Mapping[str, Any]
        """
        super(FormatStringAdapter, self).__init__(logger, extra or {})

    def log(self, level, msg, *args, **kwargs):
        """Log a message at the indicated level."""
        if self.isEnabledFor(level):
            msg, kwargs = self.process(msg, kwargs)
            self.logger._log(level, _Message(msg, args), (), **kwargs)

    def debug(self, msg, *args, **kwargs):
        """Log a DEBUG message."""
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """Log an INFO message."""
        self.log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Log a WARNING message."""
        self.log(logging.WARNING, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        """Log a WARN message."""
        self.log(logging.WARN, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Log an ERROR message."""
        self.log(logging.ERROR, msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """Log an ERROR message with exception traceback."""
        if self.isEnabledFor(logging.ERROR):
            msg, kwargs = self.process(msg, kwargs)
            kwargs["exc_info"] = 1
            self.logger._log(logging.ERROR, _Message(msg, args), (), **kwargs)

    def critical(self, msg, *args, **kwargs):
        """Log a CRITICAL message."""
        self.log(logging.CRITICAL, msg, *args, **kwargs)


class _Message(object):
    def __init__(self, fmt, args):
        self.fmt = fmt
        self.args = args

    def __str__(self):
        return self.fmt.format(*self.args)


class TaskFormatter(logging.Formatter):
    """Format log messages based on context."""

    def __init__(self, base=None, task=None, datefmt=None):
        """Initialize a TaskFormatter instance."""
        self._base = base
        self._task = task
        super(TaskFormatter, self).__init__(datefmt=datefmt)

    def format(self, record):  # noqa: A003
        task = get_current_task()
        if task and task.request:
            self._fmt = self._task
            record.__dict__.update(
                taskid=task.request.id,
                taskname=task.name,
            )
        else:
            self._fmt = self._base
        return super(TaskFormatter, self).format(record)


class WorkerFilter(logging.Filter):
    """Adds CC data to the LogRecord."""

    def __init__(self):
        """Initialize a WorkerFilter instance."""
        super(WorkerFilter, self).__init__()
        self.instance = os.environ.get("CONTROLPLANE_INSTANCE_ID")

    def filter(self, record):  # noqa: A003
        """Append 'instance' to the LogRecord."""
        record.instance = self.instance
        return True  # keep the record


class LoggingProxy(_LoggingProxy):
    """File like object that forwards writes to a logging.Logger instance."""

    def write(self, data):
        """Write data to the logger."""
        if _in_sighandler:
            return print(safe_str(data), file=sys.__stderr__)
        if getattr(self._thread, "recurse_protection", False):
            # Logger is logging back to this file, so stop recursing.
            return
        if self.closed:
            return
        self._thread.recurse_protection = True
        try:
            for line in data.rstrip().splitlines():
                self.logger.log(self.loglevel, safe_str(line.rstrip()))
        finally:
            self._thread.recurse_protection = False


class ForwardingHandler(logging.Handler):
    """Forwards log records to another handler."""

    def __init__(self, target, level=logging.NOTSET):
        self.__target = target
        super(ForwardingHandler, self).__init__(level=level)

    def emit(self, record):
        self.__target.emit(record)


_task_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_task_datefmt = "%Y-%m-%d %H:%M:%S"


class TaskLogFileHandler(logging.FileHandler):
    """Extend FileHandler for task logging."""

    def __init__(self, *args, **kwargs):
        """Initialize a TaskLogFileHandler instance."""
        super(TaskLogFileHandler, self).__init__(*args, **kwargs)
        self.setFormatter(
            logging.Formatter(fmt=_task_format, datefmt=_task_datefmt)
        )


class inject_logger(object):
    """Decorator that will insert a logger object as the first argument."""

    def __init__(self, log=None, adapter=None, aschild=True):
        if log:
            if isinstance(log, logging.getLoggerClass()):
                self.baselog = log
            elif callable(log):
                baselog = log()
                if not isinstance(baselog, logging.getLoggerClass()):
                    raise TypeError("'log' callable does produce a logger")
                self.baselog = baselog
            elif isinstance(log, six.string_types):
                self.baselog = logging.getLogger(log)
            else:
                raise TypeError(
                    "'log' is not a reference to a logger: {}".format(log),
                )
        else:
            self.baselog = None
        if aschild:
            self.getlogger = self.__getChildLogger
        else:
            self.getlogger = self.__getLogger
        self.adapter = adapter if adapter else lambda x: x

    def __getChildLogger(self, name):
        return self.baselog.getChild(name)

    def __getLogger(self, ignored):
        return self.baselog

    def __call__(self, func):
        if self.baselog:
            log = self.getlogger(func.func_name)
        else:
            names = []
            if hasattr(func, "im_class"):
                cls = func.im_class
                mod = inspect.getmodule(cls)
                fname = func.im_func.func_name
                names[:] = [mod.__name__, cls.__name__, fname]
            else:
                mod = inspect.getmodule(func)
                fname = func.func_name
                names[:] = [mod.__name__, fname]
            log = logging.getLogger("zen.{}".format(".".join(names)))

        log = self.adapter(log)

        @wraps(func)
        def inject(*args, **kw):
            return func(log, *args, **kw)

        return inject


class NullLogger(object):
    """Defines an object that returns empty callables."""

    def __getattr__(self, name):
        return lambda *x: None
