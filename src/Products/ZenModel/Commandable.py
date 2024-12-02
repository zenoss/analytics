##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenMessaging.audit import audit
from Products.ZenUtils.deprecated import deprecated

__doc__="""Commandable

Mixin class for classes that need a relationship back from UserCommand.

"""

from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from ZenossSecurity import *
from UserCommand import UserCommand
from Acquisition import aq_base, aq_chain
from Products.PageTemplates.Expressions import getEngine
from Products.ZenUtils.csrf import validate_csrf_token
from Products.ZenUtils.ZenTales import talesCompile
from Products.ZenUtils.Utils import unused
from Products.ZenWidgets import messaging
from DateTime import DateTime
import os
import popen2
import fcntl
import select
import signal
import time
import cgi
import sys

import logging
log = logging.getLogger("zen.Device")

class Commandable:

    defaultTimeout = 60 # seconds

    security = ClassSecurityInfo()

    security.declareProtected(ZEN_DEFINE_COMMANDS_EDIT, 'manage_addUserCommand')
    @validate_csrf_token
    def manage_addUserCommand(self, newId=None, desc='', cmd='', REQUEST=None):
        "Add a UserCommand to this device"
        unused(desc, cmd)
        uc = None
        if newId:
            uc = UserCommand(newId)
            self.userCommands._setObject(newId, uc)
            uc = self.userCommands._getOb(newId)
            if self.meta_type == 'Device':
                self.setLastChange()
            uc.description = desc
            uc.command = cmd
        if REQUEST:
            if uc:
                audit('UI.Command.Add', newId, action=uc.command, description=uc.description)
                messaging.IMessageSender(self).sendToBrowser(
                    'Command Added',
                    'User command %s has been created.' % newId
                )
                screenName = REQUEST.get("editScreenName", "")
                return REQUEST.RESPONSE.redirect(uc.getPrimaryUrlPath() +
                        '/%s' % screenName if screenName else '')
            return self.callZenScreen(REQUEST, True)
        return uc


    security.declareProtected(ZEN_DEFINE_COMMANDS_EDIT,
        'manage_deleteUserCommand')
    def manage_deleteUserCommand(self, ids=(), REQUEST=None):
        "Delete User Command(s) to this device"
        if isinstance(ids, basestring):
            ids = [ids]
        for id in ids:
            self.userCommands._delObject(id)
        if self.meta_type == 'Device':
            self.setLastChange()
        if REQUEST:
            for id in ids:
                audit('UI.Command.Delete', id)
            messaging.IMessageSender(self).sendToBrowser(
                'Commands Deleted',
                'User commands %s have been deleted.' % " ".join(ids)
            )
            return self.redirectToUserCommands(REQUEST)

    security.declareProtected(ZEN_DEFINE_COMMANDS_EDIT,
        'manage_editUserCommand')
    def manage_editUserCommand(self, commandId, REQUEST):
        ''' Want to redirect back to management tab after a save
        '''
        command = self.getUserCommand(commandId)
        if command:
            password = REQUEST.form.get('password', '')
            if not self.dmd.ZenUsers.authenticateCredentials(
                self.dmd.ZenUsers.getUser().getId(), password):
                messaging.IMessageSender(self).sendToBrowser(
                    'Password Error',
                    'Invalid or empty password.',
                    priority=messaging.WARNING
                )
                return REQUEST.RESPONSE.redirect(command.absolute_url_path())
            del REQUEST.form['password']
            command.manage_changeProperties(**REQUEST.form)
            audit('UI.Command.Edit', commandId, action=REQUEST.form.get('command',''))
        return self.redirectToUserCommands(REQUEST)


    security.declareProtected(ZEN_RUN_COMMANDS, 'manage_doUserCommand')
    @deprecated
    def manage_doUserCommand(self, commandId=None, REQUEST=None):
        ''' Execute a UserCommand. If REQUEST then
        wrap output in proper zenoss html page.
        '''
        # This could be changed so that output is sent through a
        # logger so that non web-based code can produce output.
        # Not necessary for now.

        command = self.getUserCommands(asDict=True).get(commandId,None)
        if not command:
            if REQUEST:
                return self.redirectToUserCommands(REQUEST)
        if REQUEST:
            REQUEST['cmd'] = command
            header, footer = self.commandOutputTemplate().split('OUTPUT_TOKEN')
            REQUEST.RESPONSE.write(str(header))
            out = REQUEST.RESPONSE
        else:
            out = None

        startTime = time.time()
        numTargets = 0
        for target in self.getUserCommandTargets():
            numTargets += 1
            try:
                self.write(out, '')
                self.write(out, '==== %s ====' % target.id)
                self.doCommandForTarget(command, target, out)
                #untested, method call cannot be found
                audit('UI.Command.Invoke', commandId, target=target)
            except Exception:
                self.write(out,
                    'exception while performing command for %s' % target.id)
                self.write(
                    out, 'type: %s  value: %s' % tuple(sys.exc_info()[:2]))
            self.write(out, '')
        self.write(out, '')
        self.write(out, 'DONE in %s seconds on %s targets' %
                    (long(time.time() - startTime), numTargets))
        REQUEST.RESPONSE.write(str(footer))


    def doCommandForTarget(self, cmd, target, out):
        ''' Execute the given UserCommand on the given target
        '''
        compiled = self.compile(cmd, target)
        child = popen2.Popen4(compiled)
        flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
        fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
        timeout = getattr(target, 'zCommandCommandTimeout', self.defaultTimeout)
        timeout = max(timeout, 1)
        endtime = time.time() + timeout
        self.write(out, '%s' % compiled)
        self.write(out, '')
        pollPeriod = 1
        firstPass = True
        while time.time() < endtime and (firstPass or child.poll() == -1):
            firstPass = False
            r, w, e = select.select([child.fromchild], [], [], pollPeriod)
            if r:
                t = child.fromchild.read()
                # We are sometimes getting to this point without any data
                # from child.fromchild.  I don't think that should happen
                # but the conditional below seems to be necessary.
                if t:
                    self.write(out, t)

        if child.poll() == -1:
            self.write(out, 'Command timed out for %s' % target.id +
                            ' (timeout is %s seconds)' % timeout)
            os.kill(child.pid, signal.SIGKILL)


    def compile(self, cmd, target):
        ''' Evaluate command as a tales expression
        '''
        command = cmd.command
        # make sure we are targeting the right collector
        if not command.startswith("dcsh") and hasattr(target, "getPerformanceServerName"):
            collector = target.getPerformanceServer()
            if collector:
                command = 'zminion --minion-name zminion_%s run -- "%s"' % (target.getPerformanceServerName(), command.replace('\n', ' '))
        exp = "string:"+ command
        compiled = talesCompile(exp)
        environ = target.getUserCommandEnvironment()
        res = compiled(getEngine().getContext(environ))
        if isinstance(res, Exception):
            raise res
        return res


    security.declareProtected(ZEN_VIEW, 'getUserCommandIds')
    def getUserCommandIds(self):
        ''' Get the user command ids available in this context
        '''
        commandIds = []
        mychain = self.getAqChainForUserCommands()
        mychain.reverse()
        for obj in mychain:
            if getattr(aq_base(obj), 'userCommands', None):
                for c in obj.userCommands():
                    commandIds.append(c.id)
        return commandIds

    security.declareProtected(ZEN_DEFINE_COMMANDS_VIEW, 'getUserCommands')
    def getUserCommands(self, asDict=False):
        ''' Get the user commands available in this context
        '''
        commands = {}
        mychain = self.getAqChainForUserCommands()
        mychain.reverse()
        for obj in mychain:
            if getattr(aq_base(obj), 'userCommands', None):
                for c in obj.userCommands():
                    commands[c.id] = c
        if not asDict:
            commands = sorted(commands.itervalues(), key=lambda cmd: cmd.getId())
        return commands


    def getAqChainForUserCommands(self):
        return aq_chain(self.primaryAq())


    def redirectToUserCommands(self, REQUEST, commandId=None):
        ''' Redirect to the page which lists UserCommands
        for this Commandable object.
        '''
        unused(commandId)
        url = self.getUrlForUserCommands()
        if url:
            return REQUEST.RESPONSE.redirect(url)
        return self.callZenScreen(REQUEST)


    def getUrlForUserCommands(self):
        ''' Return url for page which manages user commands
        '''
        # This should be overridden by subclasses of Commandable
        return self.getPrimaryUrlPath()

    security.declareProtected(ZEN_DEFINE_COMMANDS_VIEW, 'getUserCommand')
    def getUserCommand(self, commandId):
        ''' Returns the command from the current context if it exists
        '''
        return self.getUserCommands(asDict=True).get(commandId, None)


    def getUserCommandEnvironment(self):
        ''' Get the environment that provides context for the tales
        evaluation of a UserCommand.
        '''
        # Overridden by Service and Device
        return {
                'target': self,
                'here': self,
                'nothing': None,
                'now': DateTime()
                }


    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        raise NotImplemented


    def write(self, out, lines):
        ''' Output (maybe partial) result text from a UserCommand.
        '''
        # Looks like firefox renders progressive output more smoothly
        # if each line is stuck into a table row.

        # I doubt the above statement, as tested on Firefox 3
        # this only generates a larger DOM object and does nothing
        # for smoothness. It actually slows things down for large command
        # output. Should maybe retested especially now that we are
        # using CSS pre
        startLine = '<tr><td class="commandoutput">'
        endLine = '\n</td></tr>\n'
        if out:
            if not isinstance(lines, list):
                lines = [lines]
            for l in lines:
                if not isinstance(l, str):
                    l = str(l)
                l = l.strip()
                l = cgi.escape(l)
                l = l.replace('\n', endLine + startLine)
                out.write(startLine + l + endLine)



InitializeClass(Commandable)
