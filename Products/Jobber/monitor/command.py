##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import Queue
import signal

from celery.bin.base import Command

from Products.ZenCollector.configcache.app.args import ZenHelpFormatter
from Products.ZenUtils.config import ConfigLoader
from Products.ZenUtils.path import zenPath

from .broker import Broker
from .collector import MetricsCollector
from .events import EventsMonitor
from .handler import EventsHandler
from .inspector import Inspector
from .logger import configure_logging, getLogger
from .metrics import ZenJobsMetrics
from .reporter import MetricsReporter


class MonitorCommand(Command):
    # Override create_parser to get a different formatter class.
    # @override
    def create_parser(self, prog_name, command=None):
        # for compatibility with optparse usage.
        usage = self.usage(command).replace("%prog", "%(prog)s")
        parser = self.Parser(
            prog=prog_name,
            usage=usage,
            epilog=self._format_epilog(self.epilog),
            formatter_class=ZenHelpFormatter,
            description=self._format_description(self.description),
        )
        self._add_version_argument(parser)
        self.add_preload_arguments(parser)
        self.add_arguments(parser)
        self.add_compat_options(parser, self.get_options())
        self.add_compat_options(parser, self.app.user_options["preload"])

        if self.supports_args:
            # for backward compatibility with optparse, we automatically
            # add arbitrary positional args.
            parser.add_argument(self.args_name, nargs="*")
        return self.prepare_parser(parser)

    # @override
    def add_arguments(self, parser):
        parser.add_argument(
            "--conf-file",
            default=zenPath("etc", "zenjobs-monitor.conf"),
            help="Pathname of configuration file",
        )

    # @override
    def run(self, *args, **options):
        conf_file = options["conf_file"]
        config = ConfigLoader(conf_file)()
        metric_interval = config.getint("metric-interval")
        log_filename = config.get("log-filename")
        log_level = config.get("log-level")
        log_max_file_count = config.getint("log-max-file-count")
        log_max_file_size = config.getint("log-max-file-size") * 1024
        configure_logging(
            level=log_level,
            filename=log_filename,
            maxcount=log_max_file_count,
            maxsize=log_max_file_size,
        )
        log = getLogger(self)
        try:
            eventqueue = Queue.Queue()
            reporter = MetricsReporter()
            metrics = ZenJobsMetrics()
            broker_url = self.app.connection().as_uri(include_password=True)

            broker = Broker(broker_url)
            inspector = Inspector(self.app)

            handler = EventsHandler(eventqueue, metrics, self.app)
            monitor = EventsMonitor(eventqueue, self.app)
            collector = MetricsCollector(
                broker, inspector, reporter, metrics, metric_interval
            )

            handler.start()
            monitor.start()
            collector.start()

            state = {"shutdown": False}

            def _handle_signal(state, signum, frame):
                state["shutdown"] = True

            signal.signal(
                signal.SIGTERM, lambda sn, fr: _handle_signal(state, sn, fr)
            )

            while True:
                try:
                    signal.pause()
                    if state["shutdown"]:
                        break
                except (KeyboardInterrupt, SystemExit):
                    break
        except Exception:
            log.exception("unexpected error")
        finally:
            collector.stop()
            handler.stop()
            handler.join()
            collector.join(timeout=1.0)
