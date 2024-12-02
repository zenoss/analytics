##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import collections
import logging

from twisted.application.internet import backoffPolicy, ClientService
from twisted.internet import defer
from twisted.spread import pb

from Products.ZenUtils.PBUtil import setKeepAlive

from .errors import HubDown
from .server import ZenPBClientFactory

log = logging.getLogger("zen.zenhubclient")


class ZenHubClient(object):
    """
    A client for interacting with the ZenHub service.

    After start is called, this class automatically handles connecting to
    ZenHub, logging into ZenHub, and automatically reconnecting to ZenHub if
    the connection to ZenHub is corrupted for any reason.
    """

    def __init__(self, app, endpoint, credentials, timeout, reactor=None):
        """Initialize a CoreZenHubClient instance.

        :param app: Reference to the application object.
        :type app: pb.Referenceable
        :param endpoint: Where zenhub is found
        :type endpoint: IStreamClientEndpoint
        :param credentials: Credentials to log into ZenHub.
        :type credentials: IUsernamePassword
        :param float timeout: Seconds to wait before determining whether
            ZenHub is unresponsive.
        :type reactor: IReactorCore | None
        """
        self._clientref = app
        self._endpoint = endpoint
        self._credentials = credentials
        self._timeout = timeout
        self._reactor = _get_reactor(reactor)
        self._service = ClientService(
            self._endpoint,
            ZenPBClientFactory(),
            retryPolicy=_getBackoffPolicy(initialDelay=0.5, factor=3.0),
            prepareConnection=self._new_connection,
        )
        self._connected_callbacks = []
        self._disconnected_callbacks = []
        self._zenhubref = None
        self._instanceId = None
        self._services = {}

    @property
    def is_connected(self):
        # type: () -> bool
        """
        Returns True if there is a current connection to ZenHub.
        """
        return self._zenhubref is not None

    @property
    def instance_id(self):
        # type: () -> str | None
        """
        Return ZenHub's Control Center instance ID.

        The value is a string containing a number or is None.
        """
        return self._instanceId

    @property
    def services(self):
        # type: () -> collections.Mapping[str, pb.Referenceable]
        """
        Return the currently loaded ZenHub services.

        The return value is an immutable mapping of service names to service
        references.
        """
        return _FrozenDictProxy(self._services)

    def start(self):
        # type: () -> defer.Deferred
        """
        Start connecting to ZenHub.

        On a successful connection, the returned Deferred's callback is
        invoked with the ZenHub broker instance.  On failure, the errback
        is invoked with the error.

        :rtype: defer.Deferred
        """
        self._service.startService()
        log.debug("started client service  service=%r", self._service)
        return self._service.whenConnected()

    def stop(self):
        # type: () -> defer.Deferred
        """
        Stop connecting to ZenHub.

        When the connection is closed, the returned Deferred is called.

        :rtype: defer.Deferred
        """
        try:
            return self._service.stopService()
        finally:
            self._reset()

    def notify_on_connect(self, f):
        """
        Register a callable for invocation when a ZenHub connection has
        been created or recreated.
        """
        self._connected_callbacks.append(f)

    def notify_on_disconnect(self, f):
        """
        Register a callable for invocation when ZenHub is disconnected.

        Once a callable has been invoked, it is removed from the set of
        callables.  It is recommended that callables for disconnect
        notifications should be registered by the callables registered for
        connection notifications.
        """
        self._disconnected_callbacks.append(f)

    @defer.inlineCallbacks
    def ping(self):
        """
        If connected to ZenHub, 'pings' ZenHub.

        The response will be "pong" if successful.
        """
        if self._zenhubref is None:
            raise HubDown("not connected to ZenHub")
        response = yield self._zenhubref.callRemote("ping")
        defer.returnValue(response)

    @defer.inlineCallbacks
    def register_worker(self, worker, instanceId, worklistId):
        """
        Register the worker as a zenhubworker with ZenHub.

        The worker is identified by `instanceId` and `worklistId`.

        @param worker: the worker that will accept RPC calls from ZenHub.
        @type worker: pb.IReferenceable
        @param instanceId: the worker's name
        @type instanceId: str
        @param worklistId: the 'queue' the worker accepts work from
        @type worklistId: str
        """
        if self._zenhubref is None:
            raise HubDown("not connected to ZenHub")
        yield self._zenhubref.callRemote(
            "reportForWork",
            worker,
            name=instanceId,
            worklistId=worklistId,
        )

    @defer.inlineCallbacks
    def unregister_worker(self, instanceId, worklistId):
        """
        Unregister the worker from ZenHub.

        The worker is identified by `instanceId` and `worklistId`.

        @param instanceId: the worker's name
        @type instanceId: str
        @param worklistId: the 'queue' the worker accepts work from
        @type worklistId: str
        """
        if self._zenhubref is None:
            raise HubDown("not connected to ZenHub")
        yield self._zenhubref.callRemote(
            "resignFromWork",
            name=instanceId,
            worklistId=worklistId,
        )

    @defer.inlineCallbacks
    def get_service(self, name, monitor, listener, options):
        # type: (str, str, object, collections.Mapping) -> defer.Deferred
        """
        Return a reference to the named ZenHub service.

        :param name: Name of the service
        :param monitor: Name of the collector
        :param listener: Object reference to caller
        :param options: key/value data relevant to the service
        """
        if self._zenhubref is None:
            raise HubDown("not connected to ZenHub")

        if name in self._services:
            defer.returnValue(self._services[name])

        service_ref = yield self._zenhubref.callRemote(
            "getService", name, monitor, listener, options
        )
        self._services[name] = service_ref
        log.debug(
            "retrieved remote reference to ZenHub service  "
            "name=%s collector=%s service=%r",
            name,
            monitor,
            service_ref,
        )
        defer.returnValue(service_ref)

    @defer.inlineCallbacks
    def _new_connection(self, broker):
        log.debug("connected to ZenHub  broker=%r", broker)
        try:
            if hasattr(broker.transport, "socket"):
                setKeepAlive(broker.transport.socket)
            else:
                log.warning("broker.transport.socket attribute is missing")

            self._zenhubref = yield self._login(broker)

            self._instanceId = yield self._zenhubref.callRemote(
                "getHubInstanceId"
            )
        except defer.CancelledError:
            log.error("timed out trying to login to ZenHub")
            raise
        except pb.RemoteError as ex:
            log.error(
                "login rejected by ZenHub  error=%s message=%s",
                ex.remoteType,
                ex.args[0] if ex.args else "",
            )
            raise
        except Exception:
            log.exception("unexpected error communicating with ZenHub")
            raise
        else:
            log.info("connected to ZenHub  instance-id=%s", self._instanceId)
            # Connection complete; install a listener to be notified if
            # the connection is lost.
            broker.notifyOnDisconnect(self._disconnected)

            log.debug(
                "calling %d on-connect callbacks",
                len(self._connected_callbacks),
            )
            for callback in self._connected_callbacks:
                try:
                    yield defer.maybeDeferred(callback)
                except Exception:
                    log.exception(
                        "connect callback error  callback=%r", callback
                    )

    def _login(self, broker):
        d = broker.factory.login(self._credentials, self._clientref)
        timeoutCall = self._reactor.callLater(self._timeout, d.cancel)

        def completedLogin(arg):
            if timeoutCall.active():
                timeoutCall.cancel()
            return arg

        d.addBoth(completedLogin)
        return d

    def _disconnected(self):
        logmethod = log.warning if self._service.running else log.info
        logmethod("disconnected from ZenHub")
        self._reset()
        while len(self._disconnected_callbacks):
            callback = self._disconnected_callbacks.pop(0)
            try:
                callback()
            except Exception:
                log.exception(
                    "disconnect callback error  callback=%r", callback
                )

    def _reset(self):
        self._zenhubref = None
        self._services.clear()


def _get_reactor(reactor):
    if reactor is None:
        from twisted.internet import reactor as global_reactor

        return global_reactor
    else:
        return reactor


class _FrozenDictProxy(collections.Mapping):
    def __init__(self, data):
        self.__data = data

    def __getitem__(self, key):
        return self.__data[key]

    def __contains__(self, key):
        return key in self.__data

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return iter(self.__data)


def _getBackoffPolicy(*args, **kw):
    policy = backoffPolicy(*args, **kw)

    def _policy(attempt):
        log.info(
            "no connection to ZenHub; is ZenHub running?  attempt=%s", attempt
        )
        return policy(attempt)

    return _policy
