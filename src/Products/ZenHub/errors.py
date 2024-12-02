import traceback

from twisted.spread import pb
from ZODB.POSException import ConflictError


class RemoteException(pb.Error, pb.Copyable, pb.RemoteCopy):
    """Exception that can cross the PB barrier"""

    def __init__(self, msg, tb):
        super(RemoteException, self).__init__(msg)
        self.traceback = tb

    def getStateToCopy(self):
        return {
            "args": tuple(self.args),
            "traceback": self.traceback,
        }

    def setCopyableState(self, state):
        self.args = state["args"]
        self.traceback = state["traceback"]

    def __str__(self):
        return "%s:%s" % (
            super(RemoteException, self).__str__(),
            ("\n" + self.traceback) if self.traceback else " <no traceback>",
        )


pb.setUnjellyableForClass(RemoteException, RemoteException)


# ZODB conflicts
class RemoteConflictError(RemoteException):
    pass


pb.setUnjellyableForClass(RemoteConflictError, RemoteConflictError)


# Invalid monitor specified
class RemoteBadMonitor(RemoteException):
    pass


pb.setUnjellyableForClass(RemoteBadMonitor, RemoteBadMonitor)


class HubDown(Exception):
    """Raised when a connection to ZenHub is required but not available."""

    def __init__(self, mesg="ZenHub is down"):
        super(HubDown, self).__init__(mesg)


def translateError(callable):
    """
    Decorator function to wrap remote exceptions into something
    understandable by our daemon.

    @parameter callable: function to wrap
    @type callable: function
    @return: function's return or an exception
    @rtype: various
    """

    def inner(*args, **kw):
        """
        Interior decorator
        """
        try:
            return callable(*args, **kw)
        except ConflictError as ex:
            raise RemoteConflictError(
                "Remote exception: %s: %s" % (ex.__class__, ex),
                traceback.format_exc(),
            )
        except Exception as ex:
            raise RemoteException(
                "Remote exception: %s: %s" % (ex.__class__, ex),
                traceback.format_exc(),
            )

    return inner
