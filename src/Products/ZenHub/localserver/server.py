import logging

from twisted.web.server import Site

from .resource import ZenResource
from .options import add_options


class LocalServer(object):
    """
    Server class to listen to local connections.
    """

    buildOptions = staticmethod(add_options)

    def __init__(self, reactor, endpoint):
        self.__reactor = reactor
        self.__endpoint = endpoint

        root = ZenResource()
        self.__site = Site(root)

        self.__listener = None
        self.__log = logging.getLogger("zen.localserver")

    def add_resource(self, name, resource):
        self.__site.resource.putChild(name, resource)

    def start(self):
        """Start listening."""
        d = self.__endpoint.listen(self.__site)
        d.addCallbacks(self._success, self._failure)

    def stop(self):
        if self._listener:
            self._listener.stopListening()

    def _success(self, listener):
        self.__log.info("opened localhost port %d", self.__endpoint._port)
        self._listener = listener

    def _failure(self, error):
        self.__log.error(
            "failed to open local port  port=%s error=%r",
            self.__endpoint._port,
            error,
        )
        self.__reactor.stop()
