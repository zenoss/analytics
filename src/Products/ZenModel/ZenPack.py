##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007,2008,2014 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ZenPack
ZenPacks base definitions
"""

import logging
import datetime
import glob
import json
import string
import subprocess
import os
import os.path
import sys
import shutil
import zipfile

from collections import defaultdict
from StringIO import StringIO

import pkg_resources
import Products

from Acquisition import aq_base
from AccessControl.class_init import InitializeClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import importClass, zenPath, varPath
from Products.ZenUtils.Version import getVersionTupleFromString
from Products.ZenUtils.Version import Version as VersionBase
from Products.ZenUtils.controlplane import ControlPlaneClient, ServiceTree, ControlCenterError
from Products.ZenUtils.controlplane.application import getConnectionSettings
from Products.ZenModel import ExampleLicenses
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenModel.ZenPackLoader import *
from Products.ZenWidgets import messaging
from AccessControl import ClassSecurityInfo
from ZenossSecurity import ZEN_MANAGE_DMD
from Acquisition import aq_parent
from Products.ZenModel.ZVersion import VERSION as ZENOSS_VERSION
from Products.ZenMessaging.audit import audit

import servicemigration
servicemigration.require("1.0.0")

log = logging.getLogger('zen.ZenPack')

class ZenPackException(Exception):
    pass

class ZenPackNotFoundException(ZenPackException):
    pass

class ZenPackDuplicateNameException(ZenPackException):
    pass

class ZenPackNeedMigrateException(ZenPackException):
    pass

class ZenPackDependentsException(ZenPackException):
    pass

class ZenPackDevelopmentModeExeption(ZenPackException):
    pass

class Version(VersionBase):
    def __init__(self, *args, **kw):
        VersionBase.__init__(self, 'Zenoss', *args, **kw)


def needDir(path, perms=0o750):
    if not os.path.isdir(path):
        os.mkdir(path, perms)
    return path

def eliminateDuplicates(objs):
    """
    Given a list of objects, return the sorted list of unique objects
    where uniqueness is based on the getPrimaryPath() results.

    @param objs: list of objects
    @type objs: list of objects
    @return: sorted list of objects
    @rtype: list of objects
    """

    objs.sort(key = lambda x: x.getPrimaryPath())
    result = []
    for obj in objs:
        for alreadyInList in result:
            path = alreadyInList.getPrimaryPath()
            if obj.getPrimaryPath()[:len(path)] == path:
                break
        else:
            result.append(obj)
    return result


class ZenPackMigration:
    """
    Base class for defining migration methods
    """
    version = Version(0, 0, 0)

    def migrate(self, pack):
        """
        ZenPack-specific migrate() method to be overridden

        @param pack: ZenPack object
        @type pack: ZenPack object
        """
        pass

    def recover(self, pack):
        """
        ZenPack-specific recover() method to be overridden

        @param pack: ZenPack object
        @type pack: ZenPack object
        """
        pass




class ZenPackDataSourceMigrateBase(ZenPackMigration):
    """
    Base class for ZenPack migrate steps that need to switch classes of
    datasources and reindex them.  This is frequently done in migrate
    scripts for 2.2 when ZenPacks are migrated to python eggs.
    """
    # dsClass is the actual class of the datasource provided by this ZenPack
    dsClass = None
    # These are the names of the module and the class of the datasource as
    # provided by previous versios of this ZenPack.  If these are provided
    # then any instances of them will be converted to instances of dsClass.
    oldDsModuleName = ''
    oldDsClassName = ''
    # If reIndex is True then any instances of dsClass are reindexed.
    reIndex = False

    def migrate(self, pack):
        """
        Attempt to import oidDsModuleName and then any templates

        @param pack: ZenPack object
        @type pack: ZenPack object
        """
        if self.oldDsModuleName and self.oldDsClassName and self.dsClass:
            try:
                exec('import %s' % self.oldDsModuleName)
                oldClass = eval('%s.%s' % (self.oldDsModuleName,
                                            self.oldDsClassName))
            except ImportError:
                # The old-style code no longer exists in Products,
                # so we assume the migration has already happened.
                oldClass = None

        from Products.ZenModel.RRDTemplate import YieldAllRRDTemplates
        for template in YieldAllRRDTemplates(pack.dmd, None):
            for ds in template.datasources():
                if oldClass and self.dsClass and isinstance(ds, oldClass):
                    ds.__class__ = self.dsClass
                if self.reIndex and isinstance(ds, self.dsClass):
                    ds.index_object()


class DirectoryConfigContents(object):
    """
    Map-like object which, given a key consisting of an absolute path, returns
    the contents of the file at that location relative to some root.  e.g., if
    the contents of /foo/bar/baz/qux is 'barge', then
        DirectoryConfigContents('/foo/bar')['/baz/qux'] == 'barge'
    """
    def __init__(self, path):
        self._path = path
    def __getitem__(self, key):
        try:
            return open(os.path.join(self._path, key.lstrip('/'))).read()
        except Exception:
            raise KeyError(key)


class ZenPack(ZenModelRM):
    """
    The root of all ZenPacks: has no implementation,
    but sits here to be the target of the Relation
    """

    objectPaths = None

    # Metadata
    version = '0.1'
    author = ''
    organization = ''
    url = ''
    license = ''
    compatZenossVers = ''
    prevZenPackName = ''
    prevZenPackVersion = None

    # Control Center service ID for container executing this installation
    currentServiceId = ""

    # Whether or not to skip control center service mutation at install time
    ignoreServiceInstall = False

    # New-style zenpacks (eggs) have this set to True when they are
    # first installed
    eggPack = False

    installableFromUI = True

    requires = () # deprecated

    loaders = (ZPLObject(), ZPLReport(), ZPLDaemons(), ZPLBin(), ZPLLibExec(),
                ZPLSkins(), ZPLDataSources(), ZPLLibraries(), ZPLAbout(),
                ZPTriggerAction(), ZPZep())

    _properties = ZenModelRM._properties + (
        {'id':'objectPaths','type':'lines','mode':'w'},
        {'id':'version', 'type':'string', 'mode':'w', 'description':'ZenPack version'},
        {'id':'author', 'type':'string', 'mode':'w', 'description':'ZenPack author'},
        {'id':'organization', 'type':'string', 'mode':'w',
              'description':'Sponsoring organization for the ZenPack'},
        {'id':'url', 'type':'string', 'mode':'w', 'description':'Homepage for the ZenPack'},
        {'id':'license', 'type':'string', 'mode':'w',
              'description':'Name of the license under which this ZenPack is available'},
        {'id':'compatZenossVers', 'type':'string', 'mode':'w',
              'description':'Which Zenoss versions can load this ZenPack'},
    )

    _relations =  (
        # root is deprecated, use manager now instead
        # root should be removed post zenoss 2.2
        ('root', ToOne(ToManyCont, 'Products.ZenModel.DataRoot', 'packs')),
        ('manager',
            ToOne(ToManyCont, 'Products.ZenModel.ZenPackManager', 'packs')),
        ("packables", ToMany(ToOne, "Products.ZenModel.ZenPackable", "pack")),
        )

    factory_type_information = (
        { 'immediate_view' : 'viewPackDetail',
          'factory'        : 'manage_addZenPack',
          'actions'        :
          (
           { 'id'            : 'viewPackDetail'
             , 'name'          : 'Detail'
             , 'action'        : 'viewPackDetail'
             , 'permissions'   : ( "Manage DMD", )
             },
           )
          },
        )

    packZProperties = []
    packZProperties_data = {}

    security = ClassSecurityInfo()

    @classmethod
    def getZProperties(cls):
        """Return dict of zProperties added by this ZenPack.

        packZProperties and packZProperties_data will be merged into the result
        with packZProperties winning when they disagree on type or
        defaultValue.

        Example result:

            {
                'zMyZenPackProperty': {
                    'type': 'string',
                    'defaultValue': '',
                    'category': 'Mine',
                    'label': 'My Simple Property',
                    'description': 'Set this to any value.'
                }
            }

        """
        pack_zproperties = {}
        for p_id, p_value, p_type in cls.packZProperties:
            pack_zproperties[p_id] = {
                'type': p_type,
                'defaultValue': p_value,
                }

        for p_id, p_data in cls.packZProperties_data.items():
            if p_id not in pack_zproperties:
                if 'type' not in p_data or 'defaultValue' not in p_data:
                    log.error(
                        "%s: type or defaultValue not set for %s property",
                        cls.__module__,
                        p_id)

                    continue

                pack_zproperties[p_id] = {
                    'type': p_data['type'],
                    'defaultValue': p_data['defaultValue'],
                    }

            for p_data_key, p_data_value in p_data.items():
                pack_zproperties[p_id].setdefault(
                    p_data_key, p_data_value)

        return pack_zproperties

    def __init__(self, id, title=None, buildRelations=True):
        #self.dependencies = {'zenpacksupport':''}
        self.dependencies = {}
        ZenModelRM.__init__(self, id, title, buildRelations)

    def install(self, app):
        """
        Stop daemons, load any loaders, create zProperties, migrate and start daemons

        @param app: ZenPack
        @type app: ZenPack object
        """
        for loader in self.loaders:
            loader.load(self, app)
        self.createZProperties(app)
        previousVersion = self.prevZenPackVersion
        self.storeBackup()
        self.migrate(previousVersion)
        if not ZenPack.ignoreServiceInstall and previousVersion is None:
            self.installServices()

    def storeBackup(self):
        """
        makes a backup of the zenpack src to allow restoring broken zenpacks
        """
        backupDir = zenPath(".ZenPacks")
        if not os.path.isdir(backupDir):
            os.makedirs(backupDir, 0o750)

        src = self.eggPath()
        filename = ""
        zip = None
        try:
            if src.lower().endswith(".egg"):
                filename = os.path.join(backupDir, os.path.basename(src))
                zip = zipfile.ZipFile(filename+".tmp", "w")
                prefix = ""
            else:
                filename = os.path.join(backupDir, "%s-%s.zip" % (self.id, self.version))
                zip = zipfile.ZipFile(filename+".tmp", "w")
                prefix = self.id
            ignore = len(src) + 1
            for root, dirs, files in os.walk(src):
                for file in files:
                    f = os.path.join(root, file)
                    archivename = os.path.join(prefix, f[ignore:])
                    zip.write(f, archivename)
            zip.close()
            zip = None
            os.rename(filename+".tmp", filename)
        finally:
            if zip:
                zip.close()
            if filename and os.path.exists(filename+".tmp"):
                os.remove(filename+".tmp")

    def upgrade(self, app):
        """
        This is essentially an install() call except that a different method
        is called on the loaders.
        NB: Newer ZenPacks (egg style) do not use this upgrade method.  Instead
        the proper method is to remove(leaveObjects=True) and install again.
        See ZenPackCmd.InstallDistAsZenPack().

        @param app: ZenPack
        @type app: ZenPack object
        """
        for loader in self.loaders:
            loader.upgrade(self, app)
        self.createZProperties(app)
        self.migrate()

    def doServiceAction(self, tag, action):
        """
        Process all services matching tag from Control Center

        :param tag: tag for which all services will be processed
        :type tag: string
        """
        if not ZenPack.currentServiceId:
            return

        cpClient = ControlPlaneClient(**getConnectionSettings())
        services = cpClient.queryServices("*")
        serviceTree = ServiceTree(services)
        serviceRoots = serviceTree.matchServicePath(ZenPack.currentServiceId, '/')
        for root in serviceRoots:
            services = serviceTree.findMatchingServices(root, tag)
            # Ensure that child services are processed before parents
            services.sort(key=lambda x:len(serviceTree.getPath(x)), reverse=True)
            for service in services:
                if action == 'stop':
                    cpClient.stopService(service.id)
                elif action == 'delete':
                    cpClient.deleteService(service.id)

    def remove(self, app, leaveObjects=False):
        """
        This prepares the ZenPack for removal but does not actually remove
        the instance from ZenPackManager.packs  This is sometimes called during
        the course of an upgrade where the loaders' unload methods need to
        be run.

        @param app: ZenPack
        @type app: ZenPack object
        @param leaveObjects: remove zProperties and things?
        @type leaveObjects: boolean
        """
        serviceTag = self.getServiceTag()
        if not leaveObjects:
            self.doServiceAction(serviceTag, 'stop')
        for loader in self.loaders:
            loader.unload(self, app, leaveObjects)
        if not leaveObjects:
            self.removeZProperties(app)
            self.removeCatalogedObjects(app)
            self.doServiceAction(serviceTag, 'delete')

    def backup(self, backupDir, logger):
        """
        Method called when zenbackup is run. Override in ZenPack to add any
        ZenPack-specific backup operations.

        @param backupDir: Temporary directory that gets zipped to form backup
        @type backupDir: string
        @param logger: Backup log handler
        @type logger: Log object
        """
        pass

    def restore(self, backupDir, logger):
        """
        Method called when zenrestore is run. Override in ZenPack to add any
        ZenPack-specific restore operations.

        @param backupDir: Temporary directory that contains the unzipped backup
        @type backupDir: string
        @param logger: Restore log handler
        @type logger: Log object
        """
        pass


    def migrate(self, previousVersion=None):
        """
        Migrate to a new version

        @param previousVersion: previous version number
        @type previousVersion: string
        """
        instances = []
        # find all the migrate modules
        root = self.path("migrate")
        for p, ds, fs in os.walk(root):
            for f in fs:
                if f.endswith('.py') and not f.startswith("__"):
                    path = os.path.join(p[len(root) + 1:], f)
                    log.debug("Loading %s", path)
                    sys.path.insert(0, p)
                    try:
                        try:
                            c = importClass(path[:-3].replace("/", "."))
                            instances.append(c())
                        finally:
                            sys.path.remove(p)
                    except ImportError as ex:
                        log.exception("Problem loading migration step %s", path)
        # sort them by version number
        instances.sort(key = lambda x: x.version)
        # install those that are newer than previous or our pack version
        migrateCutoff = getVersionTupleFromString(self.version)
        if previousVersion:
            migrateCutoff = getVersionTupleFromString(previousVersion)
        recover = []

        try:
            for instance in instances:
                if instance.version.tuple() >= migrateCutoff:
                    recover.append(instance)
                    instance.migrate(self)
        except Exception as ex:
            # give the pack a chance to recover from problems
            recover.reverse()
            for r in recover:
                r.recover(self)
            raise


    def list(self, app):
        """
        Show the list of loaders

        @param app: ZenPack
        @type app: ZenPack object
        @return: list of loaders
        @rtype: list of objects
        """
        result = []
        for loader in self.loaders:
            result.append((loader.name,
                           [item for item in loader.list(self, app)]))
        return result

    def register_portlets(self):
        """
        Registers ExtJS portlets from a ZenPack. Override in ZenPack. ID and
        title are required, height and permissions are optional. See
        ZenWidgets.PortletManager.register_extjsPortlet.

        @return: List of dictionary objects describing a portlet
        @rtype: List of dicts
        """
        return []

    def createZProperties(self, app):
        """
        Create zProperties in the ZenPack's self.getZProperties().

        @param app: ZenPack
        @type app: ZenPack object
        """
        # for brand new installs, define an instance for each of the zenpacks
        # zprops on dmd.Devices
        for name, data in self.getZProperties().items():
            if not app.zport.dmd.Devices.hasProperty(name):
                app.zport.dmd.Devices._setProperty(
                    name,
                    data.get('defaultValue', ''),
                    data.get('type', 'string'))


    def removeZProperties(self, app):
        """
        Remove any zProperties defined in the ZenPack

        @param app: ZenPack
        @type app: ZenPack object
        """
        for name in self.getZProperties():
            if app.zport.dmd.Devices.hasProperty(name):
                app.zport.dmd.Devices._delProperty(name)


    def removeCatalogedObjects(self, app):
        """
        Delete all objects in the zenPackPersistence catalog that are
        associated with this zenpack.

        @param app: ZenPack
        @type app: ZenPack object
        """
        objects = self.getCatalogedObjects()
        for o in objects:
            parent = aq_parent(o)
            if parent:
                parent._delObject(o.id)


    def getCatalogedObjects(self):
        """
        Return a list of objects from the ZenPackPersistence catalog
        for this zenpack.
        """
        from ZenPackPersistence import GetCatalogedObjects
        return GetCatalogedObjects(self.dmd, self.id) or []


    security.declareProtected(ZEN_MANAGE_DMD, 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST, redirect=False):
        """
        Edit a ZenPack object
        """

        if self.isEggPack():
            # Handle the dependencies fields and recreate self.dependencies
            newDeps = {}
            depNames = REQUEST.get('dependencies', [])
            if not isinstance(depNames, list):
                depNames = [depNames]
            newDeps = {}
            for depName in depNames:
                fieldName = 'version_%s' % depName
                vers = REQUEST.get(fieldName, '').strip()
                if vers and vers[0] in string.digits:
                    vers = '==' + vers
                try:
                    req = pkg_resources.Requirement.parse(depName + vers)
                except ValueError:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        '%s is not a valid version specification.' % vers,
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                zp = self.dmd.ZenPackManager.packs._getOb(depName, None)
                if not zp:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        '%s is not installed.' % depName,
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                if not req.__contains__(zp.version):
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        ('The required version for %s (%s) ' % (depName, vers) +
                        'does not match the installed version (%s).' %
                         zp.version),
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                newDeps[depName] = vers
                REQUEST.form[fieldName] = vers
            self.dependencies = newDeps
            # Check the value of compatZenossVers and the dependencies to
            # make sure that they match installed versions
            compatZenossVers = REQUEST.form['compatZenossVers'] or ''
            if compatZenossVers:
                if compatZenossVers[0] in string.digits:
                    compatZenossVers = '==' + compatZenossVers
                try:
                    req = pkg_resources.Requirement.parse(
                                                'zenoss%s' % compatZenossVers)
                except ValueError:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        ('%s is not a valid version specification for Zenoss.'
                                                        % compatZenossVers),
                        priority=messaging.WARNING
                    )
                if not req.__contains__(ZENOSS_VERSION):
                    messaging.IMessageSender(self).sendToBrowser(
                        'Error',
                        ('%s does not match this version of Zenoss (%s).' %
                            (compatZenossVers, ZENOSS_VERSION)),
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)
                REQUEST.form['compatZenossVers'] = compatZenossVers

        if 'Select or specify your own' in REQUEST.get('license', ''):
            REQUEST.form['license'] = ''

        result =  ZenModelRM.zmanage_editProperties(self, REQUEST, redirect,
                audit=False)
        audit('UI.ZenPack.Edit',
                self.id,
                data_=REQUEST.form,
                skipFields_=('redirect',
                        'zenScreenName',
                        'zmanage_editProperties'))

        if self.isEggPack():
            self.writeSetupValues()
            self.writeLicense()
            self.buildEggInfo()
        return result


    def manage_deletePackable(self, packables=(), REQUEST=None):
        "Delete objects from this ZenPack"
        packables = set(packables)
        for obj in self.packables():
            if obj.getPrimaryUrlPath() in packables:
                self.packables.removeRelation(obj)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Objects Deleted',
                'Deleted objects from ZenPack %s.' % self.id
            )
            return self.callZenScreen(REQUEST)


    def manage_uploadPack(self, znetProject, description, REQUEST=None):
        """
        Create a new release of the given project.
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd
        userSettings = self.dmd.ZenUsers.getUserSettings()
        ZenPackCmd.UploadZenPack(self.dmd, self.id, znetProject, description,
            userSettings.zenossNetUser, userSettings.zenossNetPassword)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'ZenPack Uploaded',
                'ZenPack uploaded to Zenoss.net.'
            )
            return self.callZenScreen(REQUEST)


    def exportToSeparateFile(self, obj, subdir):
        xml = StringIO()
        xml.write("""<?xml version="1.0"?>\n""")
        xml.write("<objects>\n")
        xml.write('<!-- %r -->\n' % (obj.getPrimaryPath(),))
        obj.exportXml(xml,['devices','networks','pack'],True)
        xml.write("</objects>\n")

        path = needDir(self.path('objects/%s' % subdir))
        filename = '%s.xml' % '_'.join(obj.getPrimaryPath()[3:])

        objects = file(os.path.join(path, filename), 'w')
        objects.write(xml.getvalue())
        objects.close()


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_exportPack')
    def manage_exportPack(self, download="no", REQUEST=None):
        """
        Export the ZenPack to the /export directory

        @param download: download to client's desktop? ('yes' vs anything else)
        @type download: string
        @type download: string
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        @todo: make this more modular
        @todo: add better XML headers
        """
        if not self.isDevelopment():
            msg = 'Only ZenPacks installed in development mode can be exported.'
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                        'Error', msg, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
            raise ZenPackDevelopmentModeExeption(msg)

        path = needDir(self.path('objects'))

        xml = StringIO()
        # Write out packable objects
        # TODO: When the DTD gets created, add the reference here
        xml.write("""<?xml version="1.0"?>\n""")
        xml.write("<objects>\n")

        packables = eliminateDuplicates(self.packables())
        for obj in packables:
            if type(aq_base(obj)) in [RRDTemplate]:
                self.exportToSeparateFile(obj, 'templates')
            else:
                xml.write('<!-- %r -->\n' % (obj.getPrimaryPath(),))
                obj.exportXml(xml,['devices','networks','pack','rrdTemplates'],True)
                if type(aq_base(obj)) in [DeviceClass]:
                    for tpl in obj.getAllRRDTemplates():
                        self.exportToSeparateFile(tpl, 'templates')

        xml.write("</objects>\n")

        objects = file(os.path.join(path, 'objects.xml'), 'w')
        objects.write(xml.getvalue())
        objects.close()

        # Create skins dir if not there
        needDir(self.path('skins'))

        # Create __init__.py
        init = self.path('__init__.py')
        if not os.path.isfile(init):
            fp = file(init, 'w')
            fp.write(
'''
from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory("skins", globals())
''')
            fp.close()

        if self.isEggPack():
            # Create the egg
            exportDir = needDir(zenPath('export'))
            eggPath = self.eggPath()
            os.chdir(eggPath)
            for tmp_dir in ['build', 'dist']:
                if os.path.isdir(os.path.join(eggPath, tmp_dir)):
                    os.system('rm -rf {}/*'.format(tmp_dir))
            p = subprocess.Popen('python setup.py bdist_egg',
                            stderr=sys.stderr,
                            shell=True,
                            cwd=eggPath)
            p.wait()
            os.system('cp dist/* %s' % exportDir)
            exportFileName = self.eggName()
        else:
            # Create about.txt
            about = self.path(CONFIG_FILE)
            values = {}
            parser = ConfigParser.SafeConfigParser()
            if os.path.isfile(about):
                try:
                    parser.read(about)
                    values = dict(parser.items(CONFIG_SECTION_ABOUT))
                except ConfigParser.Error:
                    pass
            current = [(p['id'], str(getattr(self, p['id'], '') or ''))
                        for p in self._properties]
            values.update(dict(current))
            if not parser.has_section(CONFIG_SECTION_ABOUT):
                parser.add_section(CONFIG_SECTION_ABOUT)
            for key, value in values.items():
                parser.set(CONFIG_SECTION_ABOUT, key, value)
            fp = file(about, 'w')
            try:
                parser.write(fp)
            finally:
                fp.close()
            # Create the zip file
            path = needDir(zenPath('export'))
            from zipfile import ZipFile, ZIP_DEFLATED
            zipFilePath = os.path.join(path, '%s.zip' % self.id)
            zf = ZipFile(zipFilePath, 'w', ZIP_DEFLATED)
            base = Products.__path__[-1]
            for p, ds, fd in os.walk(self.path()):
                if p.split('/')[-1].startswith('.'): continue
                for f in fd:
                    if f.startswith('.'): continue
                    if f.endswith('.pyc'): continue
                    filename = os.path.join(p, f)
                    zf.write(filename, filename[len(base)+1:])
                ds[:] = [d for d in ds if d[0] != '.']
            zf.close()
            exportFileName = '%s.zip' % self.id

        audit('UI.ZenPack.Export', exportFileName)

        if REQUEST:
            dlLink = '- <a target="_blank" href="%s/manage_download">' \
                     'Download Zenpack</a>' % self.absolute_url_path()
            messaging.IMessageSender(self).sendToBrowser(
                'ZenPack Exported',
                'ZenPack exported to $ZENHOME/export/%s %s' %
                        (exportFileName, dlLink if download == 'yes' else ''),
                messaging.CRITICAL if download == 'yes' else messaging.INFO
            )
            return self.callZenScreen(REQUEST)

        return exportFileName

    def manage_download(self, REQUEST):
        """
        Download the already exported zenpack from $ZENHOME/export

        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        """
        if self.isEggPack():
            filename = self.eggName()
        else:
            filename = '%s.zip' % self.id
        path = os.path.join(zenPath('export'), filename)
        if os.path.isfile(path):
            REQUEST.RESPONSE.setHeader('content-type', 'application/zip')
            REQUEST.RESPONSE.setHeader('content-disposition',
                                        'attachment; filename=%s' %
                                        filename)
            zf = file(path, 'r')
            try:
                REQUEST.RESPONSE.write(zf.read())
            finally:
                zf.close()
        else:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                'An error has occurred. The ZenPack could not be exported.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)


    def _getClassesByPath(self, name):
        dsClasses = []
        for path, dirs, files in os.walk(self.path(name)):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if not f.startswith('.') \
                        and f.endswith('.py') \
                        and not f == '__init__.py':
                    subPath = path[len(self.path()):]
                    parts = subPath.strip('/').split('/')
                    parts.append(f[:f.rfind('.')])
                    modName = '.'.join([self.moduleName()] + parts)
                    dsClasses.append(importClass(modName))
        return dsClasses

    def getDataSourceClasses(self):
        return self._getClassesByPath('datasources')

    def getThresholdClasses(self):
        return self._getClassesByPath('thresholds')

    def getFilenames(self):
        """
        Get the filenames of a ZenPack exclude .svn, .pyc and .xml files
        """
        filenames = []
        for root, dirs, files in os.walk(self.path()):
            if root.find('.svn') == -1:
                    for f in files:
                        if not f.endswith('.pyc') \
                        and not f.endswith('.xml'):
                            filenames.append('%s/%s' % (root, f))
        return filenames


    def getDaemonPath(self):
        """
        Returns the directory in which daemons are located
        @return: string
        """
        return os.path.join(self.path(), 'daemons')


    def getDaemonNames(self):
        """
        Return a list of daemons in the daemon subdirectory that should be
        stopped/started before/after an install or an upgrade of the zenpack.
        """
        daemonsDir = self.getDaemonPath()
        if os.path.isdir(daemonsDir):
            daemons = [f for f in os.listdir(daemonsDir)
                        if os.path.isfile(os.path.join(daemonsDir,f))]
        else:
            daemons = []
        return daemons


    def stopDaemons(self):
        """
        Stop all the daemons provided by this pack.
        Called before an upgrade or a removal of the pack.
        """
        for d in self.getDaemonNames():
            self.About.doDaemonAction(d, 'stop')


    def startDaemons(self):
        """
        Start all the daemons provided by this pack.
        Called after an upgrade or an install of the pack.
        """
        for d in self.getDaemonNames():
            self.About.doDaemonAction(d, 'start')


    def restartDaemons(self):
        """
        Restart all the daemons provided by this pack.
        Called after an upgrade or an install of the pack.
        """
        for d in self.getDaemonNames():
            self.About.doDaemonAction(d, 'restart')


    def path(self, *parts):
        """
        Return the path to the ZenPack module.
        It would be convenient to store the module name/path in the zenpack
        object, however this would make things more complicated when the
        name of the package under ZenPacks changed on us (do to a user edit.)
        """
        if self.isEggPack():
            module = self.getModule()
            return os.path.join(module.__path__[0], *[p.strip('/') for p in parts])
        return os.path.join(Products.__path__[-1], self.id, *parts)


    def isDevelopment(self):
        """
        Return True if
        1) the pack is an old-style ZenPack (not a Python egg)
        or
        2) the pack is a Python egg and is a source install (includes a
        setup.py file)

        Returns False otherwise.
        """
        if self.isEggPack():
            return os.path.isfile(self.eggPath('setup.py'))
        return True


    def isEggPack(self):
        """
        Return True if this is a new-style (egg) zenpack, false otherwise
        """
        return self.eggPack


    def moduleName(self):
        """
        Return the importable dotted module name for this zenpack.
        """
        if self.isEggPack():
            name = self.getModule().__name__
        else:
            name = 'Products.%s' % self.id
        return name


    def installConfFile(self, filename):
        """
        Helper to install configuration files under "etc/".
        Typcially they should not be deleted on uninstall.
        """
        filepath = 'etc/' + filename
        self.installFile(filepath, overwriteIfExists=False)
        self.installFile(filepath, filepath + '.example', overwriteIfExists=True)


    def installBinFile(self, filename):
        """
        Helper to install script files under "bin/".
        Typically they should be deleted on uninstall with removeBinFile().
        """
        filepath = 'bin/' + filename
        self.installFile(filepath, overwriteIfExists=True, symLink=True)


    def removeBinFile(self, filename):
        filepath = 'bin/' + filename
        self.removeFile(filepath)


    def installFile(self, relativePath, relativeDestPath=None,
                    overwriteIfExists=True, symLink=False):
        """
        Install a file from this zenpack to ZENHOME upon installation.
        By default, relativePath is for the zenpack and its ZENHOME destination.
        Returns True if installed, False/Exception otherwise.

        Example: self.installFile('etc/myzenpack.data')
        """
        srcPath = self.path(relativePath)
        destPath = zenPath(relativePath) if relativeDestPath is None \
                                         else zenPath(relativeDestPath)

        if not overwriteIfExists and os.path.lexists(destPath):
            return False
        if not os.path.exists(srcPath):
            raise ZenPackException('Missing source file %s' % srcPath)
        if os.path.lexists(destPath):
            os.remove(destPath)
            # If the file is open for edit in Unix then it'll still exist
            # until it's closed, which means we can't overwrite it.
            if os.path.lexists(destPath):
                raise ZenPackException('Failed to remove file %s' % destPath)
        if symLink:
            os.symlink(srcPath, destPath)
        else:
            shutil.copy2(srcPath, destPath)
        if not os.path.lexists(destPath):
            raise ZenPackException('Failed to write file %s' % destPath)
        return True


    def removeFile(self, relativePath, mustSucceed=False):
        """
        Remove a file installed in ZENHOME by this zenpack, if it exists.

        Example: self.removeFile('etc/myzenpack.data')
        """
        destPath = zenPath(relativePath)
        if os.path.lexists(destPath):
            os.remove(destPath)
            if mustSucceed and os.path.lexists(destPath):
                raise ZenPackException('Failed to remove file %s' % destPath)


    ##########
    # Egg-related methods
    # Nothing below here should be called for old-style zenpacks
    ##########


    def writeSetupValues(self):
        """
        Write appropriate values to the setup.py file
        """
        import Products.ZenUtils.ZenPackCmd as ZenPackCmd
        if not self.isEggPack():
            raise ZenPackException('Calling writeSetupValues on non-egg zenpack.')
        # I don't think we need to specify packages anymore now that we are
        # using find_packages() in setup.py
        packages = []
        parts = self.id.split('.')
        for i in range(len(parts)):
            packages.append('.'.join(parts[:i+1]))

        attrs = dict(
            NAME=self.id,
            VERSION=self.version,
            AUTHOR=self.author,
            LICENSE=self.license,
            NAMESPACE_PACKAGES=packages[:-1],
            PACKAGES = packages,
            INSTALL_REQUIRES = ['%s%s' % d for d in self.dependencies.items()],
            COMPAT_ZENOSS_VERS = self.compatZenossVers,
            PREV_ZENPACK_NAME = self.prevZenPackName,
            )
        ZenPackCmd.WriteSetup(self.eggPath('setup.py'), attrs)

    def writeLicense(self):
        """
        Write LICENSE.txt file based on the ZenPack's license attribute.
        """
        if self.license not in ExampleLicenses.LICENSES:
            return

        license_text = ExampleLicenses.LICENSES[self.license] % {
            'year': datetime.date.today().year,
            'author': self.author and self.author or '<AUTHOR>',
            }

        with open(self.path('LICENSE.txt'), 'w') as license_file:
            license_file.write(license_text.lstrip('\n'))

    def buildEggInfo(self):
        """
        Rebuild the egg info to update dependencies, etc
        """
        p = subprocess.Popen('python setup.py egg_info',
                        stderr=sys.stderr,
                        shell=True,
                        cwd=self.eggPath())
        p.wait()


    def getDistribution(self):
        """
        Return the distribution that provides this zenpack
        """
        if not self.isEggPack():
            raise ZenPackException('Calling getDistribution on non-egg zenpack.')
        return pkg_resources.get_distribution(self.id)


    def getEntryPoint(self):
        """
        Return a tuple of (packName, packEntry) that comes from the
        distribution entry map for zenoss.zenopacks.
        """
        if not self.isEggPack():
            raise ZenPackException('Calling getEntryPoints on non-egg zenpack.')
        dist = self.getDistribution()
        entryMap = pkg_resources.get_entry_map(dist, 'zenoss.zenpacks')
        if not entryMap or len(entryMap) > 1:
            raise ZenPackException('A ZenPack egg must contain exactly one'
                    ' zenoss.zenpacks entry point.  This egg appears to contain'
                    ' %s such entry points.' % len(entryMap))
        packName, packEntry = entryMap.items()[0]
        return (packName, packEntry)


    def getModule(self):
        """
        Get the loaded module from the given entry point.  if not packEntry
        then retrieve it.
        """
        if not self.isEggPack():
            raise ZenPackException('Calling getModule on non-egg zenpack.')
        _, packEntry = self.getEntryPoint()
        return packEntry.load()


    def eggPath(self, *parts):
        """
        Return the path to the egg supplying this zenpack
        """
        if not self.isEggPack():
            raise ZenPackException('Calling eggPath on non-egg zenpack.')
        d = self.getDistribution()
        return os.path.join(d.location, *[p.strip('/') for p in parts])


    def eggName(self):
        if not self.isEggPack():
            raise ZenPackException('Calling eggName on non-egg zenpack.')
        d = self.getDistribution()
        return d.egg_name() + '.egg'


    def shouldDeleteFilesOnRemoval(self):
        """
        Return True if the egg itself should be deleted when this ZenPack
        is removed from Zenoss.
        If the ZenPack code resides in $ZENHOME/ZenPacks then it is
        deleted, otherwise it is not.
        """
        eggPath = self.eggPath()
        oneFolderUp = eggPath[:eggPath.rfind('/')]
        if oneFolderUp == zenPath('ZenPacks'):
            delete = True
        else:
            delete = False
        return delete


    def getPackageName(self):
        """
        Return the name of submodule of zenpacks that contains this zenpack.
        """
        if not self.isEggPack():
            raise ZenPackException('Calling getPackageName on a non-egg '
                                        'zenpack')
        modName = self.moduleName()
        return modName.split('.')[1]


    def getEligibleDependencies(self):
        """
        Return a list of installed zenpacks that could be listed as
        dependencies for this zenpack
        """
        result = []
        for zp in self.dmd.ZenPackManager.packs():
            try:
                if zp.id != self.id and zp.isEggPack():
                    result.append(zp)
            except AttributeError:
               pass
        return result


    def isInZenPacksDir(self):
        """
        Return True if the egg is located in the ZenPacks directory,
        False otherwise.
        """
        zpDir = zenPath('ZenPacks') + '/'
        eggDir = self.eggPath()
        return eggDir.startswith(zpDir)


    def isBroken(self):
        """
        Make sure that the ZenPack can be instantiated and that it
        is physically present on the filesystem.
        """
        # Well, if zope has an object to call this method on then
        # we know that it can be instantiated.  Templates will need
        # to catch the case where a broken object won't have an isBroken
        # method.
        # So here we just need to check for presence on the filesystem.
        try:
            if not os.path.isdir(self.path()):
                return True
        except pkg_resources.DistributionNotFound:
            return True

        # If packables throws an exception the pack is broken.
        try:
            unused = self.packables()
        except Exception:
            return True

        return False


    def getServiceTag(self):
        """
        The tag to be applied to all services associated with this ZenPack.
        This routine can be overridden to use a custom tag.
        :rtype string
        """
        return self.moduleName()


    def getServiceDefinitionFiles(self):
        """
        Returns a list of files containing services to be installed.

        This routine can be overridden in order to supply a non-standard list of
         files. See installServicesFromFiles() for file format.
        :returns: absolute file paths
        :rtype: list of strings
        """
        return glob.glob(self.path('service_definition', '*.json'))


    def installServices(self):
        """
        Install Control Center services for this ZenPack
        @return: None
        """
        if not ZenPack.currentServiceId:
            return
        if self.getServiceDefinitionFiles():
            sdFiles = self.getServiceDefinitionFiles()
            toConfigPath = lambda x: os.path.join(os.path.dirname(x),'-CONFIGS-')
            configFileMaps = [DirectoryConfigContents(toConfigPath(i)) for i in sdFiles]
            self.installServicesFromFiles(sdFiles, configFileMaps, self.getServiceTag())
        elif self.getDaemonNames():
            import Products.ZenModel as _zm
            templatefile = os.path.join(
                os.path.dirname(_zm.__file__), "data", "default_service.json"
            )
            with open(templatefile) as tf:
                template = tf.read()
            daemonPaths = glob.glob(os.path.join(self.getDaemonPath(), '*'))
            self.installDefaultCollectorServices(daemonPaths,
                                                 template,
                                                 self.getServiceTag())

    @staticmethod
    def normalizeService(service, configMap, tag):
        """
        Applies default actions to a service definition

        @param service: service definition
        @type service: dict
        @param configMap: maps configfile name to contents
        @type configMap:dict string->string
        @param tag: tag to be applied to all services
        @type tag: string
        @return:
        """
        import Products.ZenModel as _zm

        service.setdefault('Tags', []).append(tag)
        if 'ImageID' in service and service['ImageID'] == '':
            service['ImageID'] = os.environ['SERVICED_SERVICE_IMAGE']
        for key, value in service.get('ConfigFiles', dict()).items():
            if value.get('Content', '') == '':
                try:
                    value['Content'] = configMap[key]
                except KeyError:
                    pass

        defaultLogConfigsTemplateFile = os.path.join(
            os.path.dirname(_zm.__file__),
            "data",
            "default_service_logconfigs.json"
        )
        with open(defaultLogConfigsTemplateFile) as tf:
            defaultLogConfigsTemplate = tf.read()
        defaultLogConfigs = json.loads(defaultLogConfigsTemplate % {'zenhome': zenPath()})
        logConfigs = service.setdefault('LogConfigs', [])
        logConfigs.extend(lc for lc in defaultLogConfigs if lc not in logConfigs)
        return service

    def templateParams(self):
        # Get 'Context' from root service
        cpClient = ControlPlaneClient(**getConnectionSettings())
        serviceTree = ServiceTree(cpClient.queryServices("*"))
        tenant = serviceTree.matchServicePath(ZenPack.currentServiceId, '/')[0]
        context = tenant._data.get('Context', {})

        # Determine template parameters
        templateParams = defaultdict(lambda:'')
        templateParams.update({'zenhome':zenPath(),
                               'ZenPack.Default.RAMCommitment':"",
                               'varpath':varPath()})
        templateParams.update((key, val) for key, val in context.items()
            if key.startswith('ZenPack.Default'))
        templateParams.update(daemondir=self.getDaemonPath())
        return templateParams

    def installDefaultCollectorServices(self, daemonPaths, template, tag):
        """
        Installs a service definition appropriate for a collector daemon for each
        daemon in a list.  Generates a config file using the daemon's genconf.
        Installs the service on each collector.

        @param daemonPaths: paths to daemon executables
        @type daemonPaths: list of strings
        @param template: service definition template
        @type template: string
        @param tag: tag to be applied to all services
        @type tag: string
        @return: None
        """
        if not ZenPack.currentServiceId:
            return

        templateParams = self.templateParams()

        serviceDefinitions = []
        for daemonPath in daemonPaths:
            daemon = os.path.basename(daemonPath)
            if daemon == 'zenexample':
                continue
            configPath = os.path.join(zenPath(), 'etc', daemon+'.conf')
            configContents = subprocess.check_output([daemonPath, 'genconf'])
            configMap = {configPath: configContents}
            templateParams.update(daemon=daemon, daemonpath=daemonPath)
            service = json.loads(template % templateParams)
            service = ZenPack.normalizeService(service, configMap, tag)
            serviceDefinitions.append(json.dumps(service))
        servicePaths = ['/zenoss-application/zenoss-collection/hub/collector'] * len(serviceDefinitions)
        self.installServiceDefinitions(serviceDefinitions, servicePaths)


    def installServicesFromFiles(self, serviceFileNames, serviceConfigs, tag):
        """
        Install a set of control center services

        Each file is expected to contain a json encoded object with two fields:
         servicePath: a service path indicating where this service should be installed.
            See ServiceTree.matchServicePath for description of service path
         serviceDefinition: a service definition object which will be sent to
            Control Center.  Service definition examples may be be seen by running
            $ serviced template list $TEMPLATE_ID
        Each service will be tagged with the given tag in order to enable discovery
        for ZenPack removal.  If a service definition has an ImageID field, but
        the field is empty, the field will be set to the value of the
        SERVICED_SERVICE_IMAGE environment variable.

        :param serviceFileNames: file paths, each containing a service
        :type serviceFileNames: list of strings
        :param serviceConfigs: for each service, maps config name to contents
        :type serviceConfigs: list of dicts string->string
        :param tag: tag to be applied to all services
        :type tag: string
        """
        if not ZenPack.currentServiceId:
            return
        paths, definitions = [],[]

        templateParams = self.templateParams()

        for fileName, configMap in zip(serviceFileNames, serviceConfigs):
            serviceDef = self._loadServiceDefinition(fileName)
            service = json.loads(serviceDef % templateParams)
            definition = ZenPack.normalizeService(service['serviceDefinition'],
                                                  configMap, tag)
            definitions.append(json.dumps(definition))
            paths.append(service['servicePath'])
        self.installServiceDefinitions(definitions, paths)


    def _loadServiceDefinition(self, fileName):
        content = ""
        with open(fileName, 'r') as fh:
            content = fh.read()
        return content


    def installServiceDefinitions(self, serviceDefs, servicePaths):
        """
        Install a service into Control Center

        Install a service (described by a service definition string) at a given
             location in the service tree.  Multiple service/location pairs can
             be specified.

        :param serviceDefs: json encoded representation(s) of service definition
        :type serviceDefs: string or iterable of strings
        :param servicePaths: service path(s) at which to install service
        :type servicePaths: string or iterable of strings.  See
            ServiceTree.matchServicePath for description of service path
        """
        # No current service id indicates that we will not install services
        if not ZenPack.currentServiceId:
            return

        # Handle case where input is single strings (vs parallel lists)
        if isinstance(serviceDefs, basestring):
            serviceDefs = [serviceDefs]
        if isinstance(servicePaths, basestring):
            servicePaths = [servicePaths]

        serviceDefs = [json.loads(sd) for sd in serviceDefs]
        servicePaths = [p if p != "/hub/collector" else "/zenoss-application/zenoss-collection/hub/collector" for p in servicePaths]
        existingPaths = {}

        for sd, sp in zip(serviceDefs, servicePaths):
            sd["Services"] = []
            sp = "" if sp == "/" else sp
            existingPaths[sp + "/=" + sd["Name"]] = sd
            for tag in sd["Tags"]:
                existingPaths[sp + "/" + tag] = sd

        services = []
        parentServicePaths = []
        for sd, sp in zip(serviceDefs, servicePaths):
            if sp in existingPaths:
                existingPaths[sp]["Services"].append(sd)
            else:
                services.append(sd)
                parentServicePaths.append(sp)

        cpClient = ControlPlaneClient(**getConnectionSettings())
        serviceTree = ServiceTree(cpClient.queryServices("*"))
        ctx = servicemigration.ServiceContext()

        for service, parentServicePath in zip(services, parentServicePaths):
            parentServices = serviceTree.matchServicePath(ZenPack.currentServiceId, parentServicePath)
            for parentService in parentServices:
                ctx._ServiceContext__deployService(json.dumps(service), parentService.id)

        try:
            ctx.commit()
        except ControlCenterError as e:
            if e.message == "service exists":
                log.info("Service exists, not deploying.")
            else:
                raise e

    def getExampleLicenseNames(self):
        return sorted(ExampleLicenses.LICENSES.keys())




# ZenPackBase is here for backwards compatibility with older installed
# zenpacks that used it.  ZenPackBase was rolled into ZenPack when we
# started using about.txt files instead of ZenPack subclasses to set
# zenpack metadata.
ZenPackBase = ZenPack

InitializeClass(ZenPack)
