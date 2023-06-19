##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import cgitb
from cStringIO import StringIO
from Products.ZenUtils.path import zenPath


_PATTERN = re.compile(
            r'(?P<message>.* contains the description of this error.)')

_LOG_DIR = zenPath('log', 'tracebacks')


def log_tb(exc_info):
    """log a detailed traceback to $ZENHOME/log/tracebacks. This traceback
    include the value of parameters in addition to the call stack."""
    file_ = StringIO()
    hook = cgitb.Hook(display=0, logdir=_LOG_DIR, file=file_, format='text')
    if not os.path.isdir(hook.logdir):
        os.makedirs(hook.logdir)
    hook.handle(exc_info)
    output = file_.getvalue()
    match = _PATTERN.search(output)
    return match.group('message')
    
