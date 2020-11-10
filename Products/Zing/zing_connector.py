##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import requests
import time
import urlparse

from zope.component.factory import Factory
from zope.interface import implementer

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

from .fact import serialize_facts
from .interfaces import IZingConnectorClient, IZingConnectorProxy

log = logging.getLogger("zen.zing.zing-connector")

GLOBAL_ZING_CONNECTOR_URL = "zing-connector-url"
GLOBAL_ZING_CONNECTOR_ENDPOINT = "zing-connector-endpoint"
GLOBAL_ZING_CONNECTOR_TIMEOUT = "zing-connector-timeout"
DEFAULT_HOST = "http://localhost:9237"
DEFAULT_ENDPOINT = "/api/model/ingest"
PING_PORT = "9000"
PING_ENDPOINT = "/ping"
DEFAULT_TIMEOUT = 5
DEFAULT_BATCH_SIZE = 1000


class ZingConnectorConfig(object):
    def __init__(self, host=None, endpoint=None, timeout=None):
        host = (
            host
            or getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_URL)
            or DEFAULT_HOST
        )
        endpoint = (
            endpoint
            or getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_ENDPOINT)
            or DEFAULT_ENDPOINT
        )
        self.facts_url = urlparse.urljoin(host, endpoint)

        timeout = (
            timeout
            or getGlobalConfiguration().get(GLOBAL_ZING_CONNECTOR_TIMEOUT)
            or DEFAULT_TIMEOUT
        )
        self.timeout = timeout

        parts = urlparse.urlsplit(host)
        start = parts.netloc.rfind(":")
        if start != -1:
            newNetloc = parts.netloc[: start + 1] + PING_PORT
        else:
            newNetloc = parts.netloc + ":" + PING_PORT

        parts = list(parts)
        parts[1] = newNetloc
        adminUrl = urlparse.urlunsplit(tuple(parts))
        self.ping_url = urlparse.urljoin(adminUrl, PING_ENDPOINT)


@implementer(IZingConnectorClient)
class ZingConnectorClient(object):

    def __init__(self, config=None):
        if config is None:
            config = ZingConnectorConfig()
        self.config = config
        self.session = requests.Session()

    @property
    def facts_url(self):
        return self.config.facts_url

    @property
    def ping_url(self):
        return self.config.ping_url

    @property
    def client_timeout(self):
        return self.config.timeout

    def _send_facts(self, facts, already_serialized=False):
        resp_code = -1
        try:
            if not facts:  # nothing to send
                return 200
            if already_serialized:
                serialized = facts
            else:
                serialized = serialize_facts(facts)
            resp = self.session.put(
                self.facts_url, data=serialized, timeout=self.client_timeout
            )
            resp_code = resp.status_code
        except Exception as e:
            log.exception(
                "Unable to send facts. zing-connector URL: %s. Exception %s",
                self.facts_url,
                e,
            )
        return resp_code

    def _send_one_by_one(self, facts):
        failed = 0
        for fact in facts:
            serialized = serialize_facts([fact])
            resp_code = self._send_facts(serialized, already_serialized=True)
            if resp_code != 200:
                failed += 1
                log.warn("Error sending fact: %s", serialized)
        log.warn("%s out of %s facts were not processed.", failed, len(facts))
        return failed == 0

    def log_zing_connector_not_reachable(self, custom_msg=""):
        msg = "zing-connector is not available"
        if custom_msg:
            msg = "{}. {}".format(custom_msg, msg)
        log.error(msg)

    def send_facts(self, facts, ping=True):
        """
        @param facts: list of facts to send to zing connector
        @param ping: boolean indicating if it should ping zing-connector
            before sending the facts.
        @return: boolean indicating if all facts were successfully sent
        """
        if ping and not self.ping():
            self.log_zing_connector_not_reachable()
            return False
        resp_code = self._send_facts(facts)
        if resp_code != 200:
            log.error(
                "Error sending datamaps: zing-connector returned an "
                "unexpected response code (%s)", resp_code,
            )
            if resp_code == 500:
                log.info("Sending facts one by one to minimize data loss")
                return self._send_one_by_one(facts)
        return resp_code == 200

    def send_facts_in_batches(self, facts, batch_size=DEFAULT_BATCH_SIZE):
        """
        @param facts: list of facts to send to zing connector
        @param batch_size: doh
        """
        log.debug(
            "Sending %s facts to zing-connector in batches of %s.",
            len(facts),
            batch_size,
        )
        success = True
        if not self.ping():
            self.log_zing_connector_not_reachable()
            return False
        while facts:
            batch = facts[:batch_size]
            del facts[:batch_size]
            success = success and self.zing_connector.send_facts(
                batch, ping=False
            )
        return success is True

    def send_fact_generator_in_batches(
        self, fact_gen, batch_size=DEFAULT_BATCH_SIZE, external_log=None
    ):
        """
        @param fact_gen: generator of facts to send to zing connector
        @param batch_size: doh
        """
        if external_log is None:
            external_log = log
        external_log.debug(
            "Sending facts to zing-connector in batches of %s", batch_size
        )
        ts = time.time()
        count = 0
        if not self.ping():
            self.log_zing_connector_not_reachable()
            return False
        success = True
        batch = []
        for f in fact_gen:
            count += 1
            batch.append(f)
            if len(batch) % batch_size == 0:
                success = success and self.send_facts(batch, ping=False)
                batch = []
        if batch:
            success = success and self.send_facts(batch, ping=False)
        if count > 0:
            elapsed = time.time() - ts
            external_log.debug(
                "send_fact_generator_in_batches sent %s facts in %s seconds",
                count,
                elapsed,
            )
        return success is True

    def ping(self):
        resp_code = -1
        try:
            resp = self.session.get(self.ping_url, timeout=0.2)
            resp_code = resp.status_code
        except Exception:
            log.debug("Zing connector is unavailable at %s", self.ping_url)
        return resp_code == 200


@implementer(IZingConnectorProxy)
class ZingConnectorProxy(object):
    """This class provides a ZingConnectorClient per zope thread."""

    def __init__(self, context):
        self.context = context
        self.client = self.get_client(self.context)

    def get_client(self, context):
        """
        Retrieves/creates the zing connector client for the zope thread that
        is trying to access zing connector.
        """
        zodb_conn = getattr(self.context, "_p_jar", None)

        client = None
        # context is not a persistent object.
        # Create a temp client in a volatile variable.
        # Volatile variables are not shared across threads,
        # so each thread will have its own client.
        #
        if zodb_conn is None:
            if not hasattr(self, "_v_temp_zing_connector_client"):
                self._v_temp_zing_connector_client = ZingConnectorClient()
            client = self._v_temp_zing_connector_client
        else:
            #
            # context is a persistent object. Create/retrieve the client
            # from the zodb connection object. We store the client in the
            # zodb connection object so we are certain that each zope thread
            # has its own.
            client = getattr(zodb_conn, "zing_connector_client", None)
            if client is None:
                setattr(
                    zodb_conn, "zing_connector_client", ZingConnectorClient()
                )
                client = zodb_conn.zing_connector_client
        return client

    def send_facts(self, facts):
        return self.client.send_facts(facts)

    def send_facts_in_batches(self, facts, batch_size=DEFAULT_BATCH_SIZE):
        return self.client.send_facts_in_batches(facts, batch_size)

    def send_fact_generator_in_batches(
        self, fact_gen, batch_size=DEFAULT_BATCH_SIZE, external_log=None
    ):
        return self.client.send_fact_generator_in_batches(
            fact_gen, batch_size, external_log
        )

    def ping(self):
        return self.client.ping()


CLIENT_FACTORY = Factory(ZingConnectorClient)
