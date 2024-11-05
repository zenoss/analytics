##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""ZenPackManager
ZenPackManager is a Zope Product that helps manage ZenPacks
"""

from AccessControl.class_init import InitializeClass
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from AccessControl import ClassSecurityInfo
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.csrf import validate_csrf_token
from Products.ZenUtils.path import binPath, varPath
from Products.ZenWidgets import messaging
import os
import tempfile
import logging

from ZenossSecurity import (
    ZEN_MANAGE_DMD, ZEN_MANAGE_GLOBAL_SETTINGS, ZEN_MANAGE_GLOBAL_COMMANDS,
    ZEN_MANAGE_USERS, ZEN_VIEW_USERS, ZEN_MANAGE_ZENPACKS, ZEN_MANAGE_GROUPS,
    ZEN_VIEW_SOFTWARE_VERSIONS, ZEN_MANAGE_EVENT_CONFIG, ZEN_MANAGE_UI_SETTINGS
)

log = logging.getLogger('zen.ZenPackManager')

def manage_addZenPackManager(context, newId='', REQUEST=None):
    """
    Create a ZenPackManager instance
    """
    if not newId:
        newId = 'ZenPackManager'
    zpm = ZenPackManager(newId)
    context._setObject(newId, zpm)
    zpm = context._getOb(newId)
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url_path() + '/manage_main')


class ZenPackManager(ZenModelRM):
    """
    ZenPackManager is responsibe for managing ZenPacks
    """

    portal_type = meta_type = 'ZenPackManager'

    default_catalog = 'zenPackNameSearch'

    _relations = ZenModelRM._relations + (
        ('packs', ToManyCont(ToOne, 'Products.ZenModel.ZenPack', 'manager')),
        )

    factory_type_information = (
        {
            'immediate_view' : 'viewZenPacks',
            'actions'        :
            (
                { 'id'            : 'settings'
                , 'name'          : 'Settings'
                , 'action'        : '../editSettings'
                , 'permissions'   : ( ZEN_MANAGE_GLOBAL_SETTINGS, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Commands'
                , 'action'        : '../dataRootManage'
                , 'permissions'   : (ZEN_MANAGE_GLOBAL_COMMANDS,)
                },
                { 'id'            : 'users'
                , 'name'          : 'Users'
                , 'action'        : '../ZenUsers/manageUserFolder'
                , 'permissions'   : (ZEN_VIEW_USERS, ZEN_MANAGE_USERS, ZEN_MANAGE_GROUPS,)
                },
                { 'id'            : 'packs'
                , 'name'          : 'ZenPacks'
                , 'action'        : 'viewZenPacks'
                , 'permissions'   : (ZEN_MANAGE_ZENPACKS,)
                },
                { 'id'            : 'portlets'
                , 'name'          : 'Portlets'
                , 'action'        : '../editPortletPerms'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'versions'
                , 'name'          : 'Versions'
                , 'action'        : '../About/zenossVersions'
                , 'permissions'   : (ZEN_VIEW_SOFTWARE_VERSIONS,)
                },
                { 'id'            : 'eventConfig'
                , 'name'          : 'Events'
                , 'action'        : 'eventConfig'
                , 'permissions'   : (ZEN_MANAGE_EVENT_CONFIG, )
                },
                { 'id'            : 'userInterfaceConfig'
                , 'name'          : 'User Interface'
                , 'action'        : '../userInterfaceConfig'
                , 'permissions'   : (ZEN_MANAGE_UI_SETTINGS,)
                },
            )
         },
        )

    security = ClassSecurityInfo()


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addZenPack')
    @validate_csrf_token
    def manage_addZenPack(self, packId, REQUEST=None, devDir=''):
        """
        Create a new zenpack on the filesystem with the given info.
        Install the pack.  If REQUEST then render the REQUEST otherwise
        return the new zenpack.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd

        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackNeedMigrateException
            raise ZenPackNeedMigrateException(msg)

        # Make sure a zenpack can be created with given info
        canCreate, msgOrId = ZenPackCmd.CanCreateZenPack(self, packId)
        if canCreate:
            packId = msgOrId
        else:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Add ZenPack', msgOrId)
                return self.callZenScreen(REQUEST, redirect=False)
            from ZenPack import ZenPackException
            raise ZenPackException(msgOrId)

        if devDir == "":
            devDir = varPath("ZenPackSource")

        # Create it
        zpDir = ZenPackCmd.CreateZenPack(packId, devDir=devDir)

        # Install it
        zenPacks = ZenPackCmd.InstallEggAndZenPack(self.dmd, zpDir, link=True,
                                                   forceRunExternal=True)
        zenPack = self.packs._getOb(packId, None)
        audit('UI.ZenPack.Create', packId)
        if REQUEST:
            if zenPack:
                return REQUEST['RESPONSE'].redirect(zenPack.getPrimaryUrlPath())
            messaging.IMessageSender(self).sendToBrowser(
                'Error', 'There was an error creating the ZenPack.',
                priority=messaging.WARNING)
            return self.callZenScreen(REQUEST)
        return zenPack


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_removeZenPacks')
    @validate_csrf_token
    def manage_removeZenPacks(self, ids=(), REQUEST=None):
        """
        Uninstall the given zenpacks.  Uninstall the zenpack egg.  If not in
        development mode then also delete the egg from the filesystem.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd
        # avoid circular imports
        from Products.ZenMessaging.queuemessaging.schema import removeZenPackQueuesExchanges

        # see ZEN-2682 only allow one zenpack to be removed at a time. This is because you
        # can select a zenpack and its dependent. If the dependent is removed first
        # you will get an error removing the zenpack
        if len(ids) > 1:
            msg = 'You can only remove one zenpack at a time.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            raise ZenPackDependentsException(msg)

        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackNeedMigrateException
            raise ZenPackNeedMigrateException(msg)

        canRemove, dependents = ZenPackCmd.CanRemoveZenPacks(self.dmd, ids)
        if not canRemove:
            msg = 'The following ZenPacks depend on one or more of the ' + \
                ' ZenPacks you are trying to remove: %s' % ','.join(dependents)
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackDependentsException
            raise ZenPackDependentsException(msg)
        for zpId in ids:
            zp = self.packs._getOb(zpId, None)
            if zp:
                if zp.isEggPack():
                    ZenPackCmd.RemoveZenPack(self.dmd, zpId, skipDepsCheck=True)
                    audit('UI.ZenPack.Remove', zpId)
                else:
                    os.system('%s --remove %s' % (
                                            binPath('zenpack'), zpId))
                    self._p_jar.sync()

                removeZenPackQueuesExchanges(zp.path())
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'fetchZenPack')
    def fetchZenPack(self, packName, packVersion=''):
        """
        Retrieve the given zenpack from Zenoss.net and install.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd
        zp = ZenPackCmd.FetchAndInstallZenPack(self.dmd, packName, packVersion)
        if REQUEST:
            return REQUEST['RESPONSE'].redirect(zp.getPrimaryUrlPath())
        return zp



    security.declareProtected(ZEN_MANAGE_DMD, 'manage_installZenPack')
    @validate_csrf_token
    def manage_installZenPack(self, zenpack=None, REQUEST=None):
        """
        Installs the given zenpack.  Zenpack is a file upload from the browser.
        """
        import re
        import time
        from subprocess import Popen, PIPE, STDOUT

        from Products.ZenUtils.Utils import get_temp_dir

        ZENPACK_INSTALL_TIMEOUT = 10 * 60 # 10 minutes

        if not getattr(self.dmd, 'ZenPackManager'):
            msg = 'Your Zenoss database appears to be out of date. Try ' \
                    'running zenmigrate to update.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            from ZenPack import ZenPackNeedMigrateException
            raise ZenPackNeedMigrateException(msg)

        msg = ''
        with get_temp_dir() as tempDir:
            # zenpack.filename gives us filename of the zenpack with the
            # path as it exists on the client. We need just the filename.
            base_filename = re.split(r"\\|/", zenpack.filename)[-1]
            # Macs (and other broswers/OSs) always append a .zip to files they
            # believe to be zip files. Remedy that:
            if base_filename.endswith('.egg.zip'):
                base_filename = base_filename[:-7] + 'egg'

            # Write the zenpack to the filesystem
            tFile = open(os.path.join(tempDir, base_filename), 'wb')
            tFile.write(zenpack.read())
            tFile.close()

            p = None # zenpack install process
            # ZEN-1781: Redirect to a temporary file so the stdout buffer
            # doesn't fill up and block till you read from it.
            outFile = None
            try:
                outFile = tempfile.SpooledTemporaryFile()
                # Run zenpack install
                cmd = 'zenpack --install %s --fromui' % tFile.name
                p = Popen(cmd, shell=True, stdout=outFile, stderr=STDOUT)

                endWait = time.time() + ZENPACK_INSTALL_TIMEOUT
                # Wait for install to complete, fail, or time out
                while p.poll() is None and time.time() < endWait:
                    time.sleep(1)

                if p.poll() is not None:
                    outFile.seek(0)
                    msg = outFile.read()
            finally:
                if outFile:
                    outFile.close()
                if p and p.poll() is None:
                    p.kill()
                    msg += 'Zenpack install killed due to timeout'

        if REQUEST:
            # TODO: show the output in a scrollable window.
            # format command result for HTML
            #msg = '<br>'.join(line.strip() for line in msg.split('\n') if line.strip())
            log.info("Output from installing ZenPack %s:\n%s", zenpack.filename, msg)
            success = 'ERROR' not in msg
            msg = "Successfully installed ZenPack %s" % zenpack.filename if success \
                    else "Failed to install ZenPack %s. " \
                         "See event.log for details." % zenpack.filename
            messaging.IMessageSender(self).sendToBrowser('Zenpack', msg,
                priority = messaging.INFO if success else messaging.CRITICAL)
            return self.callZenScreen(REQUEST)


    def getZnetProjectOptions(self):
        """
        Return a list of 2-tuples of (option value, option name) for the
        user to select a Zenoss.net project from.
        """
        projects = self.getZnetProjectsList()
        return [(p, p.split('/')[-1]) for p in projects]


    def getZnetProjectsList(self):
        """
        Return a list of the zenoss.net projects.
        """
        import json
        import Products.ZenUtils.DotNetCommunication as DotNetCommunication
        userSettings = self.dmd.ZenUsers.getUserSettings()
        session = DotNetCommunication.getDotNetSession(
                    userSettings.zenossNetUser,
                    userSettings.zenossNetPassword)
        projects = session.retrieve('projectList')
        projects = json.loads(projects)
        return projects


    def getBrokenPackName(self, ob):
        ''' Extract the zenpack name from the broken module
        '''
        return ob.id if ob.id and ob.id != 'broken' else ob.__class__.__module__


InitializeClass(ZenPackManager)
