#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import argparse
import json
import pprint
import sys
import time

from collections import defaultdict

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl
from Products.ZenUtils.requestlogging.ZopeRequestLogger import (
    ZopeRequestLogger,
)


SCRIPT_VERSION = "1.1.1"


class BCOLORS:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"


def get_redis_client():
    redis_url = getRedisUrl()
    redis_client = getRedisClient(redis_url)
    if redis_client is None:
        print("ERROR connecting to redis. redis URL: {0}".format(redis_url))
        print("Please check the redis-url value in global.conf")
        sys.exit(1)
    return redis_client


def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(
        version=SCRIPT_VERSION,
        description="Checks for unfinished Zope requests.",
        usage="""%(prog)s <command>
This program checks the status of the running zope processes.
    enable         Enables logging
    disable        Disables logging
    clear          Clears redis entries for zope requests.
    show           Shows outstanding zope requests.
    show-summary   Shows the number of outstanding requests
""",
    )
    parser.add_argument("command", help="command to execute")
    return parser.parse_args()


def clear_redis(redis_client):
    pattern = "{0}*".format(ZopeRequestLogger.REDIS_KEY_PATTERN)
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)
    print("Pending requests cleared from redis")


def print_summary(fingerprints):
    count_per_zope = defaultdict(int)
    for fingerprint in fingerprints:
        zope_id = fingerprint.split(":")[-2]
        count_per_zope[zope_id] = count_per_zope[zope_id] + 1
    summary = []
    for zope_id in sorted(count_per_zope.keys()):
        summary.append(
            "zope {0} => {1}".format(zope_id, count_per_zope[zope_id])
        )
    if summary:
        print("\t{0}".format("  |  ".join(summary)))


def print_details(redis_client, keys):
    requests = []
    for key in keys:
        # Is there any method to retrieve all
        # keys and values matching a key (mget?)
        value = redis_client.get(key)
        if not value:
            continue
        start_ts = key.split(":")[-1]
        running_for = time.time() - int(start_ts) / 1000
        requests.append((running_for, value))

    sorted_requests = sorted(requests)
    for running_for, value in sorted_requests:
        print(BCOLORS.BLUE + "-" * 50)
        print(" Request started {0} seconds ago".format(running_for))
        print("----" + BCOLORS.ENDC)
        pprint.pprint(json.loads(value))
    print(
        BCOLORS.BLUE
        + "\nTotal unfinished requests: {0}\n".format(len(requests))
        + BCOLORS.ENDC
    )


def print_all_not_finished_assigments(redis_client, summary=False):
    pattern = "{0}*".format(ZopeRequestLogger.REDIS_KEY_PATTERN)
    keys = redis_client.keys(pattern)
    color = BCOLORS.GREEN if len(keys) == 0 else BCOLORS.YELLOW
    print(color + "-" * 100)
    print("Found {0} unfinished requests".format(len(keys)).center(100))
    print("-" * 100 + BCOLORS.ENDC)
    if summary:
        print_summary(keys)
    elif keys:
        print_details(redis_client, keys)


def is_logging_enabled(redis_client):
    return redis_client.exists(ZopeRequestLogger.REDIS_ONGOING_REQUESTS_KEY)


def enable_logging(redis_client):
    print("Zope ongoing requests logging enabled for 1 hour")
    redis_client.set(ZopeRequestLogger.REDIS_ONGOING_REQUESTS_KEY, time.time())
    redis_client.expire(
        ZopeRequestLogger.REDIS_ONGOING_REQUESTS_KEY, 1 * 60 * 60
    )


def disable_logging(redis_client):
    if is_logging_enabled(redis_client):
        redis_client.delete(ZopeRequestLogger.REDIS_ONGOING_REQUESTS_KEY)
        clear_redis(redis_client)
        print("Zope ongoing requests logging disabled")


def main():
    """ """
    redis_client = get_redis_client()

    options = parse_options()

    if options.command == "enable":
        enable_logging(redis_client)
    elif options.command == "disable":
        disable_logging(redis_client)
    elif options.command == "clear":
        clear_redis(redis_client)
    elif options.command.startswith("show"):
        if not is_logging_enabled(redis_client):
            enable_logging(redis_client)
        summary = False
        if options.command == "show-summary":
            summary = True
        print_all_not_finished_assigments(redis_client, summary)
    sys.exit(0)


if __name__ == "__main__":
    main()
