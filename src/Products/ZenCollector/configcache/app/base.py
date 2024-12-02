##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from signal import signal, SIGTERM, SIGHUP, SIGINT
from threading import Event

import attr

from MySQLdb import OperationalError

from ..utils import MetricReporter

from .config import add_config_arguments, getConfigFromArguments
from .init import initialize_environment
from .genconf import GenerateConfig
from .logger import add_logging_arguments, setup_logging, setup_debug_logging
from .pid import add_pidfile_arguments, pidfile
from .zodb import add_zodb_arguments, zodb

_delay = 10  # seconds


class Application(object):
    """Base class for applications."""

    @classmethod
    def from_args(cls, args):
        config = getConfigFromArguments(args.parser, args)
        return cls(config, args.task)

    def __init__(self, config, task):
        # config data from config files and CLI args
        self.config = config
        self.task = task

    def run(self):
        configs = getattr(self.task, "configs", ())
        overrides = getattr(self.task, "config_overrides", ())
        initialize_environment(configs=configs, overrides=overrides)
        setup_logging(self.config)
        setup_debug_logging(self.config)
        with pidfile(self.config):
            stop = Event()
            set_shutdown_handler(lambda x, y: _handle_signal(stop, x, y))
            controller = _Controller(stop)
            log = logging.getLogger(
                "zen.{}".format(self.task.__module__.split(".", 2)[-1])
            )
            log.info("application has started")
            try:
                # Setup Metric Reporting
                prefix = getattr(self.task, "metric_prefix", "")
                metric_reporter = MetricReporter(
                    tags={"internal": True}, prefix=prefix
                )

                # Run the application loop
                while not controller.shutdown:
                    try:
                        with zodb(self.config) as (db, session, dmd):
                            ctx = ApplicationContext(
                                controller,
                                db,
                                session,
                                dmd,
                                metric_reporter,
                            )
                            self.task(self.config, ctx).run()
                    except OperationalError as oe:
                        log.warn("Lost database connection: %s", oe)
                    except Exception:
                        log.exception("unhandled error")
                        controller.wait(_delay)
                    except BaseException as e:
                        log.warn("shutting down due to %s", e)
                        controller.quit()
            finally:
                log.info("application is quitting")

    @staticmethod
    def add_genconf_command(subparsers, parsers):
        GenerateConfig.add_command(subparsers, parsers)
        pass

    @staticmethod
    def add_all_arguments(parser):
        add_config_arguments(parser)
        add_pidfile_arguments(parser)
        add_logging_arguments(parser)
        add_zodb_arguments(parser)

    add_config_arguments = staticmethod(add_config_arguments)
    add_pidfile_arguments = staticmethod(add_pidfile_arguments)
    add_logging_arguments = staticmethod(add_logging_arguments)
    add_zodb_arguments = staticmethod(add_zodb_arguments)


@attr.s(frozen=True, slots=True)
class ApplicationContext(object):
    controller = attr.ib()
    db = attr.ib()
    session = attr.ib()
    dmd = attr.ib()
    metric_reporter = attr.ib()


class _Controller(object):
    def __init__(self, stop):
        self.__stop = stop

    @property
    def shutdown(self):
        return self.__stop.is_set()

    def quit(self):
        self.__stop.set()

    def wait(self, interval):
        self.__stop.wait(interval)


def _handle_signal(stop, signum, frame):
    stop.set()


def set_shutdown_handler(func):
    signal(SIGTERM, func)
    signal(SIGHUP, func)
    signal(SIGINT, func)
