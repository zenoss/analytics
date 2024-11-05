##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='Base Classes for loading gunk in a ZenPack'

from Products.ZenReports.ReportLoader import ReportLoader
from Products.ZenUtils.events import pausedAndOptimizedIndexing
from Products.ZenUtils.path import binPath, zenPath
from Products.ZenUtils.guid.interfaces import IGUIDManager
from Products.ZenUtils.config import ConfigFile
from Products.Zuul import getFacade

from zenoss.protocols.jsonformat import from_dict
from zenoss.protocols.protobufs.zep_pb2 import EventDetailItemSet, EventDetailItem
from zenoss.protocols.services import ServiceResponseError

import os
import json
import ConfigParser
import subprocess
import logging
log = logging.getLogger('zen.ZPLoader')

CONFIG_FILE = 'about.txt'
CONFIG_SECTION_ABOUT = 'about'

def findFiles(pack, directory, filter=None, excludedDirs=('.svn',)):
    result = []
    if isinstance(pack, basestring):
        path = os.path.join(pack, directory)
    else:
        path = pack.path(directory)
    for p, ds, fs in os.walk(path):
        # Don't visit excluded directories - os.walk with topdown=True
        for excludedDir in excludedDirs:
            if excludedDir in ds:
                ds.remove(excludedDir)
        if not os.path.split(p)[-1].startswith('.'):
            for f in fs:
                if filter is None or filter(f):
                    result.append(os.path.join(p, f))
    return result

def findDirectories(pack, directory):
    result = []
    for p, ds, fs in os.walk(pack.path(directory)):
        if not os.path.split(p)[-1].startswith('.'):
            for d in ds:
                result.append(os.path.join(p, d))
    return result

def branchAfter(filename, directory, prefix = ""):
    "return the branch after the given directory name"
    path = filename.split('/')
    return prefix + '/'.join(path[path.index(directory)+1:])


class ZenPackLoader:

    name = "Set This Name"

    def load(self, pack, app):
        """Load things from the ZenPack and put it
        into the app"""

    def unload(self, pack, app, leaveObjects=False):
        """Remove things from Zenoss defined in the ZenPack"""

    def list(self, pack, app):
        "List the items that would be loaded from the given (unpacked) ZenPack"

    def upgrade(self, pack, app):
        "Run an upgrade on an existing pack"

from xml.sax import make_parser

class ZPLObject(ZenPackLoader):

    name = "Objects"

    def load(self, pack, app):
        from Products.ZenRelations.ImportRM import ImportRM
        class AddToPack(ImportRM):
            def endElement(self, name):
                if name == 'object':
                    obj = self.objstack[-1]
                    log.debug('Now adding %s', obj.getPrimaryUrlPath())
                    try:
                        obj.buildRelations()
                        obj.removeRelation('pack')
                        obj.addRelation('pack', pack)
                    except Exception:
                        log.exception("Error adding pack to %s",
                                      obj.getPrimaryUrlPath())

                ImportRM.endElement(self, name)
        importer = AddToPack(noopts=True, app=app)
        importer.options.noindex = True
        importer.options.noCommit = True
        with pausedAndOptimizedIndexing():
            for f in self.objectFiles(pack):
                log.info("Loading %s", f)
                importer.loadObjectFromXML(xmlfile=f)


    def parse(self, filename, handler):
        parser = make_parser()
        parser.setContentHandler(handler)
        parser.parse(open(filename))


    def unload(self, pack, app, leaveObjects=False):
        if leaveObjects:
            return
        from Products.ZenRelations.Exceptions import ObjectNotFound
        dmd = app.zport.dmd
        objs = sorted(pack.packables(), key=lambda x: x.getPrimaryPath(),
                        reverse=True)
        for obj in objs:
            path = obj.getPrimaryPath()
            path, id = path[:-1], path[-1]
            obj = dmd.getObjByPath(path)
            if len(path) > 3:           # leave /Services, /Devices, etc.
                try:
                    try:
                        obj._delObject(id)
                    except ObjectNotFound:
                        obj._delOb(id)
                except (AttributeError, KeyError):
                    log.warning("Unable to remove %s on %s", id,
                                '/'.join(path))

    def list(self, pack, unused):
        return [obj.getPrimaryUrlPath() for obj in pack.packables()]


    def objectFiles(self, pack):
        def isXml(f): return f.endswith('.xml')
        return sorted(findFiles(pack, 'objects', isXml),
              key = lambda f: -1 if f.endswith('objects.xml') else 0)


class ZPLReport(ZPLObject):

    name = "Reports"

    def load(self, pack, app):
        class HookReportLoader(ReportLoader):
            def loadFile(self, root, id, fullname):
                rpt = ReportLoader.loadFile(self, root, id, fullname)
                rpt.addRelation('pack', pack)
                return rpt

            def loadDirectory(self, repdir):
                self.log.info("Loading reports from %s", repdir)
                reproot = self.dmd.Reports
                for orgpath, fid, fullname in self.reports(repdir):
                    rorg = reproot.createOrganizer(orgpath)
                    if getattr(rorg, fid, False):
                        if self.options.force:
                            rorg._delObject(fid)
                        else:
                            continue
                    self.log.info("loading: %s/%s", orgpath, fid)
                    self.loadFile(rorg, fid, fullname)

        rl = HookReportLoader(noopts=True, app=app)
        rl.options.force = True
        rl.loadDirectory(pack.path('reports'))

    def upgrade(self, pack, app):
        self.unload(pack, app)
        self.load(pack, app)

    def list(self, pack, unused):
        return [branchAfter(r, 'reports') for r in findFiles(pack, 'reports')]


class ZPLDaemons(ZenPackLoader):

    name = "Daemons"

    extensionsToIgnore = ('.svn-base', '.pyc' '~')
    def filter(self, f):
        if 'zenexample' in f:
            return False

        for ext in self.extensionsToIgnore:
            if f.endswith(ext):
                return False

        return True


    def binPath(self, daemon):
        return zenPath('bin', os.path.basename(daemon))


    def _genConfFile(self, pack):
        """
        Attempt to generate a conf file for any daemons. Wait for completion.
        """
        try:
            p = subprocess.Popen(binPath('create_sample_config.sh'),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=pack.path())
            p.wait()
        except OSError:
            pass

    def _updateConfFile(self, pack):
        """
        Update conf files for any daemons to account for logfile path
        differences on the localhost collector.
        """
        for fs in findFiles(pack, 'daemons', filter=self.filter):
            name = fs.rsplit('/', 1)[-1]
            logpath = getattr(pack, 'About', False) and \
                    pack.About._getLogPath(name).rsplit('/', 1)[0]
            if logpath and logpath != zenPath('log'):
                try:
                    with open(zenPath('etc', '%s.conf' % name), 'r') as conf:
                        confFile = ConfigFile(conf)
                        confFile.parse()
                        if 'logpath' not in (key for key, value in confFile.items()):
                            with open(zenPath('etc', '%s.conf' % name), 'a') as conf:
                                conf.write('\nlogpath %s\n' % logpath)
                except IOError:
                    # No conf file. Move on.
                    pass

    def load(self, pack, unused):
        for fs in findFiles(pack, 'daemons', filter=self.filter):
            os.chmod(fs, 0o755)
            path = self.binPath(fs)
            if os.path.lexists(path):
                os.remove(path)
            os.symlink(fs, path)
        self._genConfFile(pack)
        self._updateConfFile(pack)


    def upgrade(self, pack, app):
        self.unload(pack, app)
        self.load(pack, app)


    def unload(self, pack, unused, leaveObjects=False):
        for fs in findFiles(pack, 'daemons', filter=self.filter):
            try:
                os.remove(self.binPath(fs))
            except OSError:
                pass

    def list(self, pack, unused):
        return [branchAfter(d, 'daemons')
                for d in findFiles(pack, 'daemons', filter=self.filter)]


class ZPLBin(ZenPackLoader):

    name = "Bin"
    extensionsToIgnore = ('.svn-base', '.pyc' '~')

    def filter(self, f):
        for ext in self.extensionsToIgnore:
            if f.endswith(ext):
                return False
        return True

    def binPath(self, bin_file):
        args = ['bin']
        if '/zenrun.d/' in bin_file:
            args.append('zenrun.d')
        args.append(os.path.basename(bin_file))
        return zenPath(*args)

    def load(self, pack, unused):
        for fs in findFiles(pack, 'bin', filter=self.filter):
            os.chmod(fs, 0o755)
            path = self.binPath(fs)
            if os.path.lexists(path):
                os.remove(path)
            os.symlink(fs, path)

    def upgrade(self, pack, app):
        self.unload(pack, app)
        self.load(pack, app)

    def list(self, pack, unused):
        return [branchAfter(d, 'bin')
                for d in findFiles(pack, 'bin', filter=self.filter)]


class ZPLLibExec(ZenPackLoader):

    name = "LibExec"

    extensionsToIgnore = ('.svn-base', '.pyc' '~')
    def filter(self, f):
        for ext in self.extensionsToIgnore:
            if f.endswith(ext):
                return False
        return True

    def load(self, pack, unused):
        for fs in findFiles(pack, 'libexec', filter=self.filter):
            os.chmod(fs, 0o755)

    def upgrade(self, pack, app):
        self.unload(pack, app)
        self.load(pack, app)

    def list(self, pack, unused):
        return [branchAfter(d, 'libexec')
                for d in findFiles(pack, 'libexec', filter=self.filter)]


class ZPLModelers(ZenPackLoader):

    name = "Modeler Plugins"


    def list(self, pack, unused):
        return [branchAfter(d, 'plugins')
                for d in findFiles(pack, 'modeler/plugins')]


class ZPLSkins(ZenPackLoader):

    name = "Skins"


    def load(self, pack, app):
        from Products.ZenUtils.Skins import registerSkin
        skinsDir = pack.path('')
        if os.path.isdir(skinsDir):
            registerSkin(app.zport.dmd, skinsDir)


    def upgrade(self, pack, app):
        self.unload(pack, app)
        return self.load(pack, app)


    def unload(self, pack, app, leaveObjects=False):
        from Products.ZenUtils.Skins import unregisterSkin
        skinsDir = pack.path('')
        if os.path.isdir(skinsDir):
            unregisterSkin(app.zport.dmd, skinsDir)


    def list(self, pack, unused):
        return [branchAfter(d, 'skins') for d in findDirectories(pack, 'skins')]


class ZPLDataSources(ZenPackLoader):

    name = "DataSources"


    def list(self, pack, unused):
        return [branchAfter(d, 'datasources')
                for d in findFiles(pack, 'datasources',
                lambda f: not f.endswith('.pyc') and f != '__init__.py')]



class ZPLLibraries(ZenPackLoader):

    name = "Libraries"


    def list(self, pack, unused):
        d = pack.path('lib')
        if os.path.isdir(d):
            return [l for l in os.listdir(d)]
        return []

class ZPLAbout(ZenPackLoader):

    name = "About"

    def getAttributeValues(self, pack):
        about = pack.path(CONFIG_FILE)
        result = []
        if os.path.exists(about):
            parser = ConfigParser.SafeConfigParser()
            parser.read(about)
            result = []
            for key, value in parser.items(CONFIG_SECTION_ABOUT):
                try:
                    value = eval(value)
                except Exception:
                    # Blanket exception catchers like this are evil.
                    pass
                result.append((key, value))
        return result


    def load(self, pack, unused):
        for name, value in self.getAttributeValues(pack):
            setattr(pack, name, value)


    def upgrade(self, pack, app):
        self.load(pack, app)


    def list(self, pack, unused):
        return [('%s %s' % av) for av in self.getAttributeValues(pack)]

class ZPTriggerAction(ZenPackLoader):

    name = "Triggers and Actions"

    def load(self, pack, app):
        """
        Load Notifications and Triggers from an actions.json file

        Given a JSON-formatted configuration located at {zenpack}/actions/actions.json,
        create or update triggers and notifications specific to this zenpack.
        When creating or updating, the object is first checked to see whether or
        not an object exists with the configured guid for notifications or uuid
        for triggers. If an object is not found, one will be created. During
        creation, care is taken with regard to the id - integer suffixes will be
        appended to try to create a unique id. If we do not find a unique id after
        100 tries, an error will occur. When updating an object, care is taken
        to not change the name as it may have since been altered by the user (or
        by this loader adding a suffix).

        """
        log.debug("ZPTriggerAction: load")
        import Products.Zuul as Zuul
        from Products.Zuul.facades import ObjectNotFoundException

        tf = Zuul.getFacade('triggers', app.dmd)
        guidManager = IGUIDManager(app)

        for conf in findFiles(pack, 'zep',lambda f: f == 'actions.json'):

            data = json.load(open(conf, "r"))
            log.debug("DATA IS: %s", data)

            triggers = data.get('triggers', [])
            notifications = data.get('notifications', [])


            tf.synchronize()
            all_names = set(t['name'] for t in tf.getTriggerList())

            for trigger_conf in triggers:

                existing_trigger = guidManager.getObject(trigger_conf['uuid'])

                if existing_trigger:
                    trigger_data = tf.getTrigger(trigger_conf['uuid'])
                    trigger_conf['name'] = trigger_data['name']

                    log.info('Existing trigger found, updating: %s', trigger_conf['name'])
                    tf.updateTrigger(**trigger_conf)

                else:

                    test_name = trigger_conf['name']
                    for x in xrange(1,101):
                        if test_name in all_names:
                            test_name = '%s_%d' % (trigger_conf['name'], x)
                        else:
                            log.debug('Found unused trigger name: %s', test_name)
                            break
                    else:
                        # if we didn't find a unique name
                        raise Exception('Could not find unique name for trigger: "%s".' % trigger_conf['name'])

                    log.info('Creating trigger: %s', test_name)

                    try:
                        tf.createTrigger(test_name, uuid=trigger_conf['uuid'].lower(), rule=trigger_conf['rule'])
                    except Exception as e:
                        log.warning("Failed creating trigger '%s': %s", test_name, e)
                        raise

            for notification_conf in notifications:

                existing_notification = guidManager.getObject(str(notification_conf['guid']))

                if existing_notification:
                    log.info("Existing notification found, updating: %s", existing_notification.id)

                    subscriptions = set(existing_notification.subscriptions + notification_conf['subscriptions'])
                    notification_conf['uid'] = '/zport/dmd/NotificationSubscriptions/%s' % existing_notification.id
                    # ensure uuid's are lowercase
                    notification_conf['subscriptions'] = [x.lower() for x in list(subscriptions)]
                    notification_conf['name'] = existing_notification.id
                    try:
                        tf.updateNotification(**notification_conf)
                    except Exception as e:
                        log.warning("Failed updating notification '%s': %s", existing_notification.id, e)
                        raise
                else:
                    test_id = notification_conf['id']
                    for x in xrange(1,101):
                        test_uid = '/zport/dmd/NotificationSubscriptions/%s' % test_id

                        try:
                            tf.getNotification(test_uid)
                        except ObjectNotFoundException:
                            break

                        test_id = '%s_%d' % (notification_conf['id'], x)
                    else:
                        # if we didn't find a unique name
                        raise Exception('Could not find unique name for notification: "%s".' % notification_conf['id'])

                    log.info('Creating notification: %s', test_id)
                    tf.createNotification(str(test_id), notification_conf['action'], notification_conf['guid'])

                    notification_conf['uid'] = '/zport/dmd/NotificationSubscriptions/%s' % test_id
                    # ensure uuid's are lowercase
                    notification_conf['subscriptions'] = [x.lower() for x in list(notification_conf['subscriptions'])]
                    try:
                        tf.updateNotification(**notification_conf)
                    except Exception as e:
                        # couldnt create notification in zep
                        log.warning("Failed creating notification '%s': %s", test_id, e)
                        # remove notification from the zope side
                        tf.removeNotification(notification_conf['uid'])
                        raise


    def _getTriggerGuid(self, facade, name):
        triggers = facade.getTriggers()
        guid = None
        for trigger in triggers:
            if trigger['name'] == name:
                guid = trigger['uuid']
                break
        if not guid:
            guid = facade.addTrigger(name)
        return guid

    def unload(self, pack, app, leaveObjects=False):
        """Remove things from Zenoss defined in the ZenPack"""
        log.debug("ZPTriggerAction: unload")

    def list(self, pack, app):
        "List the items that would be loaded from the given (unpacked) ZenPack"
        log.debug("ZPTriggerAction: list")

    def upgrade(self, pack, app):
        "Run an upgrade on an existing pack"
        log.debug("ZPTriggerAction: upgrade")


class ZPZep(ZenPackLoader):

    name = "ZEP"

    def _data(self, conf):
        data = {}
        try:
            with open(conf, "r") as configFile:
                cleanJson = self._stripComments(configFile)
                data = json.loads(cleanJson)
        except IOError as e:
            # this file doesn't exist in this zenpack.
            log.debug("File could not be opened for reading: %s",
                      conf)
        except ValueError as e:
            log.error("%s JSON data has an error:\n%s",
                      conf, e)
        return data

    def _stripComments(self, configFile):
        # Remove from // to the end of line for each line
        return ''.join(line.split('//',1)[0] for line in configFile)

    def _prepare(self, pack, app):
        """
        Load in the Zep configuration file which should be located here:
        $ZENPACK/zep/zep.json
        """

        self.handlers = (EventDetailItemHandler(), )
        p = pack.path('zep')
        confFile = os.path.join(p, 'zep.json')
        data = self._data(confFile)

        return data

    def load(self, pack, app):
        data = self._prepare(pack, app)
        for handler in self.handlers:
            handler.load(data)

    def unload(self, pack, app, leaveObjects=False):
        data = self._prepare(pack, app)
        for handler in self.handlers:
            handler.unload(data, leaveObjects)

    def list(self, pack, app):
        data = self._prepare(pack, app)
        info = []
        for handler in self.handlers:
            info.extend(handler.list(data))

    def upgrade(self, pack, app):
        data = self._prepare(pack, app)
        for handler in self.handlers:
            handler.upgrade(data)


class EventDetailItemHandler(object):
    key = 'EventDetailItem'

    def load(self, configData):
        """
        configData is a JSON dict that contains a key of the same
        name as specified in this class (ie self.key).

        The value from this key is expected to be an arrary of dictionaries
        as used by the ZEP system. See the documentation in the
        ZenModel/ZenPackTemplate/CONTENT/zep/zep.json.example file.
        """
        if configData:
            self.zep = getFacade('zep')
            items = configData.get(EventDetailItemHandler.key)
            if items is None:
                log.warn("Expected key '%s' for details is missing from the zep.json file",
                          self.key)
                return
            detailItemSet = from_dict(EventDetailItemSet, dict(
                # An empty array in details casues ZEP to puke
                details = items
            ))
            try:
                self.zep.addIndexedDetails(detailItemSet)
            except Exception as ex:
                log.error("ZEP %s error adding detailItemSet data: %s\nconfigData= %s",
                              getattr(ex, 'status', 'unknown'), detailItemSet, configData)
                log.error("See the ZEP logs for more information.")

    def list(self, configData):
        if configData:
            self.zep = getFacade('zep')
            items = configData.get(EventDetailItemHandler.key, [])
            info = []
            for item in items:
                info.append("Would be adding the following detail to be indexed by ZEP: %s" % item.key)
            return info

    def unload(self, configData, leaveObjects):
        if not leaveObjects and configData:
            self.zep = getFacade('zep')
            items = configData.get(EventDetailItemHandler.key, [])
            for item in items:
                log.info("Removing the following currently indexed detail by ZEP: %s", item['key'])
                try:
                    self.zep.removeIndexedDetail(item['key'])
                except ServiceResponseError as e:
                    if e.status == 404:
                        log.debug('Indexed detail was previously removed from ZEP')
                    else:
                        log.warning("Failed to remove indexed detail: %s", e.message)

    def upgrade(self, configData):
        if configData:
            self.zep = getFacade('zep')
            items = configData.get(EventDetailItemHandler.key, [])
            for item in items:
                log.info("Upgrading the following to be indexed by ZEP: %s", item)
                detailItem = from_dict(EventDetailItem, item)
                self.zep.updateIndexedDetailItem(detailItem)

