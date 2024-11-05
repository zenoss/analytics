#! /usr/bin/env python 
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''watchdog for zenoss daemons

Run a program that is expected to run forever.  If the program stops,
restart it.

'''

from Products.ZenUtils.path import zenPath
import logging

import socket as s
import os, sys, time, signal, select

class TimeoutError(Exception): pass
class UnexpectedFailure(Exception): pass

log = logging.getLogger('watchdog')    

# time to spend waiting around for a child to die after we kill it
DEATH_WATCH_TIME = 10

# time to wait between tests of a childs imminent death
BUSY_WAIT_SLEEP = 0.5

def _sleep(secs):
    "Sleep, but don't raise an exception if interrupted"
    try:
        time.sleep(secs)
    except Exception:
        pass

class ExitStatus:
    "Model a child's exit status"
    def __init__(self, status):
        self.status = status

    def __str__(self):
        if self.signaled():
            return 'Killed with signal %d' % self.signal()
        return 'Exited with code %d' % self.exitCode()

    def __repr__(self):
        return '<ExitStatus %d (%s)>' % (self.status, self)

    def signaled(self):
        return os.WIFSIGNALED(self.status)

    def exitCode(self):
        if self.signaled():
            raise ValueError(str(self))
        return os.WEXITSTATUS(self.status)

    def signal(self):
        if not self.signaled():
            raise ValueError(str(self))
        return os.WTERMSIG(self.status)
        

class Watcher:
    """Run the given command, and expect periodic input on a shared
    UNIX-domain socket.  If the command does not connect to the socket
    in startTimeout seconds, or it does not report every cycleTimeout
    seconds, then the process is restarted.  The Watchdog will
    increase the time-between restarts until maxTime is achieved"""

    def __init__(self,
                 socketPath,
                 cmd,
                 startTimeout = None,
                 cycleTimeout = 1,
                 maxTime = 30):
        if startTimeout == None:
            startTimeout = 120
        self.socketPath = socketPath
        self.cmd = cmd
        self.startTimeout = startTimeout
        self.cycleTimeout = cycleTimeout
        self.maxTime = maxTime
        self.stop = False
        self.childPid = -1

    def _kill(self):
        """Send a signal to a process and wait for it to stop.  Use
        progressively more serious signals to get it to stop.
        """
        if self.childPid <= 0:
            return
        signals = signal.SIGINT, signal.SIGTERM, signal.SIGKILL
        for sig in signals:
            log.debug("Killing %d with %d", self.childPid, sig)
            os.kill(self.childPid, sig)
            stopTime = time.time() + DEATH_WATCH_TIME / len(signals)
            while time.time() < stopTime:
                try:
                    pid, status = os.waitpid(self.childPid, os.WNOHANG)
                    if pid:
                        return ExitStatus(status)
                except os.error:
                    pass
                _sleep(BUSY_WAIT_SLEEP)

    def _readWait(self, sock, timeout):
        "Wait for a file descriptor to become readable"
        endTime = time.time() + timeout
        # Loop because signals can cause select stop early
        while not self.stop and time.time() < endTime:
            diff = endTime - time.time()
            try:
                log.debug("waiting %f seconds", diff)
                rd, wr, ex = select.select([sock], [], [], diff)
            except Exception:
                continue
            if rd:
                return sock
        return None

    def _runOnce(self):
        try:
            if os.path.exists(self.socketPath):
                os.unlink(self.socketPath)
        except OSError:
            log.exception("Problem removing old socket %s", self.socketPath)
        cmd = self.cmd + ['--watchdogPath', self.socketPath]
        cmd.insert(0, sys.executable)
        sock = s.socket(s.AF_UNIX, s.SOCK_STREAM)
        sock.bind(self.socketPath)
        self.childPid = os.fork()
        if self.childPid < 0:
            log.error("Unable to fork")
            return
        if self.childPid == 0:
            # child
            try:
                log.debug('Running %r', cmd)
                os.execlp(cmd[0], *cmd)
            except Exception:
                log.exception("Exec failed!")
                sys.exit(0)
        try:
            sock.setblocking(False)
            sock.listen(1)
            if not self._readWait(sock, self.startTimeout):
                if not self.stop:
                    raise TimeoutError("getting initial connection from process")
            log.debug('Waiting for command to connect %r', cmd)
            conn, addr = sock.accept()
            conn.setblocking(False)
            try:
                buf = ''
                while not self.stop:
                    # get input from the child
                    if not self._readWait(conn, self.cycleTimeout * 2):
                        if not self.stop:
                            raise TimeoutError("getting status from process")
                    try:
                        bytes = conn.recv(1024)
                    except Exception:
                        continue
                    if bytes == '':          # EOF
                        pid, status = os.waitpid(self.childPid, os.WNOHANG)
                        if pid == self.childPid:
                            status = ExitStatus(status)
                            self.childPid = -1
                            if status.signaled():
                                raise UnexpectedFailure(status)
                            if status.exitCode() != 0:
                                log.error("Child exited with status %d", status.exitCode())
                                raise UnexpectedFailure(status)
                            return
                        else:
                            _sleep(0.1)
                            continue
                    # interpret the data as an updated cycleTime
                    buf += bytes
                    lines = buf.split('\n')
                    if lines:
                        buf = lines[-1]
                        line = lines[0]
                        if line:
                            log.debug("Child sent %s", line)
                            try:
                                self.cycleTimeout = max(int(line), 1)
                                log.debug("Watchdog cycleTimeout is %d",
                                          self.cycleTimeout)
                            except ValueError:
                                log.exception("Unable to convert cycleTime")
            finally:
                conn.close()
        finally:
            os.unlink(self.socketPath)
            self._kill()

    def _stop(self, *unused):
        self.stop = True

    def run(self):
        sleepTime = 1
        signal.signal(signal.SIGINT, self._stop)
        while not self.stop:
            try:
                self._runOnce()
                return
            except TimeoutError as ex:
                log.error("Timeout: %s", ex.args)
            except UnexpectedFailure as ex:
                status = ex.args[0]
                log.error("Child died: %s", status)
            except Exception as ex:
                log.exception(ex)
            if not self.stop:
                log.debug("Waiting %.2f seconds before restarting", sleepTime)
                _sleep(sleepTime)
                prog = self.cmd[0].split('/')[-1].split('.')[0]
                log.error("Restarting %s", prog)
            sleepTime = min(1.5 * sleepTime, self.maxTime)

class Reporter:
    def __init__(self, path):
        self.sock = s.socket(s.AF_UNIX, s.SOCK_STREAM)
        self.sock.connect(path)
        self.sock.setblocking(False)

    def niceDoggie(self, cycleTime):
        cycleTime = max(1, int(cycleTime))
        try:
            try:
                self.sock.recv(1)
                log.error("Received input on report socket: probably EOF")
                sys.exit(1)
            except Exception:
                pass
            self.sock.send('%d\n' % cycleTime)
        except Exception:
            log.exception("Unable to report to the watchdog.")
            sys.exit(1)

    def close(self):
        self.sock.close()

def main():
    '''Little test for the Watchdog.
    Usage:
          python Watchdog.py -- python Watchdog.py -e 1

    This will repeatedly run a child that exits with exit code 1.
    The child does periodic reports over the watchdog socket.
    '''
    import getopt
    global log
    opts, cmd = getopt.getopt(sys.argv[1:], 'p:m:d:e:c:', 'watchdogPath=')
    socketPath = 'watchdog.%d' % os.getpid()
    maxTime = 30
    cycleTime = 1
    level = 20
    child = None
    exitCode = 0
    for opt, arg in opts:
        if opt == '-p':
            socketPath = arg
        if opt == '-e':
            exitCode = int(arg)
        if opt == '-m':
            maxTime = float(arg)
        if opt == '-d':
            level = int(arg)
        if opt == '-c':
            cycleTime = int(arg)
        if opt == '--watchdogPath':
            socketPath = arg
            child = True
    if not child:
        socketPath = zenPath('var', socketPath)

    logging.basicConfig(level=level)
    log = logging.getLogger('watchdog')

    if child:
        r = Reporter(socketPath)
        print 'Connected'
        for i in range(3):
            time.sleep(1)
            r.niceDoggie(1)
            sys.stdout.write('*')
            sys.stdout.flush()
        time.sleep(2)
        r.close()
        print 'Closed'
        sys.exit(exitCode)
    else:
        w = Watcher(socketPath, cmd, cycleTimeout=cycleTime, maxTime=maxTime)
        w.run()

if __name__ == '__main__':
    main()

__all__ = ['Watcher', 'Reporter']
