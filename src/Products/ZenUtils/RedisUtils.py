##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re
import redis

from .GlobalConfig import getGlobalConfiguration


REDIS_URL_RE = re.compile(
    r"^redis://"
    r"(?P<host>[^:/]+)"
    r"(:(?P<port>\d+))?"
    r"(/(?P<db>\d+))?"
    r"(\?(?P<optionStr>.+))?"
    r"$"
)

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def parseRedisUrl(url):
    """Parses url and returns a dict of redis options suitable for the
    redis client.
    """
    parsedUrl = REDIS_URL_RE.match(url)
    if parsedUrl is None:
        raise ValueError("malformed redis URL")
    host = parsedUrl.group('host')
    port = parsedUrl.group('port')
    port = 16379 if port is None else int(port)
    db = 0 if parsedUrl.group('db') is None else int(parsedUrl.group('db'))
    options = {'host': host, 'port': port, 'db': db}
    optStr = parsedUrl.group('optionStr')
    if optStr is not None and len(optStr):
        try:
            for s in optStr.split(","):
                key, value = s.split("=", 1)
                if value.isdigit():
                    value = int(value)
                if s in ['host', 'port', 'db']:
                    raise ValueError(
                        "Malformed redis URL, can not specify %r in "
                        "options string" % key
                    )
                options[key] = value
        except ValueError:
            raise
        except Exception as ex:
            raise ValueError("Malformed redis URL: %s", ex)
    return options


def getRedisUrl():
    return getGlobalConfiguration().get("redis-url", DEFAULT_REDIS_URL)


def getRedisClient(url=None):
    """Return an instance of a redis client.
    """
    if url is None:
        url = getRedisUrl()
    return redis.StrictRedis.from_url(url)
