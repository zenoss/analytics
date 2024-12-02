##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Interface, Attribute


class IQueuePublisher(Interface):
    """
    Interface for publishing to a queue
    """

    def publish(
        exchange,
        routing_key,
        message,
        createQueues=None,
        mandatory=False,
        headers=None,
        declareExchange=True,
    ):
        """
        Publishes a message to an exchange. If twisted is running
        this will use the twisted amqp library, otherwise it will
        be blocking.
        @type  exchange: string
        @param exchange: destination exchange for the amqp server
        @type  routing_key: string
        @param routing_key: Key by which consumers will setup the
            queues to route.
        @type  message: string or Protobuf
        @param message: message we are sending in the queue
        @type  createQueues: list
        @param createQueues: The name of the queues defined in the queue
            schema to create prior to publishing the message.
        @type  mandatory: Boolean.
        @param mandatory: If true, will raise NoRouteException if there is no
            destination queue for the published event.
        @type  headers: dict
        @param headers: Headers to use when publishing a message (Useful for
            headers exchanges).
        @type  declareExchange: Boolean.
        @param declareExchange: Whether to declare the exchange when
            publishing the message.
        @raise zenoss.protocols.exceptions.NoRouteException: If mandatory is
            True and the message cannot be sent to a queue (the message is
            lost).
        """

    channel = Attribute("Retrieves the connection to the queue")


class IProtobufSerializer(Interface):
    """
    Interfaces for converting a Zope object to a protobuf.
    """

    def fill(protobuf):
        """
        This takes a protobuf and applies the properties from our zope object.
        @type  protobuf: Protobuf Message Object
        @param protobuf: The object we are populating
        @rtype:   protobuf
        @return:  The same protobuf passed in but with its properties set
        """


class IModelProtobufSerializer(IProtobufSerializer):
    """
    Interfaces for converting a Zenoss model object to a Model protobuf.
    """

    modelType = Attribute("the model type for the object")


class IQueueConsumerTask(Interface):
    """
    A Task that is called once for every message that comes from the Queue.

    It is up to the task to acknowledge that message.
    """

    queueConsumer = Attribute(
        "The consumer this task is proceessing a message for"
    )
    queue = Attribute("The queue this queue will consume from.")

    def processMessage(message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """


class IEventPublisher(Interface):
    """
    Publishes events.
    """

    def publish(event, mandatory=False):
        """
        Publish event to the raw event queue.

        @type  event: Products.ZenEvents.Event
        @param event: The event to be published to the queue.
        @type  mandatory: Boolean.
        @param mandatory: If true, will raise NoRouteException if there is no
                          destination queue for the published event.
        @raise zenoss.protocols.exceptions.NoRouteException: If mandatory is
               True and the message cannot be sent to a queue (the message is
               lost).
        """

    def close():
        """
        Closes the event publisher.
        """
