#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import sys
import os
import os.path
import code
import atexit
import logging
import transaction
from subprocess import Popen, PIPE
from optparse import OptionParser
import inspect
import re
from collections import defaultdict
from itertools import izip
from pprint import pformat
from Acquisition import aq_chain, aq_base
from zope.interface import implements
from zope.event import notify


# Parse the command line for host and port; have to do it before Zope
# configuration, because it hijacks option parsing.

parser = OptionParser(usage='usage: %prog [options] -- [ipthon_options] [ipython_args]')
parser.add_option('--host',
            dest="host", default=None,
            help="Hostname of ZEO server")
parser.add_option('--port',
            dest="port", type="int", default=None,
            help="Port of ZEO server")
parser.add_option('--script',
            dest="script", default=None,
            help="Name of file to execute.")
parser.add_option('--commit',
            dest="commit", default=False, action="store_true",
            help="Run commit() at end of script?")
parser.add_option('--shell',
            dest="shell", default=False, action="store_true",
            help="Start a shell at end of script?")
parser.add_option('-n', '--no-ipython',
            dest="use_ipython", default=True, action="store_false",
            help="Do not embed IPython shell if IPython is found")

opts, args = parser.parse_args()

readline = rlcompleter = None
Completer = object
IPShellEmbed = None

if opts.use_ipython:
    try:
        import readline

        try:
            from IPython import embed as IPShellEmbed
        except ImportError:
            IPShellEmbed = None
        except AttributeError:
            # Looks like we have IPython but the wrong version of readline, likely on OSX 10.6
            IPShellEmbed = None
        from rlcompleter import Completer
    except ImportError:
        pass

# Zope magic ensues!
import Zope2
CONF_FILE = os.path.join(os.environ['ZENHOME'], 'etc', 'zope.conf')

# hide any positional arguments during Zope2 configure
_argv = sys.argv
sys.argv = [sys.argv[0], ] + [x for x in sys.argv[1:] if x.startswith("-")]
Zope2.configure(CONF_FILE)
sys.argv = _argv # restore normality

# Now we have the right paths, so we can do the rest of the imports
from Products.CMFCore.utils import getToolByName
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Products.ZenUtils.path import zenPath
from Products.ZenUtils.Utils import set_context
from Products.ZenModel.IpNetwork import IpNetworkPrinterFactory
from Products.ZenMessaging import audit
from Products.Zuul.utils import safe_hasattr
from Products.ZenModel.interfaces import IZenDMDStartedEvent
from Products.Zuul.catalog.events import IndexingEvent


_CUSTOMSTUFF = []


def set_db_config(host=None, port=None):
    # Modify the database configuration manually
    from App.config import getConfiguration
    for serverConfig in getConfiguration().databases:
        adapterConfig= serverConfig.config.storage.config.adapter.config
        xhost, xport = adapterConfig.host, adapterConfig.port
        if host: 
            xhost = host
        if port: 
            xport = port
        adapterConfig.host, adapterConfig.port = xhost, xport

def _search_super(obj, pattern, s, seen):
    vars_ = vars(obj)
    mro = tuple(reversed(obj.__class__.mro()))

    def search_mro(dct, attr_name, attr=None):
        for cls in mro:
            if safe_hasattr(cls, attr_name):
                dct[cls].append((attr_name, attr))
                break

    attrs = defaultdict(lambda: [])
    methods = defaultdict(lambda: [])
    for attr_name in dir(obj):
        if '__' in attr_name:
            continue
        if attr_name in seen:
            continue
        if not safe_hasattr(obj, attr_name):
            continue
        if pattern is not None and not pattern.search(attr_name):
            continue
        attr = vars_[attr_name] if attr_name in vars_ \
                                            else getattr(obj, attr_name)
        if not inspect.ismethod(attr):
            search_mro(attrs, attr_name, attr)
            continue
        search_mro(methods, attr_name, attr)
    mro_slice = mro if s is None else mro[-s - 1:]
    new_seen = set([])
    for key, attr_infos in attrs.items() + methods.items():
        for attr_name, attr in attr_infos:
            new_seen.add(attr_name)
    return new_seen, (mro_slice, attrs, methods)


def _search_print(mro_slice, attrs, methods):
    for cls in mro_slice:
        if not attrs[cls] and not methods[cls]:
            continue
        print '\n', '-' * 79, '\n', cls.__module__, cls.__name__
        first = True
        for attr_name, attr in attrs[cls]:
            if first:
                print
                first = False
            if '\n' not in pformat(attr):
                print ' ', attr_name, '=', pformat(attr)
        for attr_name, attr in attrs[cls]:
            if '\n' in pformat(attr):
                print '\n ', attr_name, '=\n', pformat(attr, 4)
        for attr_name, attr in methods[cls]:
            defaults = () if attr.func_defaults is None \
                                            else attr.func_defaults
            co = attr.func_code
            varnames = co.co_varnames[1:]
            kwargs = dict((v, '{0}={1}'.format(v, d)) for v, d \
                    in izip(reversed(varnames), reversed(defaults)))
            args = [kwargs.get(v, v) for v in varnames]
            sigargs = (attr_name, ', '.join(args))
            signature = '{0}({1})'.format(*sigargs)
            fifmt = '{co.co_filename}:{co.co_firstlineno}'
            fileinfo = fifmt.format(co=co)
            print '\n ', signature, '\n ', fileinfo


def _customStuff():
    """
    Everything available in the console is defined here.
    """

    import socket
    from pprint import pprint
    from Products.ZenUtils.Utils import setLogLevel
    from Products.Zuul import getFacade, listFacades

    # Connect to the database, set everything up
    app = Zope2.app()
    app = set_context(app)

    def login(username='admin'):
        utool = getToolByName(app, 'acl_users')
        user = utool.getUserById(username)
        if user is None:
            user = app.zport.acl_users.getUserById(username)
        user = user.__of__(utool)
        newSecurityManager(None, user)
        from AccessControl.Implementation import setImplementation
        #Chip's pitched battle against segfault.
        #import pdb;pdb.set_trace()
        #setImplementation('PYTHON')

    login('admin')

    # Useful references
    zport = app.zport
    dmd   = zport.dmd
    sync  = zport._p_jar.sync
    find  = dmd.Devices.findDevice
    devices = dmd.Devices
    me = find(socket.getfqdn())
    auditComment = audit.auditComment
    shell_stdout = []
    shell_stderr = []
    # evaluate any command the user has defined to startup
    for idx, line in enumerate(dmd.getZenDMDStartupCommands()):
        try:
            exec line in globals(), locals()
        except Exception as e:
            print "Error evaluating zendmd startup command #%s  %s, %s" %(idx, line, str(e))
    def reindex():
        sync()
        dmd.Devices.reIndex()
        dmd.Events.reIndex()
        dmd.Manufacturers.reIndex()
        dmd.Networks.reIndex()
        commit()

    def logout():
        noSecurityManager()

    def zhelp():
        cmds = sorted(filter(lambda x: not x.startswith("_"), _CUSTOMSTUFF))
        for cmd in cmds:
            print cmd

    def commit():
        audit.audit('Shell.Script.Commit')
        from transaction import commit
        commit()

    def grepdir(obj, regex=""):
        if regex:
            import re
            pattern = re.compile(regex)
            for key in dir(obj):
                if pattern.search(key):
                    print key

    def indexObject(obj):
        """
        Updates every index available for the object.
        """
        if hasattr(obj, 'index_object'):
            obj.index_object()
        notify(IndexingEvent(obj))

    def lookupGuid(guid):
        """
        Given a guid this returns the object that it identifies
        """
        from Products.ZenUtils.guid.interfaces import IGUIDManager
        manager = IGUIDManager(dmd)
        return manager.getObject(guid)

    def version():
        for info in zport.About.getAllVersions():
            print "%10s: %s" % (info['header'], info['data'])
        print "%10s: %s" % ("DMD", dmd.version)

    def printNets(net=dmd.Networks, format="text", out=sys.stdout):
        """
        Print out the IpNetwork and IpAddress hierarchy under net.  To print
        out everything call printNets(dmd.Networks).  format can be text,
        python, or xml.
        """
        factory = IpNetworkPrinterFactory()
        printer = factory.createIpNetworkPrinter(format, out)
        printer.printIpNetwork(net)


    def cleandir(obj):
        portaldir = set(dir(dmd))
        objdir = set(dir(obj))
        appdir = set(dir(app))
        result = sorted(objdir - portaldir - appdir)
        pprint(result)

    def search(obj, p=None, s=None, a=None):
        """Search obj for matching attribute and method names.
           p: pattern to match
           s: super depth (how many inheritance levels to search)
           a: acquisition depth
        (ignores any attribute with '__' in its name)
        """
        pattern = None if p is None else re.compile(p, re.IGNORECASE)
        aq_end = None if a is None else a + 1
        seen = set([])
        all_print_args = {}
        chain = [x for x in aq_chain(obj)[:aq_end] if safe_hasattr(x, 'id') \
                                            and not inspect.ismethod(x.id)]
        for obj_ in chain:
            new_seen, print_args = _search_super(aq_base(obj_), pattern, s, seen)
            seen |= new_seen
            all_print_args[obj_.id] = print_args
        for obj_ in reversed(chain):
            mro_slice, attrs, methods = all_print_args[obj_.id]
            for cls in mro_slice:
                if attrs[cls] or methods[cls]:
                    print '\n', '=' * 79, '\n', path(obj_)
                    _search_print(mro_slice, attrs, methods)
                    break

    def path(obj):
        path_ = '/'.join(x.id for x in reversed(aq_chain(obj)) \
                                            if safe_hasattr(x, 'id') \
                                            and not inspect.ismethod(x.id))
        if path_ == '':
            return obj
        if path_ == 'zport':
            return path_
        if path_ == 'zport/dmd':
            return 'dmd'
        return path_[len('zport/dmd/'):]

    def history(start=None, end=None, lines=30,
                   number=False):
        """
        Display the history starting from entry 'start' to
        entry 'end'. Only available on platforms where the
        readline module can be imported.

        History starts from 0 and goes to a large number.
        The history file is $ZENHOME/.pyhistory by default.

        @parameter start: Line number to start printing
        @type start: integer
        @parameter end: Line number to finish printing
        @type end: integer
        @parameter lines: number of lines to show if no end
        @type lines: integer
        @parameter number: show the line numbers?
        @type number: boolean
        """
        if readline is not None:
            maxHistLength = readline.get_current_history_length()
            if start is None:
                start = maxHistLength
            if end is None:
                end = maxHistLength - lines
            if start < end:
                end, start = start, end
            for i in range(end, start):
                if number:
                    print i, readline.get_history_item(i)
                else:
                    print readline.get_history_item(i)

    def sh(cmd, interactive=True):
        """
        Execute a shell command.  If interactive is False, then
        direct the contents of stdout into shell_stdout and the
        output of stderr into shell_stderr.

        @parameter cmd: shell command to execute
        @type cmd: string
        @parameter interactive: show outut to the screen or not
        @type interactive: boolean
        """
        if interactive:
            proc = Popen(cmd, shell=True)
        else:
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, errors = proc.communicate()
        proc.wait()
        if not interactive:
            output = output.split('\n')[:-1]
            errors = errors.split('\n')[:-1]
            _CUSTOMSTUFF['shell_stdout'] = output
            _CUSTOMSTUFF['shell_stderr'] = errors
        return output, errors

    def edit(file=None, start=None, end=None, lines=30):
        """
        Use the value of the EDITOR environment variable to
        edit a file.  Defaults to the original Unix IDE -- vi.

        @parameter file: name of file to edit -- defaults to a temp file
        @type file: string
        @parameter start: Line number to start printing
        @type start: integer
        @parameter end: Line number to finish printing
        @type end: integer
        @parameter lines: number of lines to show if no end
        @type lines: integer
        """
        editor = os.environ.get('EDITOR', 'vi')
        isNewFile = True
        isTmpName = False
        if file == None:
            isTmpName = True
            file = os.tempnam()
            fp = open(file, 'w')
        elif os.path.exists(file):
            isNewFile = False
        else:
            fp = open(file, 'w')

        if isNewFile and readline is not None:
            maxHistLength = readline.get_current_history_length()
            if start is None:
                start = maxHistLength
            if end is None:
                end = maxHistLength - lines
            if start < end:
                end, start = start, end
            for i in range(end, start):
                fp.write(readline.get_history_item(i) + '\n')
            fp.close()

        sh('%s %s' % (editor, file))
        execfile(file, globals(), _CUSTOMSTUFF)
        if isTmpName:
            os.unlink(file)

    _CUSTOMSTUFF = locals()
    return _CUSTOMSTUFF


class ZenCompleter(Completer):
    """
    Provides the abiility to specify *just* the zendmd-specific
    stuff when you first enter and hit tab-tab, and also the
    ability to remove junk that we don't need to see.
    """
    ignored_names = [
        "COPY", "DELETE", "HEAD", "HistoricalRevisions",
        "LOCK", "MKCOL", "MOVE", "OPTIONS",
        "Open", "PROPFIND", "PROPPATCH",
        "PUT", "REQUEST", "SQLConnectionIDs",
        "SiteRootAdd", "TRACE", "UNLOCK",
        "ac_inherited_permissions",
        "access_debug_info",
        "bobobase_modification_time",
        "manage_historyCompare",
        "manage_historyCopy",
        "manage_addDTMLDocument",
        "manage_addDTMLMethod",
        "manage_clone",
        "manage_copyObjects",
        "manage_copyright",
        "manage_cutObjects",
        "manage_historicalComparison",
        "validClipData",
        "manage_CopyContainerAllItems",
        "manage_CopyContainerFirstItem",
        "manage_DAVget",
        "manage_FTPlist",
        "manage_UndoForm",
        "manage_access",
    ]
    ignored_prefixes = [
       '_', 'wl_', 'cb_', 'acl', 'http__', 'dav_',
       'manage_before', 'manage_after',
       'manage_acquired',
    ]

    current_prompt = ''
    def complete(self, text, state):
        # Don't show all objects if we're typing in code
        if self.current_prompt == sys.ps2:
            if state == 0:
                if text == '':
                    return '    '
            else:
                return None

        return Completer.complete(self, text, state)


    def global_matches(self, text):
        """
        Compute matches when text is a simple name.
        """
        matches = []
        for name in self.namespace:
            if name.startswith(text):
                matches.append(name)

        return matches

    def attr_matches(self, text):
        """
        Compute matches when text contains a dot.
        """
        matches = []
        for name in Completer.attr_matches(self, text):
            if name.endswith("__roles__"):
                continue
            component = name.split('.')[-1]
            if component in self.ignored_names:
                continue
            ignore = False
            for prefix in self.ignored_prefixes:
                if component.startswith(prefix):
                    ignore = True
                    break

            if not ignore:
                matches.append(name)

        return matches
        #return filter(lambda x: not x.endswith("__roles__"),
                      #Completer.attr_matches(self, text))

class ZenDMDStartedEvent(object):
    """
    Event that is emitted when zendmd starts.
    """
    implements(IZenDMDStartedEvent)
    def __init__(self):
        pass

class HistoryConsole(code.InteractiveConsole):
    """
    Subclass the default InteractiveConsole to get readline history
    """
    def __init__(self, locals=None, filename="<console>",
                 histfile=zenPath('.pyhistory')):
        code.InteractiveConsole.__init__(self, locals, filename)
        self.completer = None
        if readline is not None:
            self.completer = ZenCompleter(locals)
            readline.set_completer(self.completer.complete)
            readline.parse_and_bind("tab: complete")
        self.init_history(histfile)


    def init_history(self, histfile):
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(histfile)
            except IOError:
                pass
            atexit.register(self.save_history, histfile)

    def save_history(self, histfile):
        readline.write_history_file(histfile)

    def raw_input(self, prompt=""):
        if self.completer:
            self.completer.current_prompt = prompt
        return code.InteractiveConsole.raw_input(self, prompt)

    def runsource(self, source, filename):
        if source and source[0] == '!':
            self.locals['sh'](source[1:])
            return False
        elif source and source[0] == '|':
            self.locals['sh'](source[1:], interactive=False)
            return False
        return code.InteractiveConsole.runsource(self, source, filename)


if __name__=="__main__":
    # Do we want to connect to a database other than the one specified in
    # zope.conf?
    if opts.host or opts.port:
        set_db_config(opts.host, opts.port)

    vars_ = _customStuff()

    audit.audit('Shell.Script.Run')

    # set the first positional argument as the --script arg
    for arg in sys.argv[1:]:
        if not arg.startswith("-") and os.path.exists(arg):
           opts.script = arg
           break
    notify(ZenDMDStartedEvent())
    if opts.script:
        if not os.path.exists(opts.script):
            print "Unable to open script file '%s' -- exiting" % opts.script
            sys.exit(1)
        # copy globals() to temporary dict
        allVars = dict(globals().iteritems())
        allVars.update(vars_)
        oldKeys = {k for k in allVars.keys()}
        execfile(opts.script, allVars)
        if opts.shell:
            newKeys = {k for k in allVars.keys()}.difference(oldKeys)
            vars_.update({k: allVars[k] for k in newKeys})
        else:
            if opts.commit:
                audit.audit('Shell.Script.Commit')
                from transaction import commit
                commit()
            else:
                try:
                    transaction.abort()
                except Exception:
                    pass
            sys.exit(0)

    _banner = ("Welcome to the Zenoss dmd command shell!\n"
             "'dmd' is bound to the DataRoot. 'zhelp()' to get a list of "
             "commands.")
    try:
        if IPShellEmbed:
            sys.argv[1:] = args
            IPShellEmbed(banner1=_banner, user_ns=vars_)
        else:
            if readline is not None:
                _banner = '\n'.join([_banner,
                                     "Use TAB-TAB to see a list of zendmd related commands.",
                                     "Tab completion also works for objects -- hit tab after"
                                     " an object name and '.'", " (eg dmd. + tab-key)."])


            # Start up the console
            myconsole = HistoryConsole(locals=vars_)
            myconsole.interact(_banner)
    finally:
        # try to abort any open transactions for our two phase commit listeners
        try:
            transaction.abort()
        except Exception:
            pass
