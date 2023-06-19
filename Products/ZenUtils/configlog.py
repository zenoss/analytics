##############################################################################
# 
# Portions copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
#
# Portions copyright (C) Vinay Sajip. 2001-2011, all rights reserved.
# 
# Permission to use, copy, modify, and distribute configlog and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation, and that the name of Vinay Sajip
# not be used in advertising or publicity pertaining to distribution
# of the software without specific, written prior permission.
# VINAY SAJIP DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING
# ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# VINAY SAJIP BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR
# ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
# IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# 
##############################################################################


"""Creates new loggers from a python logging configuration file."""

import os
import logging
import logging.config
from logging import FileHandler
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler

from .path import zenPath

log = logging.getLogger("zen.configlog")


def _relativeToLogPath(filename):
    """Returns the filename relative to ZENHOME/log/"""
    if filename.startswith('/'):
        return filename
    return zenPath('log', filename)


class ZenFileHandler(FileHandler):
    """Like python's FileHandler but relative to ZENHOME/log/"""
    def __init__(self, filename, mode='a', encoding=None, delay=0):
        filename = _relativeToLogPath(filename)
        FileHandler.__init__(self, filename, mode, encoding, delay)


class ZenRotatingFileHandler(RotatingFileHandler):
    """Like python's RotatingFileHandler but relative to ZENHOME/log/"""
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=0):
        filename = _relativeToLogPath(filename)
        RotatingFileHandler.__init__(self, filename, mode, maxBytes, backupCount, encoding, delay)
try:
    from cloghandler import ConcurrentRotatingFileHandler as ParentHandler
except ImportError:
    from warnings import warn
    warn("ConcurrentLogHandler package not installed. Using RotatingFileLogHandler. While everything will still work fine, there is a potential for log files overlapping each other.")
    from logging.handlers import RotatingFileHandler as ParentHandler
class ZenConcurrentRotatingFileHandler(ParentHandler):
    """Like python's RotatingFileHandler but relative to ZENHOME/log/"""
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=0):
        filename = _relativeToLogPath(filename)
        ParentHandler.__init__(self, filename, mode, maxBytes, backupCount, encoding, delay)

class ZenTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Like python's TimedFileHandler but relative to ZENHOME/log/"""
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False):
        filename = _relativeToLogPath(filename)
        TimedRotatingFileHandler.__init__(self, filename, when, interval, backupCount, encoding, delay, utc)


def addLogsFromConfigFile(fname, configDefaults=None):
    """
    Add new loggers, handlers, and fomatters from a file.
    Returns whether the file successfully loaded.

    The file should be in the standard Python log config format described here:
    http://docs.python.org/library/logging.config.html#configuration-file-format

    This code was copied from the Python 2.7 logging.config.fileConfig()
    method, then altered to not require root or wipe existing loggers.
    Unfortunately the standard option "disable_existing_loggers=False" would
    still wipe out their settings and replace root, undoing Zope's log config.
    """
    if not os.path.exists(fname):
        log.debug('Log configuration file not found: %s', fname)
        return False

    import ConfigParser

    try:
        cp = ConfigParser.ConfigParser(configDefaults)
        if hasattr(fname, 'readline'):
            cp.readfp(fname)
        else:
            cp.read(fname)

        formatters = logging.config._create_formatters(cp)
    except Exception:
        log.exception('Problem loading log configuration file: %s', fname)
        return False

    try:
        logging._acquireLock()
        # Handlers add themselves to logging._handlers
        handlers = logging.config._install_handlers(cp, formatters)
        _zen_install_loggers(cp, handlers)
        return True
    except Exception:
        log.exception('Problem loading log configuration file: %s', fname)
        return False
    finally:
        logging._releaseLock()


def _zen_install_loggers(cp, handlers):
    """Create and install loggers, without wiping existing ones."""

    llist = cp.get("loggers", "keys")
    llist = [log.strip() for log in llist.split(",")]
    if 'root' in llist:
        raise Exception('Zenoss logger config files should not have a root logger.')

    #now set up the new ones...
    existing_logger_names = logging.root.manager.loggerDict.keys()
    for log in llist:
        sectname = "logger_%s" % log
        qn = cp.get(sectname, "qualname")
        opts = cp.options(sectname)
        if "propagate" in opts:
            propagate = cp.getint(sectname, "propagate")
        else:
            propagate = 1
        if qn in existing_logger_names:
            raise Exception("Logger already exists: %s" % qn)
        logger = logging.getLogger(qn)
        if "level" in opts:
            level = cp.get(sectname, "level")
            logger.setLevel(logging._levelNames[level])
        for h in logger.handlers[:]:
            logger.removeHandler(h)
        logger.propagate = propagate
        logger.disabled = 0
        hlist = cp.get(sectname, "handlers")
        if len(hlist):
            hlist = hlist.split(",")
            hlist = logging.config._strip_spaces(hlist)
            for hand in hlist:
                logger.addHandler(handlers[hand])
