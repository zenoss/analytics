##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
from contextlib import contextmanager
from collections import defaultdict

from AccessControl import ClassSecurityInfo
from uuid import uuid1
from zope.interface import implements, Interface, Attribute
from zope.event import notify
from zope.component import getGlobalSiteManager
from zope.component import provideHandler
from ZODB.transact import transact

from Products.PluggableAuthService.interfaces.events import IUserLoggedInEvent
from Products.PluggableAuthService.interfaces.events import IUserLoggedOutEvent
from Products.PluggableAuthService.events import PASEvent
from Products.PluggableAuthService.plugins import (ZODBUserManager, ZODBGroupManager,
                                                   ZODBRoleManager)

GSM = getGlobalSiteManager()

class UserLoggedInEvent(PASEvent):
    """
    Login notification event.

    Subscribe to this to run code when a user logs in.
    The username can be obtained in the handler via: evt.object.id

    WARNING: Currently it doesn't notify when switching directly from
             a non-admin user to the admin user without logging out,
             because we're unable to determine whether the login succeeded.
    """
    implements(IUserLoggedInEvent)


class UserLoggedOutEvent(PASEvent):
    """
    Manual logout notification event.

    This does not fire for session timeouts.
    """
    implements(IUserLoggedOutEvent)

class IQuickstartWizardFinishedEvent(Interface):
    """
    Returns the Zope application.
    """
    app = Attribute("The Zope Application")

class QuickstartWizardFinishedEvent(object):
    implements(IQuickstartWizardFinishedEvent)

    def __init__(self, app):
        self.app = app

class IZopeApplicationOpenedEvent(Interface):
    """
    Returns the Zope application.
    """
    app = Attribute("The Zope Application")

class ZopeApplicationOpenedEvent(object):
    implements(IZopeApplicationOpenedEvent)

    def __init__(self, app):
        self.app = app

def notifyZopeApplicationOpenedSubscribers(event):
    """
    Re-fires the IDatabaseOpenedWithRoot notification to subscribers with an
    open handle to the application defined in the database.
    """
    db = event.database
    conn = db.open()
    try:
        app = conn.root()['Application']
        transact(notify)(ZopeApplicationOpenedEvent(app))
    finally:
        conn.close()

def registerUUID(event):
    """
    attempts to make sure that dmd.uuid is set to a non-empty value
    """
    try:
        if getattr(event.app.zport.dmd, "uuid", None) is None:
           event.app.zport.dmd.uuid = str(uuid1())
    except AttributeError:
        pass

def disablePasResources(event):
    """Disable access to users/groups/roles management PAS plugins from browser
    as they have no protection from CSRF attacks.
    """
    try:
        zport = getattr(event.app, 'zport', None)
        if not zport or getattr(zport.dmd, 'allowManageAccess', False):
            return
        for class_ in (ZODBUserManager.ZODBUserManager,
                       ZODBGroupManager.ZODBGroupManager,
                       ZODBRoleManager.ZODBRoleManager):
            security = ClassSecurityInfo()
            security.declareObjectPrivate()
            security.apply(class_)
    except AttributeError:
        pass

def teeHandler(handler, buffer=None):
    """
    All calls to C{handler} will also call C{buffer.append}.

    The buffer and any temporary handlers registered will be returned.
    """
    if buffer is None:
        buffer = []

    handlers = []

    for reg in GSM.registeredHandlers():
        if reg.handler == handler:
            required = reg.required
            
            def tempHandler(*args, **kwargs):
                buffer.append((args, kwargs))

            provideHandler(tempHandler, required)
            handlers.append((tempHandler, required))

    return buffer, handlers


def pauseHandler(handler, buffer=None):
    """
    First tee calls to C{handler} to C{buffer.append}, then unregister the
    original handler so only the buffer gets the events.

    The buffer and any temporary handlers registered will be returned.
    """
    buffer, temp_handlers = teeHandler(handler, buffer)

    for _, required in temp_handlers:
        GSM.unregisterHandler(handler, required=required)  

    return buffer, temp_handlers


def unteeHandler(temp_handlers=None):
    """
    Unregister any temporary handlers returned by L{teeHandler}.
    """
    if temp_handlers is not None:
        for temp_handler, required in temp_handlers:
            GSM.unregisterHandler(temp_handler, required=required)


def unpauseHandler(handler, buffer=None, temp_handlers=None):
    """
    First untee temporary handlers; then, reregister handlers paused by
    L{pauseHandler}. Finally, replay the buffered events through the original
    handler.
    """
    unteeHandler(temp_handlers)

    if temp_handlers is not None:
        for temp_handler, required in temp_handlers:
            provideHandler(handler, required)

    if buffer is not None:
        for args, kwargs in buffer:
            handler(*args, **kwargs)



@contextmanager
def paused(handler, buffer=None):
    """
    Pause this handler for the duration of the with block.

    WARNING: This is NOT safe to use in an async I/O environment if you
    yield to the event loop within the context manager!
    """
    buffer, temp_handlers = pauseHandler(handler, buffer)
    yield 
    unpauseHandler(handler, buffer, temp_handlers)


@contextmanager
def teed(handler, buffer=None):
    """
    Tee events destined for this handler for the duration of
    the with block.

    WARNING: This is NOT safe to use in an async I/O environment if you
    yield to the event loop within the context manager!
    """
    buffer, temp_handlers = teeHandler(handler, buffer)
    yield
    unteeHandler(temp_handlers)
     

class OptimizedIndexingBuffer(object):
    """
    Accumulates and dedupes IndexingEvents so that only one will eventually be
    fired per object.
    """
    def __init__(self):
        self.indexes = defaultdict(set)
        self.update_metadatas = {}
        self.args = {}
        from Products.Zuul.catalog.events import IndexingEvent
        from OFS.event import ObjectWillBeRemovedEvent
        self.IndexingEvent = IndexingEvent
        self.ObjectWillBeRemovedEvent = ObjectWillBeRemovedEvent
    
    def append(self, (args, kwargs)):
        ob, event = args
        if isinstance(event, self.ObjectWillBeRemovedEvent):
            # Removal event; just delete pending indexing requests,
            # since they would be invalid. Removal will then continue.
            self.indexes.pop(ob, None)
            self.update_metadatas.pop(ob, None)
        elif isinstance(event, self.IndexingEvent):
            # If indexes are specified, we have decisions to make
            if event.idxs:
                idxs = ((event.idxs,) if isinstance(event.idxs, basestring) 
                        else event.idxs)
                # Have we seen the ob already? If not, add the indexes
                # If we have seen it already, only update if the set isn't 
                # empty, which signifies all indexes (thereby encompassing
                # those specified in the event)
                if ob not in self.indexes or self.indexes[ob]:
                    self.indexes[ob].update(idxs)
            else:
                # Replace whatever's there with an empty set
                self.indexes[ob] = set()

            # Update metadata if any event says to do so
            self.update_metadatas[ob] = (self.update_metadatas.get(ob, False) 
                                         or event.update_metadata)

    def __iter__(self):
        for ob, idxs in self.indexes.iteritems():
            yield ((ob, self.IndexingEvent(ob, list(self.indexes.get(ob, [])), 
                        self.update_metadatas.get(ob, False))), {})


@contextmanager
def pausedAndOptimizedIndexing(index_handler=None, unindex_handler=None):
    """
    Delay global catalog indexing for the duration of the with block. Also,
    collapse indexing events so that only one is fired per object.

    Uncataloging will not be paused, since it must happen immediately before
    the object being uncataloged disappears or is moved.

    WARNING: This is NOT safe to use in an async I/O environment if you
    yield to the event loop within the context manager!
    """
    # Circular import
    from Products.Zuul.catalog.events import onIndexingEvent
    index_handler = index_handler or onIndexingEvent

    # Circular import
    from Products.Zuul.catalog.events import onObjectRemoved
    unindex_handler = unindex_handler or onObjectRemoved

    index_buffer = OptimizedIndexingBuffer()
    with paused(index_handler, index_buffer):
        with teed(unindex_handler, index_buffer):
            yield

