##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import json
import logging
import time

from datetime import datetime, timedelta

import redis
import yaml

from celery.beat import Scheduler
from celery.schedules import crontab

from .config import getConfig, ZenCeleryConfig


class ZenJobsScheduler(Scheduler):
    """A Celery beat scheduler for periodic jobs.

    The last run time and count of runs for each schedule entry are stored
    in Redis.

    The schedule is defined in a configuration file.  The configuration file
    is in YAML.  Each schedule entry has the following format:

        name-of-entry:
          task: "name of task"
          args: [list, of, positional, arguments, to, task]
          kwargs:
            key: value
          options:
            key: value
          schedule:
            <cron | interval>:
              <key/value for schedule>

    The required keys for an entry are 'task' and 'schedule'.

    An 'interval' schedule looks like the following:

        interval-example:
          task: "some.job"
          schedule:
            interval:
              seconds: 90

    This specifies that the 'interval-example' schedule will run the
    "some.job" task every 90 seconds.  Interval schedules accept only
    the 'seconds' key/value argument.

    A 'cron' schedule looks like the following:

        cron-example:
          task: "some.job"
          schedule:
            cron:
              minute: "*/15"
              hour: "8-17"
              day_of_week: "mon-fri"

    This specifies that the 'cron-example' schedule will run the "some.job"
    task every fifteen minutes, between the hours of 8am and 5pm, monday
    through friday.  The key/value arguments for a 'cron' schedule are
    'minute', 'hour', 'day_of_week', 'day_of_month', and 'month_of_year'.
    More details on cron are found here:
    https://docs.celeryproject.org/en/3.1/userguide/periodic-tasks.html#crontab-schedules
    """

    def __init__(self, *args, **kwargs):
        self.__entries = {}
        self.__log = logging.getLogger("zen.zenjobs.scheduler")
        super(ZenJobsScheduler, self).__init__(*args, **kwargs)

    def setup_schedule(self):
        """Initialize the scheduler."""
        # Retrieve the previously saved schedule from redis.
        raw_data = _getClient().get(_key("entries")) or "{}"
        schedule_stats = ScheduleStatsDecoder().decode(raw_data)

        # Retrieve the schedule from the configuration file
        schedule = load_schedule()

        relevant_stats = (
            (k, v) for k, v in schedule.iteritems() if k in schedule_stats
        )
        for name, entry in relevant_stats:
            entry_stats = schedule_stats[name]
            last_run_at = entry_stats["last_run_at"]
            if last_run_at is not None:
                last_run_at = datetime.fromtimestamp(last_run_at)
            entry["last_run_at"] = last_run_at
            entry["total_run_count"] = entry_stats["total_run_count"]

        # Update scheduler state
        self.update_from_dict(schedule)

        # Add 'default' entries to the schedule
        self.install_default_entries(schedule)

        for entry in self.schedule.values():
            self.__log.info("schedule loaded  %s", entry)

        # Save to redis.
        self.sync()

    @property
    def schedule(self):
        return self.__entries

    @property
    def info(self):
        return "    . schedule-file -> {}".format(
            getConfig().get("scheduler-config-file"),
        )

    def sync(self):
        stats = {
            k: {
                "total_run_count": v.total_run_count,
                "last_run_at": v.last_run_at,
            }
            for k, v in self.__entries.iteritems()
        }
        encoded = json.dumps(stats, cls=DatetimeEncoder)
        _getClient().set(_key("entries"), encoded)

    def close(self):
        self.sync()


_valid_fields = set(("task", "args", "kwargs", "options", "schedule"))


def load_schedule():
    configfile = getConfig().get("scheduler-config-file")
    with open(configfile, "r") as f:
        raw = yaml.load(f, Loader=yaml.loader.SafeLoader)
    parsed_schedule = {}
    for name, entry in raw.viewitems():

        # Check for unknown fields
        unknowns = set(entry) - _valid_fields
        if unknowns:
            raise RuntimeError(
                "Schedule '{}' contains invalid fields: {}".format(
                    name, ",".join(unknowns)
                )
            )

        # Extract known fields.
        fields = {
            k: entry[k]
            for k in ("task", "args", "kwargs", "options")
            if k in entry
        }

        # Convert the value of the 'args' field, if present, into a tuple.
        if "args" in fields:
            fields["args"] = tuple(fields["args"])

        # Transform the value of the 'schedule' field into its
        # specified object.
        schedule = entry["schedule"]
        if len(schedule) != 1:
            raise RuntimeError(
                "Schedule '{}' may have only one schedule".foramt(name)
            )
        if "cron" in schedule:
            cron_args = schedule["cron"]
            fields["schedule"] = crontab(**cron_args)
        elif "interval" in schedule:
            interval_args = schedule["interval"]
            fields["schedule"] = timedelta(**interval_args)
        else:
            raise RuntimeError(
                "Schedule '{}' has an unknown schedule type: {}".format(
                    name, schedule.keys()[0]
                )
            )

        parsed_schedule[name] = fields

    return parsed_schedule


class ScheduleStatsDecoder(json.JSONDecoder):
    """Convert "last_run_at" field values from UNIX times to datetimes."""

    def default(self, obj):
        if "last_run_at" in obj:
            obj["last_run_at"] = datetime.fromtimestamp(obj["last_run_at"])
        return obj


class DatetimeEncoder(json.JSONEncoder):
    """Encode datetime.datetime types into UNIX epoch timestamp."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return time.mktime(obj.timetuple()) + (obj.microsecond * 1e-6)


_keybase = "zenjobs:schedule:"
_keytemplate = "{}{{}}".format(_keybase)
# _keypattern = _keybase + "*"


def _key(name):
    """Return the redis key for the given name."""
    return _keytemplate.format(name)


def _getClient():
    """Create and return the ZenJobs JobStore client."""
    return redis.StrictRedis.from_url(ZenCeleryConfig.result_backend)


def handle_beat_init(*args, **kw):
    beat_logger = logging.getLogger("celery.beat")
    zenjobs_logger = logging.getLogger("zen.zenjobs")
    root_logger = logging.getLogger()
    root_logger.handlers = zenjobs_logger.handlers = beat_logger.handlers
