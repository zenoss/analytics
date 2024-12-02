##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

import attr

from attr.validators import instance_of
from twisted.internet import defer
from twisted.spread import pb

from Products.ZenHub.errors import RemoteException

from .service import ServiceRegistry
from .utils import getLogger


@attr.s(slots=True, frozen=True)
class Worker(object):
    """
    Wraps zenhubworker RemoteReference objects.
    """

    name = attr.ib(converter=str)
    """Name of the zenhubworker"""

    remote = attr.ib(validator=instance_of(pb.RemoteReference))
    """Remote reference to the zenhubworker"""

    services = attr.ib(factory=ServiceRegistry)
    """Mapping of ZenHub service references used by this worker"""

    @defer.inlineCallbacks
    def run(self, call):
        """Execute the call.

        @param call: Details on the RPC method to invoke.
        @type call: ServiceCall
        @raises Exception if an error occurs while attempting to
            execute a remote procedure call.  An RPC error may occur while
            retrieving the remote service reference or when invoking the
            job specified method on the remote service reference.
        """
        log = getLogger(self)
        service = yield self._get_service(call.service, call.monitor, log)
        try:
            result = yield service.callRemote(
                call.method, *call.args, **call.kwargs
            )
            log.debug(
                "remote method executed  service=%s method=%s id=%s worker=%s",
                call.service,
                call.method,
                call.id.hex,
                self.name,
            )
            defer.returnValue(result)
        except (RemoteException, pb.RemoteError) as ex:
            if log.isEnabledFor(logging.DEBUG):
                log.error(
                    "remote method failed  "
                    "service=%s method=%s id=%s worker=%s error=%s",
                    call.service,
                    call.method,
                    call.id.hex,
                    self.name,
                    ex,
                )
            raise
        except Exception as ex:
            if log.isEnabledFor(logging.DEBUG):
                log.error(
                    "failed to execute remote method  "
                    "service=%s method=%s id=%s worker=%s error=(%s) %s",
                    call.service,
                    call.method,
                    call.id.hex,
                    self.name,
                    ex.__class__.__name__,
                    ex,
                )
            raise

    @defer.inlineCallbacks
    def _get_service(self, service, monitor, log):
        """Retrieve a service reference asynchronously."""
        svcref = self.services.get(monitor, service)
        if svcref is None:
            try:
                svcref = yield self.remote.callRemote(
                    "getService", service, monitor
                )
                self.services.add(monitor, service, svcref)
                log.debug(
                    "retrieved remote service  service=%s worker=%s",
                    service,
                    self.name,
                )
            except Exception as ex:
                if log.isEnabledFor(logging.DEBUG):
                    log.error(
                        "failed to retrieve remote service  "
                        "service=%s worker=%s error=(%s) %s",
                        service,
                        self.name,
                        ex.__class__.__name__,
                        ex,
                    )
                raise
        defer.returnValue(svcref)
