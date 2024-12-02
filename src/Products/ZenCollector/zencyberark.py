##############################################################################
#
# Copyright (C) Zenoss, Inc. 2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import argparse
import httplib
import json
import logging
import sys

from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import react

from .cyberark import get_cyberark


def configure_logging(verbose=False):
    logging._handlers.clear()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO if not verbose else logging.DEBUG)
    root.addHandler(handler)
    return logging.getLogger("zencyberark")


def check(args):
    log = configure_logging(args.verbose)
    log.info("Checking config")
    get_cyberark()
    return 0


@inlineCallbacks
def get(args):
    log = configure_logging(args.verbose)
    cyberark = get_cyberark()
    client = cyberark._manager._client

    log.info("Retrieving value for %s", args.query)
    try:
        code, result = yield client.request(args.query)
    except Exception as ex:
        mesg = "Unable to send request"
        if log.isEnabledFor(logging.DEBUG):
            log.exception(mesg)
        else:
            log.error(mesg + ": %s", ex)
        raise SystemExit(1)

    result = result.strip()
    if code != httplib.OK:
        try:
            decoded = json.loads(result)
        except Exception:
            log.error(
                "Query error  status=%s %s result=%s",
                code,
                httplib.responses.get(code),
                result,
            )
        else:
            log.error(
                "Query error  status=%s %s ErrorCode=%s ErrorMsg=%s",
                code,
                httplib.responses.get(code),
                decoded.get("ErrorCode"),
                decoded.get("ErrorMsg"),
            )
    elif len(result) == 0:
        log.error("Empty response")
        raise SystemExit(1)
    else:
        try:
            decoded = json.loads(result)
        except Exception as ex:
            log.error(
                "Failed to decode message body: %s  query=%s body=%s",
                ex,
                args.query,
                result,
            )
            raise SystemExit(1)
        else:
            log.info("Success  result=%s", decoded.get("Content"))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Model Catalog hacking tool",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="display more information",
    )
    subparsers = parser.add_subparsers(help="sub-command help")

    check_cmd = subparsers.add_parser(
        "check",
        help="Check CyberArk configuration",
    )
    check_cmd.set_defaults(func=check)

    get_cmd = subparsers.add_parser(
        "get",
        help="Get a value from CyberArk",
    )
    get_cmd.add_argument("query")
    get_cmd.set_defaults(func=get)

    return parser.parse_args()


def app(reactor):
    args = parse_args()
    return maybeDeferred(args.func, args)


def main():
    react(app)
