##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from contextlib import closing

from metrology import Metrology
from twisted.internet import defer
from zenoss.protocols.amqp import Publisher as BlockingPublisher
from zenoss.protocols.exceptions import NoRouteException
from zenoss.protocols.interfaces import IQueueSchema, IAMQPConnectionInfo
from zenoss.protocols.protobufs import modelevents_pb2
from zenoss.protocols.protobufs.zep_pb2 import Event
from zenoss.protocols.protobufutil import ProtobufEnum
from zenoss.protocols.twisted.amqp import AMQPFactory
from zope.component import getUtility
from zope.event import notify
from zope.interface import implementer

from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenUtils.guid import generate
from Products.ZenUtils.AmqpDataManager import AmqpDataManager
from Products.ZenMessaging.ChangeEvents.events import (
    MessagePostPublishingEvent,
    MessagePrePublishingEvent,
)

from .interfaces import (
    IEventPublisher,
    IModelProtobufSerializer,
    IProtobufSerializer,
    IQueuePublisher,
)

log = logging.getLogger("zen.queuepublisher")

MODEL_TYPE = ProtobufEnum(modelevents_pb2.ModelEvent, "model_type")


class ModelChangePublisher(object):
    """
    Keeps track of all the model changes so far in this
    transaction. Do not instantiate this class directly,
    use "getModelChangePublisher" to receive the singleton
    """

    def __init__(self):
        self._events = []

        # shortcut to object references of the events
        self._events_ref = []

        self._msgs = []
        self._addedGuids = set()
        self._modifiedGuids = set()
        self._removedGuids = set()
        self._publishable = []
        self._discarded = 0
        self._total = 0
        self._maintWindowChanges = []

    def _createModelEventProtobuf(self, ob, eventType):
        """
        Creates and returns a ModelEvent. This is tightly
        coupled to the modelevent.proto protobuf.
        """
        try:
            serializer = IModelProtobufSerializer(ob)

            event = modelevents_pb2.ModelEvent()
            self._events.append(event)

            event.event_uuid = generate()
            event.type = getattr(event, eventType)

            type = serializer.modelType
            event.model_type = MODEL_TYPE.getNumber(type)
            proto = getattr(event, type.lower(), None)
            if proto:
                if eventType == "REMOVED":
                    guid = self._getGUID(ob)
                    proto.uuid = guid
                else:
                    serializer.fill(proto)
            return event
        except TypeError:
            log.debug("Could not adapt %r to a protobuf serializer.", ob)

    def _getGUID(self, ob):
        return str(IGlobalIdentifier(ob).create())

    def publishAdd(self, ob):
        """
        Schedules a ModelChange event message with the 'ADDED' operation for
        ob.

        This method and the publishRemove method maintain the following set
        invariants after their execution:
            - _removedGuids & _addedGuids == set()
            - guid in (_removedGuids | _addedGuids)
            - _total == # of calls to publish*
            - len([
                  msg
                  for msg in _msgs
                  if msg[1][0] == ob and msg[1][1] in ('ADDED', 'REMOVED')
              ]) == 1
        In addition, this method assures:
            - guid in _addedGuids
            - (function, (ob, 'ADDED')) in _msgs
        @param ob: the object added to the model
        @type ob: IGlobalIdentifier
        """
        self._total += 1
        guid = self._getGUID(ob)
        if guid not in self._addedGuids:
            if guid in self._removedGuids:
                # Get rid of the previously scheduled removal of this object
                try:
                    self._msgs.remove(
                        (self._createModelEventProtobuf, (ob, "REMOVED"))
                    )
                    self._events_ref.remove((ob, guid, "REMOVED"))
                except ValueError:
                    pass
                self._removedGuids.remove(guid)
                self._discarded += 1

            self._msgs.append((self._createModelEventProtobuf, (ob, "ADDED")))
            self._events_ref.append((ob, guid, "ADDED"))

            self._addedGuids.add(guid)
        else:
            self._discarded += 1

    def publishRemove(self, ob):
        """
        Schedules a ModelChange event message with the 'REMOVED' operation
        for ob.

        This method and the publishAdd method maintain the following set
        invariants after their execution:
            - _removedGuids & _addedGuids == set()
            - guid in (_removedGuids | _addedGuids)
            - _total == # of calls to publish*
            - len([
                  msg
                  for msg in _msgs
                  if msg[1][0] == ob and msg[1][1] in ('ADDED', 'REMOVED')
              ]) == 1
        In addition, this method assures:
            - guid in _removedGuids
            - (function, (ob, 'REMOVED')) in _msgs
        @param ob: the object added to the model
        @type ob: IGlobalIdentifier
        """
        self._total += 1
        guid = self._getGUID(ob)
        if guid not in self._removedGuids:
            if guid in self._addedGuids:
                # get rid of the previously scheduled add of this object
                try:
                    self._msgs.remove(
                        (self._createModelEventProtobuf, (ob, "ADDED"))
                    )
                    self._events_ref.remove((ob, guid, "ADDED"))
                except ValueError:
                    pass
                self._addedGuids.remove(guid)
                self._discarded += 1

            self._msgs.append(
                (self._createModelEventProtobuf, (ob, "REMOVED"))
            )
            self._events_ref.append((ob, guid, "REMOVED"))

            self._removedGuids.add(guid)
        else:
            self._discarded += 1

    def publishModified(self, ob, maintWindowChange=False):
        self._total += 1

        guid = self._getGUID(ob)
        if maintWindowChange:
            self._maintWindowChanges.append(guid)

        def _createModified(object):
            # Do the check again in case an add was added afterwards.
            # This happens when an object is modified before it is attached.
            if guid not in self._addedGuids:
                self._createModelEventProtobuf(object, "MODIFIED")
            else:
                self._discarded += 1

        if guid not in self._addedGuids and guid not in self._modifiedGuids:
            self._msgs.append((_createModified, (ob,)))
            self._modifiedGuids.add(guid)
            self._events_ref.append((ob, guid, "MODIFIED"))
        else:
            self._discarded += 1

    def addToOrganizer(self, ob, org):
        def createEvent(ob, organizer):
            event = self._createModelEventProtobuf(ob, "ADDRELATION")

            org_guid = self._getGUID(organizer)
            event.add_relation.destination_uuid = org_guid

        guid = self._getGUID(ob)
        self._msgs.append((createEvent, (ob, org)))
        self._events_ref.append((ob, guid, "ADDRELATION"))

    def removeFromOrganizer(self, ob, org):
        def createEvent(ob, organizer):
            event = self._createModelEventProtobuf(ob, "REMOVERELATION")

            org_guid = self._getGUID(organizer)
            event.remove_relation.destination_uuid = org_guid

        guid = self._getGUID(ob)
        self._msgs.append((createEvent, (ob, org)))
        self._events_ref.append((ob, guid, "REMOVERELATION"))

    def moveObject(self, ob, fromOb, toOb):
        guid = self._getGUID(ob)
        event = self._createModelEventProtobuf(ob, "MOVED")

        def createEvent(ob, fromObj, toObj):
            event.moved.origin = self._getGUID(fromObj)
            event.moved.destination = self._getGUID(toObj)

        self._msgs.append((createEvent, (ob, fromOb, toOb)))
        self._events_ref.append((ob, guid, "MOVED"))

    @property
    def events(self):
        log.debug(
            "discarded %s messages of %s total", self._discarded, self._total
        )
        for fn, args in self._msgs:
            fn(*args)
        return self._events


def getModelChangePublisher():
    """
    Adds a synchronizer to the transaction and keep track if a
    synchronizer is on the transaction.
    """
    import transaction

    tx = transaction.get()
    # check to see if there is a publisher on the transaction
    log.debug("getting publisher on tx %s", tx)
    if not getattr(tx, "_synchronizedPublisher", None):
        tx._synchronizedPublisher = ModelChangePublisher()
        # Create new PublishSynchronizer also add after completion hook
        # so that client/channel can be closed.
        pSync = PublishSynchronizer()
        tx.addBeforeCommitHook(pSync.beforeCompletionHook, [tx])
        tx.addAfterCommitHook(pSync.afterCompletionHook, [tx])
    return tx._synchronizedPublisher


_prepublishing_timer = None


def _getPrepublishingTimer():
    global _prepublishing_timer
    if not _prepublishing_timer:
        _prepublishing_timer = Metrology.timer("MessagePrePublishingEvents")
    return _prepublishing_timer


class PublishSynchronizer(object):
    _queuePublisher = None
    _postPublishingEventArgs = ()

    def findNonImpactingEvents(self, events):
        """
        Detect and return the event_uuid for each event that we don't actually
        want to send to the model change queue. Currently de-duplicating all
        ADD/REMOVE events is handled when calling publishAdd/publishRemove.
        """
        return []

    def correlateEvents(self, events):
        """
        In the case of moving objects we get only the latest add or remove
        event per device or component. Also we expect devices to have a
        "move" event associated.
        """
        eventsToRemove = self.findNonImpactingEvents(events)

        eventsToKeep = events
        if eventsToRemove:
            eventsToRemove = set(eventsToRemove)
            eventsToKeep = [
                event
                for event in events
                if event.event_uuid not in eventsToRemove
            ]

        # protobuf is odd about setting properties, so we have to make a new
        # event list and then copy the events we want into it
        queueSchema = getUtility(IQueueSchema)

        # batch events into manageable ModelEventList messages
        batchSize = 5000
        msgs = []
        count = 0
        returnMsg = queueSchema.getNewProtobuf("$ModelEventList")
        returnMsg.event_uuid = generate()
        msgs.append(returnMsg)
        for event in eventsToKeep:
            if count >= batchSize:
                log.debug(
                    "ModelEventList starting new batch after %s events", count
                )
                returnMsg = queueSchema.getNewProtobuf("$ModelEventList")
                returnMsg.event_uuid = generate()
                msgs.append(returnMsg)
                # reset counter
                count = 0
            newEvent = returnMsg.events.add()
            newEvent.CopyFrom(event)
            # not needed in the actual published event, just takes up space
            newEvent.ClearField("event_uuid")
            count += 1
        else:
            log.debug("ModelEventList batch size %s", count)
        return msgs

    @Metrology.utilization_timer(
        "zen.queuepublisher.beforeCompletionHookTimer"
    )
    def beforeCompletionHook(self, tx):
        try:
            log.debug("beforeCompletionHook on tx %s", tx)
            publisher = getattr(tx, "_synchronizedPublisher", None)
            if publisher:
                msgs = self.correlateEvents(publisher.events)
                self._postPublishingEventArgs = (publisher._events_ref,)
                with _getPrepublishingTimer():
                    notify(
                        MessagePrePublishingEvent(
                            msgs,
                            maintWindowChanges=publisher._maintWindowChanges,
                            refs=publisher._events_ref,
                        )
                    )
                if msgs:
                    self._queuePublisher = getUtility(
                        IQueuePublisher, "class"
                    )()
                    dataManager = AmqpDataManager(
                        self._queuePublisher.channel, tx._manager
                    )
                    tx.join(dataManager)
                    for msg in msgs:
                        self._queuePublisher.publish(
                            "$ModelChangeEvents",
                            "zenoss.event.modelchange",
                            msg,
                        )
            else:
                log.debug("no publisher found on tx %s", tx)
        finally:
            if hasattr(tx, "_synchronizedPublisher"):
                tx._synchronizedPublisher = None

    @Metrology.utilization_timer("zen.queuepublisher.afterCompletionHookTimer")
    def afterCompletionHook(self, status, tx):
        try:
            log.debug("afterCompletionHook status:%s for tx %s", status, tx)
            if self._queuePublisher:
                try:
                    self._queuePublisher.close()
                except Exception:
                    log.exception("Error closing queue publisher")
            if self._postPublishingEventArgs:
                notify(
                    MessagePostPublishingEvent(*self._postPublishingEventArgs)
                )
        finally:
            self._queuePublisher = None
            self._postPublishingEventArgs = ()


@implementer(IEventPublisher)
class EventPublisherBase(object):
    def _publish(
        self, exchange, routing_key, proto, mandatory=False, createQueues=None
    ):
        raise NotImplementedError

    def publish(self, event, mandatory=False):
        if not isinstance(event, Event):
            queueSchema = getUtility(IQueueSchema)
            if not hasattr(event, "evid"):
                event.evid = generate(1)
            # create the protobuf
            serializer = IProtobufSerializer(event)
            proto = queueSchema.getNewProtobuf("$Event")
            serializer.fill(proto)
            event = proto
        else:
            if not event.uuid:
                event.uuid = generate(1)

        # fill out the routing key
        eventClass = "/Unknown"
        if event.event_class:
            eventClass = event.event_class
        routing_key = (
            "zenoss.zenevent%s" % eventClass.replace("/", ".").lower()
        )
        log.debug(
            "About to publish this event to the raw event "
            "queue:%s, with this routing key: %s",
            event,
            routing_key,
        )
        try:
            self._publish(
                "$RawZenEvents", routing_key, event, mandatory=mandatory
            )
        except NoRouteException:
            # Queue hasn't been created yet. For this particular case, we don't
            # want to lose events by setting mandatory=False, so we'll create
            # the queue explicitly (but we don't want to pass it every time
            # because it could get expensive). See ZEN-3361.
            self._publish(
                "$RawZenEvents",
                routing_key,
                event,
                mandatory=mandatory,
                createQueues=("$RawZenEvents",),
            )

    def close(self):
        pass


class ClosingEventPublisher(EventPublisherBase):
    def _publish(
        self, exchange, routing_key, proto, mandatory=False, createQueues=None
    ):
        with closing(BlockingQueuePublisher()) as publisher:
            publisher.publish(
                exchange,
                routing_key,
                proto,
                mandatory=mandatory,
                createQueues=createQueues,
            )


class EventPublisher(EventPublisherBase):
    _publisher = None

    def _publish(
        self, exchange, routing_key, proto, mandatory=False, createQueues=None
    ):
        if EventPublisher._publisher is None:
            EventPublisher._publisher = BlockingQueuePublisher()
        EventPublisher._publisher.publish(
            exchange,
            routing_key,
            proto,
            mandatory=mandatory,
            createQueues=createQueues,
        )

    def close(self):
        if EventPublisher._publisher:
            EventPublisher._publisher.close()


class AsyncEventPublisher(EventPublisher):
    def _publish(self, exchange, routing_key, proto, mandatory=False):
        publisher = AsyncQueuePublisher()
        d = publisher.publish(
            exchange, routing_key, proto, mandatory=mandatory
        )
        d.addCallback(lambda r: publisher.close())


@implementer(IQueuePublisher)
class AsyncQueuePublisher(object):
    """
    Sends the protobuf to an exchange in a non-blocking manner
    """

    def __init__(self):
        self.reconnect()

    def reconnect(self):
        connectionInfo = getUtility(IAMQPConnectionInfo)
        queueSchema = getUtility(IQueueSchema)
        self._amqpClient = AMQPFactory(connectionInfo, queueSchema)

    @defer.inlineCallbacks
    def publish(
        self,
        exchange,
        routing_key,
        message,
        createQueues=None,
        mandatory=False,
        headers=None,
        declareExchange=True,
    ):
        if createQueues:
            for queue in createQueues:
                yield self._amqpClient.createQueue(queue)
        result = yield self._amqpClient.send(
            exchange,
            routing_key,
            message,
            mandatory=mandatory,
            headers=headers,
            declareExchange=declareExchange,
        )
        defer.returnValue(result)

    @property
    def channel(self):
        return self._amqpClient.channel

    def close(self):
        return self._amqpClient.shutdown()


@implementer(IQueuePublisher)
class BlockingQueuePublisher(object):
    """
    Class that is responsible for sending messages to the amqp exchange.
    """

    def __init__(self):
        self.reconnect()

    def reconnect(self):
        connectionInfo = getUtility(IAMQPConnectionInfo)
        queueSchema = getUtility(IQueueSchema)
        self._client = BlockingPublisher(connectionInfo, queueSchema)

    def publish(
        self,
        exchange,
        routing_key,
        message,
        createQueues=None,
        mandatory=False,
        headers=None,
        declareExchange=True,
    ):
        if createQueues:
            for queue in createQueues:
                if not self._client.queueExists(queue):
                    self.reconnect()
                    self._client.createQueue(queue)
        self._client.publish(
            exchange,
            routing_key,
            message,
            mandatory=mandatory,
            headers=headers,
            declareExchange=declareExchange,
        )

    @property
    def channel(self):
        return self._client.getChannel()

    def close(self):
        """
        Closes the channel and connection
        """
        self._client.close()


@implementer(IQueuePublisher)
class DummyQueuePublisher(object):
    """
    Class for the unit tests that ignores all messages
    """

    def publish(
        self,
        exchange,
        routing_key,
        message,
        createQueues=None,
        mandatory=False,
    ):
        pass

    @property
    def channel(self):
        return None

    def reconnect(self):
        pass

    def close(self):
        pass


@implementer(IEventPublisher)
class DummyEventPublisher(object):
    """
    Class for the unit tests that ignores all messages
    """

    def publish(self, event, mandatory=False):
        pass

    def close(self):
        pass
