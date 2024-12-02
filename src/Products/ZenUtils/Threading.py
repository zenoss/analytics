##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import ctypes
import inspect
import Queue
import threading

# ==========================
# NOTE
# The thread interrupt code found here is a modified version of Bluebird75's
# solution found at:
# http://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python
# ==========================


class ThreadInterrupt(BaseException):
    """Raised when a thread is interrupted."""


class InterruptableThread(threading.Thread):
    """A thread class that supports interruption.

    Target functions should catch ThreadInterrupt to perform cleanup.
    """

    def __init__(self, *args, **kw):
        self.__interrupted = False
        super(InterruptableThread, self).__init__(*args, **kw)

    def interrupt(self, exception_type=ThreadInterrupt):
        if self.__interrupted:
            return
        inject_exception_into_thread(self.ident, exception_type)
        self.__interrupted = True

    def kill(self):
        self.interrupt(SystemExit)


def inject_exception_into_thread(tid, exception):
    """Inject an exception into the given thread context.

    :param int tid: A thread ID
    :param BaseException exception: The exception class to inject.
    """
    if not inspect.isclass(exception):
        raise TypeError("Can't raise exception instances into a thread")
    if not issubclass(exception, BaseException):
        raise TypeError("Not a subclass of Exception")
    threadid = ctypes.c_long(tid)
    exception = ctypes.py_object(exception)
    rc = ctypes.pythonapi.PyThreadState_SetAsyncExc(threadid, exception)
    if rc == 0:
        raise ValueError("Invalid thread ID: {}".format(tid))
    elif rc != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(threadid, None)
        raise SystemError("Failed to interrupt thread")


class LineReader(threading.Thread):
    """Simulate non-blocking readline() behavior."""

    daemon = True

    def __init__(self, stream):
        """Initialize a LineReader instance.

        :param stream: input data stream.
        :type stream: A file-like object.
        """
        super(LineReader, self).__init__()
        self._stream = stream
        self._queue = Queue.Queue()

    def run(self):
        for line in iter(self._stream.readline, b''):
            self._queue.put(line)
        self._stream.close()
        self._stream = None

    def readline(self, timeout=0):
        try:
            return self._queue.get(timeout=timeout)
        except Queue.Empty:
            return ''
