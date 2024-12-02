##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


""" Portal class

$Id: ZentinelPortal.py,v 1.17 2004/04/08 15:35:25 edahl Exp $
"""

import urlparse
import re
import time
import textwrap

from AccessControl import getSecurityManager, ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from App.special_dtml import HTMLFile

from Products.Sessions.BrowserIdManager import constructBrowserIdManager
from Products.BeakerSessionDataManager.sessiondata import (
    addBeakerSessionDataManager
)

from Products.CMFCore.PortalObject import PortalObjectBase
from Products.CMFCore.utils import getToolByName

from Products.ZenUtils import Security, Time
from Products.ZenUtils.deprecated import deprecated

from ZenossSecurity import *


class ZentinelPortal(PortalObjectBase):
    """
    The *only* function this class should have is to help in the setup
    of a new ZentinelPortal. It should not assist in the functionality at all.
    """
    meta_type = 'ZentinelPortal'

    _properties = (
        {'id': 'title', 'type': 'string'},
        {'id': 'description', 'type': 'text'},
    )
    title = ''
    description = ''

    security = ClassSecurityInfo()

    def __init__(self, id, title=''):
        PortalObjectBase.__init__(self, id, title)

    def server_time(self):
        return time.time()

    def _additionalQuery(self):
        return None

    def getLoginMessage(self):
        WIDTH = 27
        DELIMITER = "<br />"

        request = self.REQUEST
        session = self.session_data_manager.getSessionData()

        url = request.form.get('came_from')
        if 'terms' in url:
            msg = "You did not accept the Zenoss Terms."
        elif request.SESSION.get('locked_message', False):
            msg = request.SESSION.get('locked_message')
            del request.SESSION['locked_message']
        elif session.get('login_message'):
            msg = session.get('login_message')
            del session['login_message']
        elif 'submitted' in url:
            msg = ("Your session has expired or you have entered an incorrect"
                   " username or password.")
        else:
            msg = ""

        return DELIMITER.join(textwrap.wrap(msg, WIDTH))

    security.declareProtected(ZEN_COMMON, 'searchDevices')
    @deprecated
    def searchDevices(self, queryString='', REQUEST=None):
        """Returns the concatenation of a device name, ip and mac
        search on the list of devices.
        """
        # TODO: Remove. Not used anymore in Zenoss code --Ian
        return []

    security.declareProtected(ZEN_COMMON, 'searchComponents')
    @deprecated
    def searchComponents(self, device='', component='', REQUEST=None):
        """
        Redirect to the component of a device. Hopefully.
        """
        # TODO: Remove. Not used anymore in Zenoss code --Ian
        return []

    security.declareProtected(ZEN_COMMON, 'dotNetProxy')
    def dotNetProxy(self, path='', params={}, REQUEST=None):
        """
        Logs in to Zenoss.net using the user's credentials and retrieves data,
        thereby putting it in the current domain
        """
        session = self.dmd.ZenUsers.getUserSettings().getDotNetSession()
        response = session.open(path.lstrip('/'))
        if response:
            data = response.read()
            headers = response.headers.dict
            url = response.geturl()
            response.close()
        else:
            return response
        localbase = 'http://localhost:8080/zport/dotNetProxy?path='
        allrefs = re.compile(r"""(href *= *["']|src *= *["'])(.*?)(["'])""")
        proxyrefs = re.compile(
            r"""((<a[^<>]*?|location\.)href *= *["'])(.*?)(['"])""")

        def mod_rewrite(matchobj):
            start, path, end = matchobj.groups()
            if not path.startswith('javascript'):
                path = urlparse.urljoin(url, path)
            return start + path + end

        def make_proxied(matchobj):
            start, trash, path, end = matchobj.groups()
            path = path.replace(session.base_url, localbase)
            return start + path + end

        data = re.sub(allrefs, mod_rewrite, data)
        data = re.sub(proxyrefs, make_proxied, data)
        for header in headers:
            REQUEST.RESPONSE.setHeader(header, headers[header])
        return data

    def isManager(self, obj=None):
        """
        Return true if user is authenticated and has Manager role.
        """
        user = self.dmd.ZenUsers.getUser()
        if user:
            return user.has_role((MANAGER_ROLE, ZEN_MANAGER_ROLE), obj)

    def has_role(self, role, obj=None):
        """Check to see of a user has a role.
        """
        if obj is None:
            obj = self
        user = getSecurityManager().getUser()
        if user:
            return user.has_role(role, obj)

    def has_permission(self, perm, obj=None):
        """Check to see of a user has a permission.
        """
        if obj is None:
            obj = self
        user = getSecurityManager().getUser()
        if user:
            return user.has_permission(perm, obj)

    def getCurrentYear(self):
        """
        This is purely for copyright on the login page.
        """
        return Time.getYear()

    def getZenossVersionShort(self):
        return self.About.getZenossVersionShort()

    def getVersionedResourcePath(self, path):
        from Products.ZenUI3.browser.javascript import absolutifyPath
        return absolutifyPath(path)

    def getLoginButton(self):
        return """<input id="loginButton" type="submit" name="submitbutton"
                class="submitbutton" value=""/>"""

    def getExtraLoginFormContents(self):
        """
        On first run, log us in as admin automatically.

        This is done via a proxy form with hidden fields, so that the browser
        doesn't ask to save the password (which will be changed on the next
        screen).
        """
        if not self.dmd._rq:
            return """
            <form id="_proxy_form">
            <input type="hidden" name="__ac_name"/>
            <input type="hidden" name="__ac_password"/>
            <input type="hidden" name="came_from" value="/zport/dmd/quickstart"/>
            </form>
            <script>
            var origform=document.forms[0];
            var newform = document.getElementById('_proxy_form');
            newform.__ac_name.value = 'admin';
            newform.__ac_password.value = 'zenoss';
            newform.action = origform.action;
            newform.method = origform.method;
            newform.submit()
            </script>
            """

    def ruok(self):
        """
        check if zport is ok by answering a question only the
        real zport would know, but an imposter wouldn't know
        """
        return "imok"


InitializeClass(ZentinelPortal)


class PortalGenerator:

    klass = ZentinelPortal

    def setupTools(self, p):
        """Set up initial tools"""
        addCMFCoreTool = p.manage_addProduct['CMFCore'].manage_addTool
        addCMFCoreTool('CMF Skins Tool', None)

    def setupMailHost(self, p):
        p.manage_addProduct['MailHost'].manage_addMailHost(
            'MailHost', smtp_host='localhost')

    def setupUserFolder(self, p):
        Security.createPASFolder(p)
        Security.setupPASFolder(p)

    def setupCookieAuth(self, p):
        pass

    def setupRoles(self, p):
        # Set up the suggested roles.
        p.__ac_roles__ += (ZEN_USER_ROLE, ZEN_MANAGER_ROLE,)

    def setupPermissions(self, p):
        # Set up some suggested role to permission mappings.
        mp = p.manage_permission

        role_owner_manager = [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE]
        mp(ZEN_CHANGE_SETTINGS,         role_owner_manager, 1)
        mp(ZEN_CHANGE_DEVICE,           role_owner_manager, 1)
        mp(ZEN_CHANGE_DEVICE_PRODSTATE, role_owner_manager, 1)
        mp(ZEN_MANAGE_DMD,              role_owner_manager, 1)
        mp(ZEN_DELETE,                  role_owner_manager, 1)
        mp(ZEN_DELETE_DEVICE,           role_owner_manager, 1)
        mp(ZEN_ADD,                     role_owner_manager, 1)
        mp(
            ZEN_VIEW,
            [ZEN_USER_ROLE, ZEN_MANAGER_ROLE,
             MANAGER_ROLE, OWNER_ROLE]
        )
        mp(ZEN_COMMON,
            ["Authenticated", ZEN_USER_ROLE, ZEN_MANAGER_ROLE,
             MANAGER_ROLE, OWNER_ROLE],
            1)

        # Events
        mp(ZEN_MANAGE_EVENTMANAGER,     role_owner_manager, 1)
        mp(ZEN_MANAGE_EVENTS,           role_owner_manager, 1)
        mp(ZEN_SEND_EVENTS,             role_owner_manager, 1)

        manager_role = [ZEN_MANAGER_ROLE, MANAGER_ROLE]
        mp(ZEN_CHANGE_ADMIN_OBJECTS,    manager_role, 1)
        mp(ZEN_CHANGE_EVENT_VIEWS,      manager_role, 1)
        mp(ZEN_ADMIN_DEVICE,            manager_role, 1)
        mp(ZEN_MANAGE_DEVICE,           manager_role, 1)
        mp(ZEN_ZPROPERTIES_EDIT,        manager_role, 1)
        mp(ZEN_EDIT_LOCAL_TEMPLATES,    manager_role, 1)
        mp(ZEN_MAINTENANCE_WINDOW_EDIT, manager_role, 1)
        mp(ZEN_ADMINISTRATORS_EDIT,     manager_role, 1)

        manager_role_usr = [ZEN_MANAGER_ROLE, MANAGER_ROLE, ZEN_USER_ROLE]
        mp(ZEN_ZPROPERTIES_VIEW,        manager_role_usr, 1)
        mp(ZEN_DEFINE_COMMANDS_VIEW,    manager_role_usr, 1)
        mp(ZEN_MAINTENANCE_WINDOW_VIEW, manager_role_usr, 1)
        mp(ZEN_ADMINISTRATORS_VIEW,     manager_role_usr, 1)

        mp(ZEN_CHANGE_ALERTING_RULES,
            [ZEN_MANAGER_ROLE, MANAGER_ROLE, OWNER_ROLE], 1)

        mp(ZEN_RUN_COMMANDS,
            [ZEN_USER_ROLE, ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)

        mp(ZEN_DEFINE_COMMANDS_EDIT,
            [MANAGER_ROLE], 1)

        # Triggers
        mp(MANAGE_TRIGGER,                      role_owner_manager, 1)
        mp(UPDATE_TRIGGER,                      role_owner_manager, 1)
        mp(UPDATE_NOTIFICATION,                 role_owner_manager, 1)
        mp(MANAGE_NOTIFICATION_SUBSCRIPTIONS,   role_owner_manager, 1)
        mp(VIEW_TRIGGER,
            [ZEN_MANAGER_ROLE, OWNER_ROLE,
             MANAGER_ROLE, ZEN_USER_ROLE],
            1)

    def setupDefaultSkins(self, p):
        from Products.CMFCore.DirectoryView import addDirectoryViews
        ps = getToolByName(p, 'portal_skins')
        addDirectoryViews(ps, 'skins', globals())
        ps.manage_addProduct['OFSP'].manage_addFolder(id='custom')
        ps.addSkinSelection('Basic', "custom, zenmodel", make_default=1)
        p.setupCurrentSkin()

    def setupSessionManager(self, p):
        """build a session manager and brower id manager for zport"""
        constructBrowserIdManager(p, cookiepath="/zport")
        sdmId = 'session_data_manager'
        app = p.getPhysicalRoot()
        if app.hasObject(sdmId):
            app._delObject(sdmId)
        addBeakerSessionDataManager(app, sdmId, 'Beaker Session Data Manager')

    def setup(self, p, create_userfolder):
        if create_userfolder:
            self.setupUserFolder(p)
        self.setupTools(p)
        self.setupMailHost(p)
        self.setupRoles(p)
        self.setupPermissions(p)
        self.setupDefaultSkins(p)
        self.setupSessionManager(p)

    def create(self, parent, id, create_userfolder):
        id = str(id)
        portal = self.klass(id=id)
        parent._setObject(id, portal)
        # Return the fully wrapped object.
        p = parent.this()._getOb(id)
        self.setup(p, create_userfolder)
        return p

    def setupDefaultProperties(self, p, title, description,
                               email_from_address, email_from_name,
                               validate_email,
                               ):
        p._setProperty('email_from_address', email_from_address, 'string')
        p._setProperty('email_from_name', email_from_name, 'string')
        p._setProperty('validate_email', validate_email and 1 or 0, 'boolean')
        p.title = title
        p.description = description


manage_addZentinelPortal = HTMLFile('dtml/addPortal', globals())
manage_addZentinelPortal.__name__ = 'addPortal'


def manage_addZentinelPortal(obj, id="zport", title='Zentinel Portal',
                             description='',
                             create_userfolder=True,
                             email_from_address='postmaster@localhost',
                             email_from_name='Portal Administrator',
                             validate_email=0, RESPONSE=None):
    '''
    Adds a portal instance.
    '''
    gen = PortalGenerator()
    from string import strip
    id = strip(id)
    p = gen.create(obj, id, create_userfolder)
    gen.setupDefaultProperties(p, title, description,
                               email_from_address, email_from_name,
                               validate_email)
    if RESPONSE is not None:
        RESPONSE.redirect(obj.absolute_url_path() + '/manage_main')
