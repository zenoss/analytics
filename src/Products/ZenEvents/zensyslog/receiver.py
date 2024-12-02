##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2011, 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import os
import socket

from twisted.internet import reactor

log = logging.getLogger("zen.zensyslog.receiver")


class Receiver(object):
    """
    Listens for syslog messages and turns them into Zenoss events.
    """

    def __init__(self, protocol, portfactory):
        self._protocol = protocol
        self._portfactory = portfactory
        self._port = None

    def start(self):
        self._port = self._portfactory(self._protocol)

    def stop(self):
        if self._port is None:
            return
        self._port.stopListening()
        self._port = None


class CreatePort(object):
    def __init__(self, port, interface):
        self._port = port
        self._interface = interface

    def __call__(self, protocol):
        return reactor.listenUDP(
            self._port, protocol, interface=self._interface
        )


class AdoptPort(object):
    def __init__(self, fd):
        self._fd = fd

    def __call__(self, protocol):
        # Create a datagram socket from the specific file descriptor
        sock = socket.fromfd(self._fd, socket.AF_INET, socket.SOCK_DGRAM)

        # No longer need the file descriptor; `fromfd` created a duplicate.
        os.close(self._fd)
        del self._fd

        # Set the socket non-blocking
        sock.setblocking(False)

        try:
            # Adopt the socket and keep a reference to the IListeningPort.
            return reactor.adoptDatagramPort(
                sock.fileno(), socket.AF_INET, protocol
            )
        finally:
            # No longer need the socket;
            # `adoptDatagramPort` created a duplicate.
            sock.close()
