##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from collections import deque
from twisted.internet import reactor, defer, error
from twisted.internet.protocol import ProcessProtocol
from twisted.python import failure
import time
import logging

log = logging.getLogger("zen.processqueue")


class QueueStopped(Exception):
    pass

class ProcessQueue(object):
    """
    Ansynchronously run processes.  Processes are queued up and run in a FIFO 
    order. Processes are run in concurrently up to the configured amount.  
    """
    
    def __init__(self, parallel=10):
        """
        initialize the process queue; process in queue will not executed until
        start is called.
        @param parallel: number of process to run concurrently
        @type parallel: int
        """
        self._parallel=parallel
        self._processes=deque()
        self._started=False
        self._num_running=0

        self._maxQtime = 0
        self._maxExecTime = 0
        self._stopped=None
        
    def queueProcess(self, executable, args=(), env={}, path=None, uid=None, 
                   gid=None, usePTY=0, childFDs=None, processProtocol=None, 
                   timeout=60, timeout_callback=None):
        """
        add a process to the queue. args are similar to reactor.spawnProcess
        @param processProtocol: optional protocol to control the process
        @type processProtocol:  ProcessProtocol from twisted 
        @param timeout: how many seconds to let the process execute
        @type timeout: int 
        @param timeout_callback: callable to call if the process times out
        @type timeout_callback: callable w/ one arg
        @raise QueueStopped: if the queue has been stopped 
        """
        if self._stopped:
            raise QueueStopped()
        processQProtocol = None
        if processProtocol:
            processQProtocol = _ProcessQueueProtocolDecorator(processProtocol, 
                                                             executable, args, 
                                                             env, path, uid, 
                                                             gid, usePTY, 
                                                             childFDs,timeout,
                                                             timeout_callback)
        else:
            processQProtocol = _ProcessQueueProtocol(executable, args, 
                                                    env, path, uid, 
                                                    gid, usePTY, 
                                                    childFDs,timeout,
                                                    timeout_callback)
        log.debug("Adding process %s to queue", processQProtocol)
        log.debug("Processes in queue: %s", len(self._processes))
        
        self._processes.append(processQProtocol)
        
        if self._started:
            self._processQueue()

    def stop(self):
        """
        stops the process queue; no more processes will be accepted. deferred
        will be called back when process queue is empty
        """
        if self._stopped: return self._stopped
        self._stopped = defer.Deferred()
        if self._num_running ==0 and len(self._processes) == 0:
            self._stopped.callback("process queue is empty and stopped")
        return self._stopped
    
    def start(self):
        """
        start processing the queue. Processes will only be executed when the 
        reactor starts
        """
        def _doStart():
            # don't want to actually start unless reactor is running to prevent
            #zombie processes
            if not self._started:
                self._started=True
                self._processQueue()
        
        reactor.callLater(0,_doStart)
            
    def _processQueue(self):
        def processFinished(value, processProtocol):
            self._num_running -= 1
            reactor.callLater(0, self._processQueue)
            
            execTime =  processProtocol.execStopTime - processProtocol.execStartTime
            qTime = processProtocol.queueStopTime - processProtocol.queueStartTime
            self._maxQtime = max(self._maxQtime, qTime)
            self._maxExecTime = max(self._maxExecTime, execTime)
            log.debug("execution time %s seconds; queue time %s seconds; "
                      "process %s",
                      execTime, qTime, processProtocol)
            if (self._num_running == 0 
                and self._stopped 
                and not self._stopped.called 
                and len(self._processes) == 0):
                self._stopped.callback("process queue is empty and stopped")
        log.debug("Number of process being executed: %s", self._num_running)
        if self._num_running < self._parallel:
            processQProtocol = None
            if self._processes:
                processQProtocol = self._processes.popleft()
            if processQProtocol:
                self._num_running += 1
                d = processQProtocol.start()
                d.addBoth(processFinished, processQProtocol)
        
        if self._processes and self._num_running < self._parallel:
            reactor.callLater(0, self._processQueue)
        return

class _ProcessQueueProtocol(ProcessProtocol):
    """
    For interal use by ProcessQueue
    Protocol to run processes in ProcessQueue. Controls life cycle or process 
    including timing out long running processes
    """

    def __init__(self, executable, args=(), env={}, path=None,
                 uid=None, gid=None, usePTY=0, childFDs=None, timeout=60,
                 timeout_callback=None):
        self._executable=executable
        self._args=args
        self._env=env
        self._path=path
        self._uid=uid
        self._gid=gid
        self._usePTY=usePTY
        self._childFDs=childFDs
        self._time_out=timeout
        self._timeoutDeferred=None
        self._timeout_callback=timeout_callback
        self.queueStartTime = time.time()
        self.queueStopTime = None
        self.execStartTime = None
        self.execStopTime = None

    def __str__(self):
        if self._args:
            return "process %s" % " ".join([x or 'None' for x in self._args])
        else:
            return "process %s" % self._executable 

    def start(self):
        log.debug("spawning %s ", self)
        now = time.time()
        self.queueStopTime = now
        self.execStartTime = now
        reactor.spawnProcess(self, self._executable, self._args,
                             self._env, self._path, self._uid, self._gid,
                             self._usePTY, self._childFDs)
        self._timeoutDeferred = createTimeout(defer.Deferred(), self._time_out, self)
        self._timeoutDeferred.addErrback(self._timedOut)
        if self._timeout_callback:
            self._timeoutDeferred.addErrback(self._timeout_callback)
        return self._timeoutDeferred
    
    def _timedOut(self, value):
        "Kill a process if it takes too long"
        try:
            if not self.execStopTime:
                self.execStopTime = time.time()

            self.transport.signalProcess('KILL')
            log.warning("timed out after %s seconds: %s", self._time_out, self)
        except error.ProcessExitedAlready:
            log.debug("Process already exited: %s", self)
        return value
    
    def processEnded(self, reason):
        """
        This will be called when the subprocess is finished.

        @type reason: L{twisted.python.failure.Failure}
        """
        if not self.execStopTime:
            self.execStopTime = time.time()

        deferred = self._timeoutDeferred
        self._timeoutDeferred = None
        if deferred and not deferred.called:
            msg = reason.getErrorMessage()
            exitCode = reason.value.exitCode
            deferred.callback((exitCode,msg))
            


class _ProcessQueueProtocolDecorator(_ProcessQueueProtocol):
    """
    For interal use by ProcessQueue
    Wraps an existing ProcessProtocol so that it can be run in a ProcessQueue
    """
    def __init__(self, protocol, executable, args=(), env={}, path=None,
                 uid=None, gid=None, usePTY=0, childFDs=None, timeout=60,
                 timeout_callback=None):
        _ProcessQueueProtocol.__init__(self, executable, args, env, path, uid, 
                                      gid, usePTY, childFDs, timeout, 
                                      timeout_callback)
        self._protocol = protocol

    def connectionMade(self):
        self._protocol.connectionMade()

    def makeConnection(self, transport):
        self._protocol.transport = transport
        _ProcessQueueProtocol.makeConnection(self, transport)

    def outReceived(self, data):
        """
        Some data was received from stdout.
        """
        self._protocol.outReceived(data)

    def errReceived(self, data):
        """
        Some data was received from stderr.
        """
        self._protocol.errReceived(data)

    def inConnectionLost(self):
        """
        This will be called when stdin is closed.
        """
        self._protocol.inConnectionLost()

    def outConnectionLost(self):
        """
        This will be called when stdout is closed.
        """
        self._protocol.outConnectionLost()


    def errConnectionLost(self):
        """
        This will be called when stderr is closed.
        """
        self._protocol.errConnectionLost()

    def processEnded(self, reason):
        """
        This will be called when the subprocess is finished.

        @type reason: L{twisted.python.failure.Failure}
        """
        _ProcessQueueProtocol.processEnded(self, reason)
        self._protocol.processEnded(reason)

class TimeoutError(Exception):
    """
    Error for a defered call taking too long to complete
    """

    def __init__(self, *args):
        Exception.__init__(self)
        self.args = args

def createTimeout(deferred, seconds, obj):
    """
    Cause an error on a deferred when it is taking too long to complete. 
    @param deferred: deferred to monitor for callback/errback
    @type deferred: Deferred
    @param seconds: Time to wait for a callback/errback on the deferred
    @type seconds: int
    @pram obj: context for the TimeoutError when timeout occurs
    @type obj: anything
    """

    def _timeout(deferred, obj):
        "took too long... call an errback"
        deferred.errback(failure.Failure(TimeoutError(obj)))

    def _cb(arg, timer):
        "the process finished, possibly by timing out"
        if not timer.called:
            timer.cancel()
        return arg

    timer = reactor.callLater(seconds, _timeout, deferred, obj)
    deferred.addBoth(_cb, timer)
    return deferred
