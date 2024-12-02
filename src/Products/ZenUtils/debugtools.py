##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import cProfile
import pstats
import tempfile
import os
import time

class Profiler(object):

    def __init__(self):
        self._stats = None

    @property
    def stats(self):
        return self._stats

    def print_stats(self, limit=20):
        if self._stats:
            self._stats.sort_stats('time', 'calls')
            self._stats.print_stats(limit)

    def runcall(self, func, *args, **kwargs):
        profile = cProfile.Profile()
        result = profile.runcall(func, *args, **kwargs)
        statsfile = tempfile.NamedTemporaryFile()
        try:
            profile.dump_stats(statsfile.name)
            self._stats = pstats.Stats(statsfile.name)
        finally:
            statsfile.close()
        return result


def profile(f):
    """
    Decorator that will profile a function and print stats.
    """
    def inner(*args, **kwargs):
        p = Profiler()
        result = p.runcall(f, *args, **kwargs)
        p.print_stats()
        return result
    return inner


def rpdb_set_trace(log=None):
    """
    convenience function to set_trace with rpdb in a control center container
    """
    import rpdb
    import subprocess

    ip=subprocess.check_output(["hostname", "-i"]).strip()
    port=4444
    print "connect to rpdb remotely with: nc %s %d  # Control-C to exit nc" % (ip, port)
    if log:
        log.warn("connect to rpdb remotely with: nc %s %d  # Control-C to exit nc", ip, port)
    debugger = rpdb.Rpdb(ip, port)
    debugger.set_trace()

class ContinuousProfiler(object):
    def __init__(self, process_identifier='', log=None):
        self.__profile = cProfile.Profile()
        self.__isRunning = False
        self.process_identifier=process_identifier
        self.log = log

    @property
    def isRunning(self):
        return self.__isRunning

    def start(self):
        if not self.__isRunning:
            self.__profile.enable()
            self.__isRunning = True
            if self.log:
                self.log.debug("Profiling started")

    def stop(self):
        if self.__isRunning:
            self.__profile.disable()
            self.__isRunning = False
            if self.log:
                self.log.debug("Profiling stopped")

    def dump_stats(self, filename=None, tmpdir=None):
        if filename is not None:
            stats_filename = filename
        else:
            datetime_stamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
            stats_filename = "{}-{}{}.pstats".format(datetime_stamp, os.getpid(), 
                                                     '-'+self.process_identifier if self.process_identifier else '')

        if tmpdir is not None:
            stats_filepath = os.path.join(tmpdir, stats_filename)
        else:
            stats_filepath = os.path.join(tempfile.gettempdir(), stats_filename)

        self.__profile.dump_stats(stats_filepath)
        if self.log:
            self.log.debug("pStats file created at %s", stats_filepath)
        return stats_filepath
