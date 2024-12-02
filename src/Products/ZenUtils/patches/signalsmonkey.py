##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

"""
This module patches Signals.SignalHandler to pass the signum and frame to its
registered handlers if (and only if) the handler accepts arguments.
"""
# This is a little tricky for two reasons:
# (1) SignalHandler is a singleton. Its class definition had the same name.
# (2) The singleton's registerHandler() method may have already been called,
#     and/or may be called later.

import sys
import signal
import inspect
from Signals.SignalHandler import LOG
from Signals.SignalHandler import get_signal_name
from Signals.SignalHandler import SignalHandler as OriginalSignalHandler

def improvedSignalHandler(signum, frame):
    """Improved signal handler that dispatches to registered handlers."""
    signame = get_signal_name(signum)
    LOG.info("Caught signal %s" % signame)

    for handler in OriginalSignalHandler.registry.get(signum, []):
        # Never let a bad handler prevent the standard signal
        # handlers from running.
        try:
            if inspect.getargspec(handler).args:
                handler(signum, frame)
            else:
                handler()
        except Exception:
            LOG.warn('A handler for %s failed!' % signame,
                     exc_info=sys.exc_info())

def upgradeHandler(signum):
    signal.signal(signum, improvedSignalHandler)
    signame = get_signal_name(signum)
    LOG.debug("Upgraded sighandler for %s", signame)

originalRegisterHandler = OriginalSignalHandler.registerHandler
def improvedRegisterHandler(signum, handler):
    wasnt_installed = (signum not in OriginalSignalHandler.registry)
    originalRegisterHandler(signum, handler)
    if wasnt_installed and (signum in OriginalSignalHandler.registry):
        upgradeHandler(signum)

OriginalSignalHandler.registerHandler = improvedRegisterHandler
for signum in OriginalSignalHandler.registry:
    upgradeHandler(signum)

