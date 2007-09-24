###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import atexit
import socket
try:
    import readline
    import rlcompleter
except ImportError:
    readline = rlcompleter = None
from pprint import pprint

import Globals
import transaction
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager

#from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.ZenUtils import zenPath

if readline:
    # Note: the history code in this file was originally authored by
    # Itamar Shtull-Trauring of Twisted Python. A current copy of his
    # original code is available at http://pastebin.adytum.us/40 though
    # the original has proven difficult to locate.
    zenHome = zenPath()
    historyPath = zenPath('.pyhistory')
    def save_history(historyPath=historyPath):
        import readline
        readline.write_history_file(historyPath)

    if os.path.exists(historyPath):
        readline.read_history_file(historyPath)

class zendmd(ZenScriptBase):
    pass

if __name__ == '__main__':
    zendmd = zendmd(connect=True)
    dmd = zendmd.dmd
    app = dmd.getPhysicalRoot()
    zport = app.zport
    find = dmd.Devices.findDevice
    devices = dmd.Devices
    sync = dmd._p_jar.sync
    commit = transaction.commit
    abort = transaction.abort
    me = find(socket.getfqdn())

    def zhelp():
        cmds = filter(lambda x: not x.startswith("_"), globals())
        cmds.sort()
        for cmd in cmds[2:]: print cmd


    def reindex():
        sync()
        dmd.Devices.reIndex()
        dmd.Events.reIndex()
        dmd.Manufacturers.reIndex()
        dmd.Networks.reIndex()
        commit()

    def login(name):
        '''Logs in.'''
        uf = zport.acl_users
        user = uf.getUserById(name)
        if not hasattr(user, 'aq_base'):
            user = user.__of__(uf)
        newSecurityManager(None, user)

    def logout():
        '''Logs out.'''
        noSecurityManager()

    def grepdir(obj, regex="", exact=""):
        if regex:
            import re
            pattern = re.compile(regex)
            for key in dir(obj):
                if pattern.search(key):
                    print key
        if exact:
            for key in dir(obj):
                if key == exact:
                    print key
    
    print "Welcome to zenoss dmd command shell!"
    print "use zhelp() to list commands"

if readline:
    atexit.register(save_history)
    del os, atexit, readline, rlcompleter, save_history, historyPath
