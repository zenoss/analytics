##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import inspect
import logging

from zenoss.protocols.eventlet.amqp import Publishable
from zenoss.protocols.jsonformat import to_dict

from Products.ZenEvents.events2.processing import (
    DropEvent,
    ProcessingException,
)

log = logging.getLogger("zen.AmqpPubSub")


class BasePubSubMessageTask(object):
    """
    Base for other eventlet-using queue consumers.

    Subclasses should implement the processMessage method, which can yield or
    return a tuple of (exchange, routing_key, protobuf) in order to publish its
    own messages.
    """

    def __call__(self, message, proto):
        try:
            result = self.processMessage(proto)

            if result:
                if not inspect.isgenerator(result):
                    result = (result,)

                for msg in result:
                    if isinstance(msg, Publishable):
                        yield msg
                    else:
                        exchange, routing_key, msg = result
                        yield Publishable(
                            msg, exchange=exchange, routingKey=routing_key
                        )

            message.ack()

        except DropEvent as e:
            if log.isEnabledFor(logging.DEBUG):
                log.debug("%s - %s", e.message, to_dict(e.event))
            message.ack()

        except ProcessingException as e:
            log.error("%s - %s", e.message, to_dict(e.event))
            log.exception(e)
            message.reject()

        except Exception as e:
            log.exception(e)
            message.reject()

    def processMessage(self, protobuf):
        raise NotImplementedError
