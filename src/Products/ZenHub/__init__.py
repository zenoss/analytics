##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

XML_RPC_PORT = 8081
PB_PORT = 8789
OPTION_STATE = 1
CONNECT_TIMEOUT = 60


def installReactor():
    # Tries to install epoll first, then poll, and if neither are
    # available, the default select reactor will install when
    # twisted.internet.reactor is imported.
    try:
        from select import epoll  # noqa F401
        from twisted.internet import epollreactor

        epollreactor.install()
    except ImportError:
        try:
            from select import poll  # noqa F401
            from twisted.internet import pollreactor

            pollreactor.install()
        except ImportError:
            pass
