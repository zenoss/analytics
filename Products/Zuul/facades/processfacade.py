##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################
import re
import logging
from itertools import izip, count, imap, islice
from zope.event import notify
from Acquisition import aq_parent
from zope.interface import implements
from Products.ZenModel.OSProcess import OSProcess
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.Zuul import getFacade
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IProcessFacade, ITreeFacade
from Products.Zuul.utils import unbrain
from Products.Zuul.interfaces import IInfo
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.tree import SearchResults, StaleResultsException
from zope.container.contained import ObjectMovedEvent
from Products.ZenModel.OSProcessMatcher import OSProcessClassDataMatcher 
from Products.ZenModel.OSProcessMatcher import applyOSProcessClassMatchers
from Products.ZenUtils.guid.interfaces import IGUIDManager

log = logging.getLogger('zen.ProcessFacade')

class Response:
    lines = []
    
    def __init__(self):
        self.lines = []

    def write(self, s):
        self.lines.append(s)

    def getLines(self):
        return self.lines
    

class ProcessFacade(TreeFacade):
    implements(IProcessFacade, ITreeFacade)

    @property
    def _root(self):
        return self._dmd.Processes

    def _classFactory(self, contextUid):
        return OSProcessClass

    @property
    def _classRelationship(self):
        return 'osProcessClasses'

    @property
    def _instanceClass(self):
        return "Products.ZenModel.OSProcess.OSProcess"

    def _getSecondaryParent(self, obj):
        return obj.osProcessClass()

    def moveProcess(self, uid, targetUid):
        obj = self._getObject(uid)
        target = self._getObject(targetUid)
        brainsCollection = []

        # reindex all the devices and processes underneath this guy and the target
        for org in (obj.getPrimaryParent().getPrimaryParent(), target):
            catalog = IModelCatalogTool(org)
            brainsCollection.append(catalog.search(OSProcess))

        if isinstance(obj, OSProcessClass):
            source = obj.osProcessOrganizer()
            source.moveOSProcessClasses(targetUid, obj.id)
            newObj = getattr(target.osProcessClasses, obj.id)
        elif isinstance(obj, OSProcessOrganizer):
            source = aq_parent(obj)
            source.moveOrganizer(targetUid, (obj.id,))
            newObj = getattr(target, obj.id)
        else:
            raise Exception('Illegal type %s' % obj.__class__.__name__)

        # fire the object moved event for the process instances (will update catalog)
        for brains in brainsCollection:
            objs = imap(unbrain, brains)
            for item in objs:
                notify(ObjectMovedEvent(item, item.os(), item.id, item.os(), item.id))

        return newObj.getPrimaryPath()

    def getSequence(self):
        processClasses = self._dmd.Processes.getSubOSProcessClassesSorted()
        for processClass in processClasses:
            yield {
                'uid': '/'.join(processClass.getPrimaryPath()),
                'folder': processClass.getPrimaryParent().getOrganizerName(),
                'name': processClass.title,
                'includeRegex': processClass.includeRegex,
                'monitor': processClass.zMonitor,
                'count': processClass.count()
            }

    def getSequence2(self):
        processClasses = self._dmd.Processes.getSubOSProcessClassesSorted()
        for processClass in processClasses:
            yield {
                'uid': '/'.join(processClass.getPrimaryPath()),
                'folder': processClass.getPrimaryParent().getOrganizerName(),
                'name': processClass.name,
                'regex': processClass.regex,
                'excludeRegex': processClass.excludeRegex,
                'monitor': processClass.zMonitor,
                'count': processClass.count(),
                'use': processClass.count() > 0,
            }

    def setSequence(self, uids):
        for sequence, uid in izip(count(), uids):
            ob = self._getObject(uid)
            ob.sequence = sequence
            
    def applyOSProcessClassMatchers(self, uids, lines):
        lines2 = []
        # Remove comments and empty lines from the process list
        for line in lines:
            line2 = line.strip()
            if not line2.startswith('#') and not len(line2) == 0:
                lines2.append(line)
        matchers = []
        for uid in uids:
            if isinstance(uid, str):
                matcher = self._getObject(uid)
            else:
                matcher = OSProcessClassDataMatcher(**uid)
            matchers.append(matcher)
        i = 0
        matched, unmatched = applyOSProcessClassMatchers(matchers, lines2)
        for processClass, processClassMatches in matched.iteritems():
            for processSet, matchedLines in processClassMatches.iteritems():
                for line in matchedLines:
                    i += 1
                    ii = str(i)
                    name = processClass.name
                    yield {
                        'uid': ii,
                        'matched': True,
                        'processClass': name,
                        'processSet': processSet,
                        'process': line
                    }

    def getProcessList(self, deviceGuid):
        if deviceGuid and len(deviceGuid) > 0:
            s = ''
            try:
                import subprocess
                from Products.ZenUtils.path import binPath
                device = IGUIDManager(self._dmd).getObject(deviceGuid)
                s = '# ' + device.id
                zenmodelerOpts = ['run', '--now', '--debug', '-v10', '-d', device.id]
                isPerfMonRemote = False
                zenmodelerName = 'zenmodeler'
                zenmodelerPath = binPath(zenmodelerName)
                monitorId = device.perfServer().id
                if monitorId != 'localhost':
                    isPerfMonRemote = True
                if isPerfMonRemote:
                    cmd = 'zminion --minion-name zminion_%s run -- "%s %s"' % (device.getPerformanceServerName(), zenmodelerName, ' '.join(zenmodelerOpts))
                else:
                    cmd = "%s %s" % (zenmodelerPath, ' '.join(zenmodelerOpts))
                processList = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).splitlines()
                filterProcessLine = re.compile('DEBUG zen\.osprocessmatcher: COMMAND LINE: (?P<process>.*)$')
                for processListLine in processList:
                    m = filterProcessLine.search(processListLine)
                    if m:
                        s += '\n' + m.group('process')
            except Exception as e:
                s += '\n# ' + str(e)
            yield {
               'uid': '0',
               'process': s
            }

        else:
            pass


    def _processSearch(self, limit=None, start=None, sort='name', dir='ASC',
              params=None, uid=None, criteria=()):
        ob = self._getObject(uid) if isinstance(uid, basestring) else uid
        cat = IModelCatalogTool(ob)
        query = {}
        if params and params.get('name'):
            query['name'] = "*{0}*".format(params.get('name'))
        reverse = dir=='DESC'
        return cat.search("Products.ZenModel.OSProcessClass.OSProcessClass",
                          start=start, limit=limit, orderby=sort,
                          reverse=reverse, query=query)

    def getList(self, limit=None, start=None, sort='name', dir='DESC',
              params=None, uid=None, criteria=()):
        brains = self._processSearch(limit, start, sort, dir, params, uid, criteria)
        wrapped = imap(IInfo, imap(unbrain, brains))
        return SearchResults(wrapped, brains.total, brains.hash_)

    def getDevices(self, uid=None, start=0, limit=50, sort='name', dir='ASC',
                   params=None, hashcheck=None):

        # We have to query for the process(es) and then use unrestrictedTraverse on the deviceIds to get the devices
        brains = self.getObjectBrains(uid, 0, None, sort, dir, params, None, 'Products.ZenModel.OSProcess.OSProcess', ['deviceId'])
        # ZEN-10057 - Handle the case of empty results for a filter with no matches
        if not brains:
            return SearchResults([], 0, [])

        def getDevice(devId):
            return self.context.dmd.unrestrictedTraverse(str(devId))

        devices = list(getDevice(brain.deviceId) for brain in brains)
        devices = list(device for device in devices if device)

        # we may have changed the number of results, so check the hash here
        totalCount = len(devices)
        hash_ = str(totalCount)
        if hashcheck is not None:
            if hash_ != hashcheck:
                raise StaleResultsException("Search results do not match")

        # Pick out the correct range
        start = max(start, 0)
        if limit is None:
            stop = None
        else:
            stop = start + limit
        results = islice(devices, start, stop)

        deviceInfos = list(imap(IInfo, results))

        # This part is copy-paste from ZuulFacade.getDevices:
        uuids = set(dev.uuid for dev in deviceInfos)
        if uuids:
            zep = getFacade('zep', self._dmd)
            severities = zep.getEventSeverities(uuids)
            for device in deviceInfos:
                device.setEventSeverities(severities[device.uuid])

        return SearchResults(iter(deviceInfos), totalCount, hash_)


