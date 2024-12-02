##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zope.component import provideHandler
from zope.component.interfaces import ObjectEvent
from zope.interface import implementer
from zope.interface.advice import addClassAdvisor

from .interfaces import IUpdateEvent, IDeletionEvent

log = logging.getLogger("zen.ZenHub")


class InvalidationEvent(ObjectEvent):
    def __init__(self, object, oid):
        super(InvalidationEvent, self).__init__(object)
        self.oid = oid


@implementer(IUpdateEvent)
class UpdateEvent(InvalidationEvent):
    pass


@implementer(IDeletionEvent)
class DeletionEvent(InvalidationEvent):
    pass


def _listener_decorator_factory(eventtype):
    """
    Given a particular event interface, returns a decorator factory that may be
    used to create decorators for methods causing those methods, when bound, to
    be registered as object event subscribers.

    @param eventtype: The event interface to which the subscribers should
    listen.
    """

    def factory(*types):
        """
        The eventtype-specific decorator factory. Calling this factory both
        produces a decorator and wraps the __init__ of the class of the
        decorated method with a function that registers the handlers.
        """
        # Create a mutable to store the handler name between the call to
        # decorator and the call to advisor (simple assignment won't work for
        # scope reasons)
        _f = {}

        def decorator(f):
            """
            The decorator. All it does is print a log message, then call the
            original function.
            """

            def inner(self, obj, event):
                # Log that we've called this listener
                fname = ".".join((self.__class__.__name__, f.__name__))
                log.debug("%s is interested in %r for %r", fname, event, obj)

                # Call the original function
                return f(self, obj, event)

            # Push the name of the function outside the decorator scope so the
            # class advisor has access when it needs to register handlers.
            _f[f.__name__] = 1

            # Return the closure to replace the original function.
            return inner

        def advisor(cls):
            """
            A class advisor that is called after the class is created. We use
            this to wrap __init__ in a function that registers any handlers
            created via this factory, which are stored on the class.
            """
            # Set one flag per fname on the class so we don't double-register
            # when we override in a subclass (once for super, once for sub)
            fname = _f.keys()[0]
            cls.__registered = getattr(cls, "__registered", {})

            # Check our flag
            if fname not in cls.__registered or not issubclass(
                cls, tuple(cls.__registered[fname])
            ):
                # Decorator for __init__
                def registerHandlers(f):
                    def __init__(self, *args, **kwargs):
                        # Call the original constructor;
                        # we'll register handlers afterwards
                        f(self, *args, **kwargs)
                        handler = getattr(self, fname)
                        for t in types:
                            # Register the handler. Here's where we use
                            # eventtype, which was passed in to the outermost
                            # function in this behemoth.
                            provideHandler(handler, (t, eventtype))

                    # Return the closure to replace the decorated method
                    return __init__

                # Decorate __init__ so it will register the handlers on
                # instantiation
                cls.__init__ = registerHandlers(cls.__init__)
                # Set the flag for this fname
                cls.__registered.setdefault(fname, []).append(cls)

            # Return the class, which will replace the original class.
            return cls

        # Add the advisor to the class.
        addClassAdvisor(advisor)

        # Return the decorator so we get the log message when called
        return decorator

    return factory


# Create two decorator factories for the two kinds of events.
onUpdate = _listener_decorator_factory(IUpdateEvent)
onDelete = _listener_decorator_factory(IDeletionEvent)
