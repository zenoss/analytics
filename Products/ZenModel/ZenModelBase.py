##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""ZenModelBase

$Id: ZenModelBase.py,v 1.17 2004/04/23 19:11:58 edahl Exp $"""

__version__ = "$Revision: 1.17 $"[11:-2]

import re
import time
import sys

from xml.sax import saxutils
from urllib import unquote
from cgi import escape
import zope.component
import zope.interface
from datetime import datetime
import pytz

from OFS.ObjectManager import checkValidId as globalCheckValidId

from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base, aq_chain

from Products.ZenModel.interfaces import IZenDocProvider
from Products.ZenRelations.ZenPropertyManager import iscustprop
from Products.ZenUtils.path import zenpathjoin, zenpathsplit
from Products.ZenUtils.Utils import getDisplayType
from Products.ZenUtils.Utils import createHierarchyObj, getHierarchyObj
from Products.ZenUtils.Utils import getObjByPath, unpublished

from Products.ZenUtils.csrf import get_csrf_token
from Products.ZenUtils.Utils import prepId as globalPrepId, isXmlRpc
from Products.ZenWidgets import messaging
from Products.ZenUtils.Time import convertTimestampToTimeZone, isoDateTime, convertJsTimeFormatToPy
from Products.ZenUI3.browser.interfaces import INewPath
from Products.ZenMessaging.audit import audit as auditFn
from ZenossSecurity import *

_MARKER = object()


class ZenModelBase(object):
    """
    All ZenModel Persistent classes inherit from this class.  It provides some
    screen management functionality, and general utility methods.
    """
    _zendoc = ''

    sub_meta_types = ()
    #prodStateThreshold = 500

    security = ClassSecurityInfo()

    def __call__(self):
        """
        Invokes the default view.
        """
        if isXmlRpc(self.REQUEST):
            return self
        else:
            newpath = INewPath(self)
            self.REQUEST.response.redirect(newpath)

    def __repr__(self):
        """Return a short string describing the object."""
        return "<{0} at {1}>".format(
            self.__class__.__name__, '/'.join(self.getPhysicalPath()),
        )

    index_html = None  # This special value informs ZPublisher to use __call__


    security.declareProtected(ZEN_VIEW, 'view')
    def view(self):
        '''
        Returns the default view even if index_html is overridden.

        @permission: ZEN_VIEW
        '''
        return self()


    def __hash__(self):
        return hash(self.id)

    def prepId(self, id, subchar='_'):
        """
        Clean out an id of illegal characters.

        @type id: string
        @param subchar: Character to be substituted with illegal characters
        @type subchar: string
        @rtype: string

        >>> dmd.Devices.prepId('ab^*cd')
        'ab__cd'
        >>> dmd.Devices.prepId('ab^*cd', subchar='Z')
        'abZZcd'
        >>> dmd.Devices.prepId('/boot')
        'boot'
        >>> dmd.Devices.prepId('/')
        '-'
        >>> dmd.Devices.prepId(' mydev ')
        'mydev'
        """
        return globalPrepId(id, subchar)

    def checkValidId(self, id, prep_id = False):
        """
        Checks that an id is a valid Zope id.  Looks for invalid characters and
        checks that the id doesn't already exist in this context.

        @type id: string
        @type prep_id: boolean
        @rtype: boolean

        >>> dmd.Devices.checkValidId('^*')
        'The id "^*" contains characters illegal in URLs.'
        >>> dmd.Devices.checkValidId('Server')
        'The id "Server" is invalid - it is already in use.'
        >>> dmd.Devices.checkValidId('ZenTestId')
        True
        """
        new_id = unquote(id)
        if prep_id: new_id = self.prepId(id)
        try:
            globalCheckValidId(self, new_id)
            return True
        except Exception:
            return str(sys.exc_info()[1])


    def getUnusedId(self, relName, baseKey, extensionIter=None):
        """
        Return a new id that is not already in use in the relationship.  If
        baseKey is not already in use, return that.  Otherwise append values
        from extensionIter to baseKey until an used key is found.  The default
        extensionIter appends integers starting with 2 and counting up.

        @type relName: string
        @type baseKey: string
        @type extensionIter: iterator
        @rtype: string
        """
        import itertools
        if extensionIter is None:
            extensionIter = itertools.count(2)
        rel = getattr(self, relName)
        candidate = baseKey
        while candidate in rel.objectIds():
            candidate = self.prepId('%s%s' % (baseKey, extensionIter.next()))
        return candidate


    def getIdLink(self):
        """
        DEPRECATED Return an a link to this object with its id as the name.

        @return: An HTML link to this object
        @rtype: string

        >>> dmd.Devices.getIdLink()
        '<a href="/zport/dmd/Devices">/</a>'
        """
        return self.urlLink()


    def callZenScreen(self, REQUEST, redirect=False):
        """
        Call and return screen specified by zenScreenName value of REQUEST.
        If zenScreenName is not present call the default screen.  This is used
        in functions that are called from forms to get back to the correct
        screen with the correct context.
        """
        if REQUEST is None or getattr(REQUEST, 'dontRender', False):
            # EventView uses a FakeRequest class to avoid the overhead
            # of rendering pages as result of ajax calls.
            return ''
        screenName = REQUEST.get("zenScreenName", "")
        if not redirect and REQUEST.get("redirect", None) :
            redirect = True
        if redirect:
            nurl = "%s/%s" % (self.getPrimaryUrlPath(), screenName)
            REQUEST['RESPONSE'].redirect(nurl)
        else:
            REQUEST['URL'] = "%s/%s" % (self.absolute_url_path(), screenName)
            screen = getattr(self, screenName, False)
            if not screen: return self()
            return screen()


    @unpublished
    def zenScreenUrl(self):
        """
        Return the url for the current screen as defined by zenScreenName.
        If zenScreenName is not found in the request the request url is used.

        @return: An url to this object
        @rtype: string
        """
        screenName = self.REQUEST.get("zenScreenName", "")
        if not screenName: return self.REQUEST.URL
        return self.getPrimaryUrlPath() + "/" + screenName


    @unpublished
    def urlLink(self, text=None, url=None, attrs={}):
        """
        Return an anchor tag if the user has access to the remote object.

        @param text: the text to place within the anchor tag or string.
                     Defaults to the id of this object.
        @param url: url for the href. Default is getPrimaryUrlPath
        @type attrs: dict
        @param attrs: any other attributes to be place in the in the tag.
        @return: An HTML link to this object
        @rtype: string
        """
        if not text:
            text = self.titleOrId()
        text = escape(text)
        if not self.checkRemotePerm("View", self):
            return text
        if not url:
            url = self.getPrimaryUrlPath()
        if len(attrs):
            return '<a href="%s" %s>%s</a>' % (url,
                ' '.join('%s="%s"' % (x,y) for x,y in attrs.items()),
                text)
        else:
            return '<a href="%s">%s</a>' % (url, text)


    def getBreadCrumbUrlPath(self):
        """
        Return the url to be used in breadcrumbs for this object.  normally
        this is equal to getPrimaryUrlPath. It can be used as a hook to modify
        the url so that it points towards a different tab then the default.

        @return: A url to this object
        @rtype: string

        >>> dmd.Devices.getBreadCrumbUrlPath()
        '/zport/dmd/Devices'
        >>> rc = dmd.Reports._getOb('Graph Reports')
        >>> rc.manage_addGraphReport('test').getBreadCrumbUrlPath()
        '/zport/dmd/Reports/Graph%20Reports/test/editGraphReport'
        """
        return self.getPrimaryUrlPath()


    def getBreadCrumbName(self):
        return self.title_or_id()


    def breadCrumbs(self, terminator='dmd', terminate=lambda x: False):
        """
        Return the data to create the breadcrumb links for this object.

        This is a list of tuples where the first value is the URL of the bread
        crumb and the second is the lable.

        @return: List of tuples to create a bread crumbs
        @rtype: list

        >>> dmd.Devices.Server.breadCrumbs()
        [('/zport/dmd/Devices', 'Devices'),
            ('/zport/dmd/Devices/Server', 'Server')]
        """
        links = []
        curDir = self.primaryAq()
        while curDir.id != terminator and not terminate(curDir):
            if curDir.meta_type == 'ToManyContRelationship':
                curDir = curDir.getPrimaryParent()
                continue
            if not getattr(aq_base(curDir),"getBreadCrumbUrlPath", False):
                break
            url = ""
            if self.checkRemotePerm("View", curDir):
                url = curDir.getBreadCrumbUrlPath()
            links.append((url, curDir.getBreadCrumbName()))
            curDir = curDir.aq_parent
        links.reverse()
        return links


    def upToOrganizerBreadCrumbs(self, terminator='dmd'):

        def isOrganizer(curDir):
            from Products.ZenModel.Organizer import Organizer
            try:
                return isinstance(curDir, Organizer)
            except Exception:
                return False

        return ZenModelBase.breadCrumbs(self, terminator, isOrganizer)


    security.declareProtected(ZEN_COMMON, 'checkRemotePerm')
    def checkRemotePerm(self, permission, robject):
        """
        Look to see if the current user has permission on remote object.

        @param permission: Zope permission to be tested. ie "View"
        @param robject: remote objecct on which test is run.  Will test on
        primary acquisition path.
        @rtype: boolean
        @permission: ZEN_COMMON
        """
        user = getSecurityManager().getUser()
        return user.has_permission(permission, robject.primaryAq())



    security.declareProtected(ZEN_VIEW, 'zentinelTabs')
    def zentinelTabs(self, templateName, REQUEST=None):
        """
        Return a list of hashes that define the screen tabs for this object.

        Keys in the hash are:
            - action = the name of the page template for this tab
            - name = the label used on the tab
            - permissions = a tuple of permissions to view this template

        @permission: ZEN_VIEW

        >>> dmd.Devices.zentinelTabs('deviceOrganizerStatus')
        [{'action': 'deviceOrganizerStatus', 'selected': True,
            'name': 'Classes', 'permissions': ('View',)},
        {'action': 'viewEvents', 'name': 'Events', 'permissions': ('View',)},
        {'action': 'zPropertyEdit', 'name': 'Configuration Properties',
            'permissions': ('View',)},
        {'action': 'perfConfig', 'name': 'Templates',
            'permissions': ('Manage DMD',)}]
        """
        tabs = []
        user = getSecurityManager().getUser()
        actions = self.factory_type_information[0]['actions']
        selectedTabName = self._selectedTabName(templateName, REQUEST)
        for a in actions:
            def permfilter(p): return user.has_permission(p,self)
            permok = filter(permfilter, a['permissions'])
            if not a.get('visible', True) or not permok:
                continue
            a = a.copy()
            if a['action'] == selectedTabName: a['selected'] = True
            tabs.append(a)
        return tabs

    def _selectedTabName(self, templateName, REQUEST=None):
        if REQUEST and REQUEST.get('selectedTabName', '') :
            selectedTabName = REQUEST.get('selectedTabName', '')
        else:
            selectedTabName = templateName
        requestUrl = REQUEST['URL'] if REQUEST else None
        if not selectedTabName and requestUrl and requestUrl.rfind('/') != -1:
            selectedTabName = requestUrl[requestUrl.rfind('/') + 1:]
            if selectedTabName.startswith('@@'):
                selectedTabName = selectedTabName[2:]
        return selectedTabName


    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None, redirect=False, audit=True):
        """
        Edit a ZenModel object and return its proper page template.
        Object will be reindexed if nessesary.

        @permission: ZEN_MANAGE_DMD
        """
        self.manage_changeProperties(**REQUEST.form)
        index_object = getattr(self, 'index_object', lambda self: None)
        index_object()
        if REQUEST:            
            messaging.IMessageSender(self).sendToBrowser(
                'Properties Saved',
                "Saved At: %s" % self.getCurrentUserNowString()
            )

            if audit:
                auditType = getDisplayType(self)
                auditKind = 'Setting' if auditType == 'DataRoot' else auditType
                auditFn(['UI', auditKind, 'Edit'],
                        data_=REQUEST.form,
                        skipFields_=('redirect',
                                'zenScreenName',
                                'zmanage_editProperties',
                                'curpasswd'),
                        maskFields_=('smtpPass'))
            return self.callZenScreen(REQUEST, redirect=redirect)


    security.declareProtected(ZEN_VIEW, 'getPrimaryDmdId')
    def getPrimaryDmdId(self, rootName="dmd", subrel=""):
        """
        Return the full dmd id of this object for instance /Devices/Server.
        Everything before dmd is removed.  A different rootName can be passed
        to stop at a different object in the path.  If subrel is passed any
        relationship name in the path to the object will be removed.

        @param rootName: Name of root
        @type rootName: string
        @param subrel: Name of relation
        @type subrel: string
        @return: Path to object
        @rtype: string
        @permission: ZEN_VIEW
        """
        path = list(self.getPrimaryPath())
        path = path[path.index(rootName)+1:]
        if subrel: path = filter(lambda x: x != subrel, path)
        return '/'+'/'.join(path)


    @unpublished
    def zenpathjoin(self, path):
        """
        DEPRECATED Build a Zenoss path based on a list or tuple.

        @type path: list or tuple

        >>> dmd.zenpathjoin(('zport', 'dmd', 'Devices', 'Server'))
        '/zport/dmd/Devices/Server'
        """
        return zenpathjoin(path)


    def zenpathsplit(self, path):
        """
        DEPRECATED Split a path on its '/'.
        """
        return zenpathsplit(path)


    def createHierarchyObj(self, root, name, factory, relpath="", alog=None):
        """
        DEPRECATED this is only seems to be used in Organizer.createOrganizer -
        Create an object from its path we use relpath to skip down any missing
        relations in the path and factory is the constructor for this object.
        """
        return createHierarchyObj(root, name, factory, relpath, alog)


    @unpublished
    def getHierarchyObj(self, root, name, relpath):
        """
        DEPRECATED this doesn't seem to be used anywere don't use it!!!
        """
        return getHierarchyObj(root, name, relpath)


    def getDmd(self):
        """
        DEPRECATED Return the dmd root object with unwraped acquisition path.

        >>> dmd.Devices.Server.getDmd()
        <DataRoot at /zport/dmd>
        """
        for obj in aq_chain(self):
            if getattr(obj, 'id', None) == 'dmd': return obj


    def getDmdRoot(self, name):
        """
        Return a dmd root organizer such as "Systems".  The acquisition path
        will be cleaned so that it points directly to the root.

        >>> dmd.Devices.Server.getDmdRoot("Systems")
        <System at /zport/dmd/Systems>
        """
        dmd = self.getDmd()
        return dmd._getOb(name)


    def getDmdObj(self, path):
        """
        DEPRECATED Return an object from path that starts at dmd.

        >>> dmd.getDmdObj('/Devices/Server')
        <DeviceClass at /zport/dmd/Devices/Server>
        """
        if path.startswith("/"): path = path[1:]
        return self.getDmd().getObjByPath(path)


    def getZopeObj(self, path):
        """
        DEPRECATED Return an object from path tat starts at zope root.

        >>> dmd.getZopeObj('/zport/dmd/Devices/Server')
        <DeviceClass at /zport/dmd/Devices/Server>
        """
        return self.getObjByPath(path)

    def convertToUsersTimeZone(self, timestamp):
        """
        This is an instance method so that it is available to
        tal statements, such as reports.
        """
        user = self.zport.dmd.ZenUsers.getUserSettings()
        if user.timezone:
            utc_dt = pytz.utc.localize(datetime.utcfromtimestamp(int(timestamp)))
            tz = pytz.timezone(user.timezone)
            tval = tz.normalize(utc_dt.astimezone(tz))
            return tval.strftime(convertJsTimeFormatToPy(user.dateFormat+" "+user.timeFormat))
        return isoDateTime(timestamp)

    def getCurrentUserNowString(self):
        return self.convertToUsersTimeZone(time.time())

    def getNowString(self):
        """
        Return the current time as a string in the format '2007/09/27 14:09:53'.

        @rtype: string
        """
        return time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())


    def todayDate(self):
        """
        Return today's date as a string in the format 'mm/dd/yyyy'.

        @rtype: string
        """
        return time.strftime("%m/%d/%Y", time.localtime())


    def yesterdayDate(self):
        """
        Return yesterday's date as a string in the format 'mm/dd/yyyy'.

        @rtype: string
        """
        yesterday = time.time() - 24*3600
        return time.strftime("%m/%d/%Y", time.localtime(yesterday))


    def all_meta_types(self, interfaces=None):
        """
        DEPRECATED Override the ObjectManager method that is used to control
        the items available in the add drop down in the ZMI.  It uses the
        attribute sub_menu_items to create the data structures.  This is a list
        of meta_types for the available classes.  This functionality is rarely
        used in Zenoss because the ZMI is not the perfered management
        interface.
        """
        mts = super(ZenModelBase,self).all_meta_types(interfaces)
        if self.sub_meta_types:
            mts = filter(lambda mt: mt['name'] in self.sub_meta_types, mts)
        return mts


    security.declareProtected('Delete objects', 'manage_deleteObjects')
    def manage_deleteObjects(self, ids=(), REQUEST=None):
        """
        Delete objects by id from this object and return to the current
        template as defined by callZenScreen.  Uses ObjectManager._delObject to
        remove the object.

        @permission: ZEN_VIEW
        """
        for id in ids:  self._delObject(id)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def custPropertyIds(self):
        """
        List custom properties that are defined at root node. Custom properties
        start with a lower "c" followed by a uppercase character.
        """
        return self.zenPropertyIds(pfilt=iscustprop)


    def custPropertyMap(self):
        """
        Return custom property definitions.

        @rtype: [{'id':'cName','label':'Name', 'type':'string'},]
        """
        return self.zenPropertyMap(pfilt=iscustprop)


    def visibleCustPropertyMap(self):
        """
        List custom property definitions that are visible using
        custPropertyMap::

        @rtype: [{'id':'cName','label':'Name', 'type':'string'},]
        """
        return [ p for p in self.zenPropertyMap(pfilt=iscustprop) \
                    if p.get('visible', True) ]


    security.declareProtected(ZEN_MANAGE_DMD, 'saveCustProperties')
    def saveCustProperties(self, REQUEST):
        """
        Save custom properties from REQUEST.form.

        @permission: ZEN_MANAGE_DMD
        """
        redirect = self.saveZenProperties(iscustprop, REQUEST)
        auditFn(['UI', getDisplayType(self), 'Edit'], self, data_=REQUEST.form,
              skipFields_=('zenScreenName', 'saveCustProperties'))
        return redirect


    def getObjByPath(self, path):
        """
        Lookup and object by its path.  Basically does a Zope unrestricted
        traverse on the path given.

        @type path: list or string /zport/dmd/Devices

        >>> dmd.getObjByPath(('zport','dmd','Devices'))
        <DeviceClass at /zport/dmd/Devices>
        >>> dmd.getObjByPath(('Devices','Server'))
        <DeviceClass at /zport/dmd/Devices/Server>
        >>> dmd.getObjByPath('/zport/dmd/Devices/Server')
        <DeviceClass at /zport/dmd/Devices/Server>
        >>> dmd.getObjByPath('Devices/Server')
        <DeviceClass at /zport/dmd/Devices/Server>
        """
        return getObjByPath(self, path)


    def isLocalName(self, name):
        """
        Check to see if a name is local to our current context or if it comes
        from our acquisition chain.

        @rtype: boolean

        >>> dmd.isLocalName('Devices')
        True
        >>> dmd.Devices.Server.isLocalName('Devices')
        False
        """
        v = getattr(aq_base(self), name, '__ZENMARKER__')
        return v != '__ZENMARKER__'

    security.declareProtected(ZEN_VIEW, 'helpLink')
    def helpLink(self):
        """
        DEPRECATED Return a link to the objects help file.

        @permission: ZEN_VIEW
        """
        path = self.__class__.__module__.split('.')
        className = path[-1].replace('Class','')
        product = path[-2]

        path = ("", "Control_Panel", "Products", product, "Help",
                "%s.stx"%className)

        # check to see if we have a help screen
        app = self.getPhysicalRoot()
        try:
            app.restrictedTraverse(path)
        except (KeyError, Unauthorized):
            return ""

        url = "/HelpSys?help_url="+ "/".join(path)

        return """<a class="tabletitle" href="%s" \
            onClick="window.open('%s','zope_help','width=600,height=500, \
            menubar=yes,toolbar=yes,scrollbars=yes,resizable=yes');  \
            return false;" onMouseOver="window.status='Open online help'; \
            return true;" onMouseOut="window.status=''; return true;">Help!</a>
            """ % (url, url)


    security.declareProtected(ZEN_VIEW, 'getIconPath')
    def getIconPath(self):
        """
        Return the icon associated with this object.  The icon path is defined
        in the zProperty zIcon.

        @return: Path to icon
        @rtype: string
        @permission: ZEN_VIEW
        """
        try:
            return self.primaryAq().zIcon
        except AttributeError:
            return '/zport/dmd/img/icons/noicon.png'


    def aqBaseHasAttr(self, attr):
        """
        Return hasattr(aq_base(self), attr)
        This is a convenience function for use in templates, where it's not
        so easy to make a similar call directly.
        hasattr itself will swallow exceptions, so we don't want to use that.
        We also need to allow for values of None, so something like
        getattr(aq_base(self, attr, None) doesn't really tell us anything.
        Testing __dict__ is not a good choice because it doesn't allow
        for properties (and I believe __getitem__ calls.)
        So while this looks pretty attrocious, it might be the most sane
        solution.
        """
        return getattr(aq_base(self), attr, _MARKER) is not _MARKER

    def get_csrf_token(self):
        """
        Returns string with CSRF token for current user.
        """
        return get_csrf_token(self.REQUEST)


class ZenModelZenDocProvider(object):
    zope.interface.implements(IZenDocProvider)
    zope.component.adapts(ZenModelBase)

    def __init__(self, zenModelBase):
        self._underlyingObject = zenModelBase

    def getZendoc(self):
        zendoc = self._underlyingObject._zendoc
        if not zendoc and self._underlyingObject.aqBaseHasAttr( 'description' ):
            zendoc = self._underlyingObject.description
        return zendoc

    def setZendoc(self, zendocText):
        self._underlyingObject._zendoc = zendocText

    def exportZendoc(self,ofile):
        """Return an xml representation of a RelationshipManagers zendoc
        <property id='_zendoc' type='string' mode='w'>
            value
        </property>
        """
        value = self.getZendoc()
        if not value: return
        ofile.write("<property id='zendoc' type='string'>\n")
        if not isinstance(value, basestring):
            value = unicode(value)
        elif isinstance(value, str):
            value = value.decode('latin-1')
        ofile.write(saxutils.escape(value).encode('utf-8')+"\n")
        ofile.write("</property>\n")


InitializeClass(ZenModelBase)
