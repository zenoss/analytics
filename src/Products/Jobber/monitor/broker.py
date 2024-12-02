##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import requests

from six.moves.urllib.parse import urlparse, urljoin, quote_plus, unquote

from .logger import getLogger


class Broker(object):
    def __new__(cls, broker_url):
        scheme = urlparse(broker_url).scheme
        if scheme == "amqp":
            return RabbitMQ(broker_url)


class RabbitMQ(object):
    """Just enough API to satisfy collecting metrics from the broker."""

    def __init__(self, broker_url):
        parsed = urlparse(broker_url)
        self._host = parsed.hostname
        self._port = 15672
        self._vhost = quote_plus(parsed.path[1:])
        username = parsed.username
        password = parsed.password
        self._username = unquote(username) if username else username
        self._password = unquote(password) if password else password
        self._http_api = (
            "http://{username}:{password}@{host}:{port}/api/"
        ).format(
            username=self._username,
            password=self._password,
            host=self._host,
            port=self._port,
        )
        self._log = getLogger(self)

    def queues(self, names):
        if not names:
            return ()
        attempts = 1
        timeout = 1.0
        url = urljoin(self._http_api, "queues/" + self._vhost)
        params = {"columns": ",".join(["name", "messages"])}
        while True:
            try:
                r = requests.get(url, params=params, timeout=timeout)
            except requests.Timeout:
                if attempts < 3:
                    attempts += 1
                    timeout *= 2
                else:
                    self._log.warning(
                        "timed out requesting data from RabbitMQ"
                    )
                    return ()
            except Exception:
                self._log.exception(
                    "unexpected error while requesting data from RabbitMQ"
                )
            else:
                break

        if r.status_code != 200:
            r.raise_for_status()
        return tuple(q for q in r.json() if q["name"] in names)
