##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from twisted.internet import defer
from zope.component import adapter, getGlobalSiteManager
from zope.interface import implementer, providedBy

from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenRelations.PrimaryPathObjectManager import (
    PrimaryPathObjectManager,
)
from Products.ZenUtils.Utils import giveTimeToReactor

from .interfaces import IInvalidationProcessor, IHubCreatedEvent
from .zodb import UpdateEvent, DeletionEvent

log = logging.getLogger("zen.zenhub.invalidations")
INVALIDATIONS_PAUSED = "PAUSED"


@implementer(IInvalidationProcessor)
class InvalidationProcessor(object):
    """
    Registered as a global utility. Given a database hook and a list of oids,
    handles pushing updated objects to the appropriate services, which in turn
    cause collectors to be pushed updates.
    """

    _hub = None
    _hub_ready = None

    def __init__(self):
        self._hub_ready = defer.Deferred()
        getGlobalSiteManager().registerHandler(self.onHubCreated)

    @adapter(IHubCreatedEvent)
    def onHubCreated(self, event):
        self._hub = event.hub
        self._hub_ready.callback(self._hub)

    @defer.inlineCallbacks
    def processQueue(self, oids):
        yield self._hub_ready
        handled, ignored = 0, 0
        for oid in oids:
            try:
                obj = self._hub.dmd._p_jar[oid]
                # Don't bother with all the catalog stuff; we're depending on
                # primaryAq existing anyway, so only deal with it if it
                # actually has primaryAq.
                if isinstance(
                    obj, (PrimaryPathObjectManager, DeviceComponent)
                ):
                    handled += 1
                    event = _get_event(self._hub.dmd, obj, oid)
                    yield _notify_event_subscribers(event)
                else:
                    ignored += 1
            except KeyError:
                log.warning("object not found  oid=%r", oid)
        defer.returnValue((handled, ignored))


def _get_event(dmd, obj, oid):
    try:
        # Try to get the object
        obj = obj.__of__(dmd).primaryAq()
    except (AttributeError, KeyError):
        # Object has been removed from its primary path (i.e. was
        # deleted), so make a DeletionEvent
        log.debug("notifying services that %r has been deleted", obj)
        return DeletionEvent(obj, oid)
    else:
        # Object was updated, so make an UpdateEvent
        log.debug("notifying services that %r has been updated", obj)
        return UpdateEvent(obj, oid)


@defer.inlineCallbacks
def _notify_event_subscribers(event):
    gsm = getGlobalSiteManager()
    subscriptions = gsm.adapters.subscriptions(
        map(providedBy, (event.object, event)), None
    )
    for subscription in subscriptions:
        try:
            yield giveTimeToReactor(subscription, event.object, event)
        except Exception:
            log.exception(
                "failure in suscriber  subscriber=%r event=%r",
                subscription,
                event,
            )
