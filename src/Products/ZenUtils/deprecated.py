##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
import logging
import traceback
from decorator import decorator
from Products.ZenUtils.Utils import zenPath


class DeprecatedLogger(object):
    def __init__(self):
        self.loggedFunctions = set()
        self.config()

    def config(self, repeat=False, fileName='deprecated.log', delay=True, propagate=True):
        """
        Initialize or change the behavior of @deprecated.

        @param repeat: Log every time the same deprecated function is called, or just once?
        @type repeat: boolean
        @param fileName: Name of the file, or None for no file.
        @type fileName: string
        @param delay: Prevent creating the log file until used?
        @type delay: boolean
        @param propagate: Also log to current file/screen?
        @type propagate: boolean
        """
        self.log = logging.getLogger('zen.deprecated')
        # Remove the handler to start from scratch.
        if self.log.handlers:
            self.log.removeHandler(self.log.handlers[0])
        # New settings
        self.repeat = repeat
        self.log.propagate = propagate
        if fileName:
            filePath = zenPath('log', fileName)
            handler = logging.FileHandler(filePath, delay=delay)
            # 2011-11-02 17:44:43,674 WARNING zen.deprecated: ...
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
            handler.setFormatter(formatter)
            self.log.addHandler(handler)
        else:
            self.log.addHandler(logging.NullHandler())

    def logFunction(self, func):
        if self.repeat or not func in self.loggedFunctions:
            # 2011-11-02 17:51:52,314 WARNING zen.deprecated: Call to deprecated function audit
            # Source: /Users/philbowman/zen/home/Products/ZenMessaging/audit/__init__.py:57
            # Traceback: ...
            stack = ''.join(traceback.format_stack()[:-3])  # exclude this stuff
            self.log.warn(
                "Call to deprecated function %s\nSource: %s:%d\nTraceback:%s",
                func.__name__,
                func.func_code.co_filename,
                func.func_code.co_firstlineno + 1,
                stack)

        self.loggedFunctions.add(func)

    def __call__(self): return self     # these 2 lines make this a singleton
DeprecatedLogger = DeprecatedLogger()   # and initialize it on startup


@decorator
def deprecated(func, *args, **kwargs):
    """
    This can be used to mark functions as deprecated.
    If the function is used it will log a warning to the current
    log file and $ZENHOME/log/deprecated.log
    """
    if Globals.DevelopmentMode:   # Never show to customers.
        DeprecatedLogger.logFunction(func)

    return func(*args, **kwargs)
