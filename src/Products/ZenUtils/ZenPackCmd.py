##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = "Manage ZenPacks"

import pkg_resources
import Products

from ZODB.transact import transact
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.Utils import cleanupSkins, zenPath, binPath, getObjByPath,atomicWrite, varPath

from Products.ZenModel import ZVersion
from Products.ZenModel.ZenPack import ZenPackException, \
                                        ZenPackNotFoundException, \
                                        ZenPackNeedMigrateException
from Products.ZenModel.ZenPack import ZenPackDependentsException
from Products.ZenModel.ZenPack import ZenPack
from Products.ZenUtils.events import paused
from Products.Zuul.utils import CatalogLoggingFilter
from Products.Zuul.catalog.events import onIndexingEvent
import Products.ZenModel.ZenPackLoader as ZPL
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_ERROR
from Products.ZenModel.ZVersion import VERSION as ZENOSS_VERSION
import zenpack as oldzenpack
import transaction
import os, sys
import shutil
import string
import tempfile
import subprocess
import socket
import logging
import zExceptions
import json

from urlparse import urlparse
from Products.ZenMessaging.audit import audit


log = logging.getLogger('zen.ZenPackCMD')

PACKS_DUMP = zenPath(".ZenPacks/packs.json")

#import zenpacksupport

FQDN = socket.getfqdn()

ZENPACKS_BASE_URL = 'http://zenpacks.zenoss.com/pypi'

# All ZenPack eggs have to define exactly one entry point in this group.
ZENPACK_ENTRY_POINT = 'zenoss.zenpacks'

########################################
#   ZenPack Creation
########################################

def CreateZenPack(zpId, prevZenPackName='', devDir=None):
    """
    Create the zenpack in the filesystem.
    The zenpack is not installed in Zenoss, it is simply created in
    the $ZENHOME/ZenPacks directory.  Usually this should be followed
    with a "zenpack install" call.
    zpId should already be valid, scrubbed value.
    prevZenPackName is written to PREV_ZENPACK_NAME in setup.py.
    """
    import Products.ZenModel as _zm

    parts = zpId.split('.')
    
    # Copy template to $ZENHOME/ZenPacks
    srcDir = os.path.join(os.path.dirname(_zm.__file__), 'ZenPackTemplate')
    if not devDir:
        devDir = zenPath('ZenPacks')
    if not os.path.exists(devDir):
        os.mkdir(devDir, 0o750)
    destDir = os.path.join(devDir, zpId)
    shutil.copytree(srcDir, destDir, symlinks=False)

    # Write setup.py
    packages = []
    for i in range(len(parts)):
        packages.append('.'.join(parts[:i+1]))
    mapping = dict(
        NAME = zpId,
        VERSION = '1.0.0',
        AUTHOR = '',
        LICENSE = '',
        NAMESPACE_PACKAGES = packages[:-1],
        PACKAGES = packages,
        INSTALL_REQUIRES = [],
        COMPAT_ZENOSS_VERS = '',
        PREV_ZENPACK_NAME = prevZenPackName,
        )
    WriteSetup(os.path.join(destDir, 'setup.py'), mapping)

    # Create subdirectories
    base = destDir
    for part in parts[:-1]:
        base = os.path.join(base, part)
        os.mkdir(base)
        f = open(os.path.join(base, '__init__.py'), 'w')
        f.write("__import__('pkg_resources').declare_namespace(__name__)\n")
        f.close()
    base = os.path.join(base, parts[-1])
    shutil.move(os.path.join(destDir, 'CONTENT'), base)
    audit('Shell.ZenPack.Create', zpId)

    return destDir


def WriteSetup(setupPath, values):
    """
    """
    f = file(setupPath, 'r')
    lines = f.readlines()
    f.close()

    newLines = []
    for i, line in enumerate(lines):
        if line.startswith('STOP_REPLACEMENTS'):
            newLines += lines[i:]
            break
        key = line.split('=')[0].strip()
        if key in values:
            value = values[key]
            if isinstance(value, basestring):
                fmt = '%s = "%s"\n'
            else:
                fmt = '%s = %s\n'
            newLines.append(fmt % (key, value))
        else:
            newLines.append(line)
    
    f = file(setupPath, 'w')
    f.writelines(newLines)
    f.close()


def CanCreateZenPack(dmd, zpId):
    """
    Return tuple (bool, string) where first element is true if a new zenpack
    can be created with the given info and false if not.  If first element
    is True then the second part of the tuple contains the scrubbed ZenPack id.
    If the first part is False then the second contains an explanatory
    message.
    """
    # Check if id and package looks reasonable
    (allowable, idOrMsg) = ScrubZenPackId(zpId)
    if allowable:
        zpId = idOrMsg
    else:
        return (False, idOrMsg)

    # Is the id already in use?
    if dmd:
        if zpId in dmd.ZenPackManager.packs.objectIds():
            return (False, 'A ZenPack named %s already exists.' % zpId)

    # Is there another zenpack in the way?
    # Now that zenpacks are created in $ZENHOME/ZenPacks instead of 
    # $ZENHOME/ZenPackDev this may no longer be necessary because a
    # zp in the way should be installed and caught by the already in use
    # check above.
    if os.path.exists(zenPath('ZenPacks', zpId)):
        return (False, 'A directory named %s already exists' % zpId +
                        ' in $ZENHOME/ZenPacks.  Use a different name'
                        ' or remove that directory.')

    return (True, idOrMsg)


def ScrubZenPackId(name):
    """
    If the given name conforms to ZenPack naming rules, or can easily be
    modified to do so, then return (True, scrubbedName) where scrubbedName
    is either name or a slightly modified name.  If the given name does
    not conform to naming rules and we can't easily modify it to do so
    then return (False, errorMsg) where errorMsg describes why name
    is unacceptable.
    """
    parts = name.split('.')

    # Remove leading dots, trailing dots, adjacent dots and strip whitespace
    # from each part
    parts = [p.strip() for p in parts]
    parts = [p for p in parts if p]

    # Add/fix leading 'ZenPacks'
    if parts[0] != 'ZenPacks':
        if parts[0].lower() == 'zenpacks':
            parts[0] = 'ZenPacks'
        else:
            parts.insert(0, 'ZenPacks')

    # Must be at least 3 parts
    if len(parts) < 3:
        return (False, 'ZenPack names must contain at least three package '
                'names separated by periods.')

    # Each part must start with a letter
    for p in parts:
        if p[0] not in string.letters:
            return (False, 'Each package name must start with a letter.')

    # Only letters, numbers and underscores in each part
    allowable = string.letters + string.digits + '_'
    for p in parts:
        for c in p:
            if c not in allowable:
                return (False, 'Package names may only contain letters, '
                        'numbers and underscores.')

    return (True, '.'.join(parts))


########################################
#   ZenPack Installation
########################################

class NonCriticalInstallError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message

def InstallEggAndZenPack(dmd, eggPath, link=False,
                            filesOnly=False, sendEvent=True,
                            previousVersion=None, forceRunExternal=False,
                            fromUI=False, serviceId=None, ignoreServiceInstall=False):
    """
    Installs the given egg, instantiates the ZenPack, installs in
    dmd.ZenPackManager.packs, and runs the zenpacks's install method.
    Returns a list of ZenPacks that were installed.
    """
    zenPacks = []
    nonCriticalErrorEncountered = False
    with paused(onIndexingEvent):
        try:
            zpDists = InstallEgg(dmd, eggPath, link=link)
            for d in zpDists:
                try:
                    zp = InstallDistAsZenPack(dmd,
                                              d,
                                              eggPath,
                                              link,
                                              filesOnly=filesOnly,
                                              previousVersion=previousVersion,
                                              forceRunExternal=forceRunExternal,
                                              fromUI=fromUI,
                                              serviceId=serviceId,
                                              ignoreServiceInstall=ignoreServiceInstall)
                    zenPacks.append(zp)
                    audit('Shell.ZenPack.Install', zp.id)
                except NonCriticalInstallError as ex:
                    nonCriticalErrorEncountered = True
                    if sendEvent:
                        ZPEvent(dmd, 3, ex.message)
        except Exception as e:
            # Get that exception out there in case it gets blown away by ZPEvent
            log.exception("Error installing ZenPack %s", eggPath)
            if sendEvent:
                ZPEvent(dmd, SEVERITY_ERROR, 'Error installing ZenPack %s' % eggPath,
                    '%s: %s' % sys.exc_info()[:2])
            # Don't just raise, because if ZPEvent blew away exception context
            # it'll be None, which is bad. This manipulates the stack to look like
            # this is the source of the exception, but we logged it above so no
            # info is lost.
            raise e
    transaction.commit()
    if sendEvent:
        zenPackIds = [zp.id for zp in zenPacks]
        if zenPackIds:
            ZPEvent(dmd, 2, 'Installed ZenPacks %s' % ','.join(zenPackIds))
        elif not nonCriticalErrorEncountered:
            ZPEvent(dmd, SEVERITY_ERROR, 'Unable to install %s' % eggPath)
    return zenPacks


def InstallEgg(dmd, eggPath, link=False):
    """
    Install the given egg and add to the current working set.
    This does not install the egg as a ZenPack.
    Return a list of distributions that should be installed as ZenPacks.
    """
    eggPath = os.path.abspath(eggPath)
    zenPackDir = zenPath('ZenPacks')

    # Make sure $ZENHOME/ZenPacks exists
    CreateZenPacksDir()

    # Install the egg
    if link:
        zenPackDir = varPath('ZenPacks')
        cmd = ('%s setup.py develop ' % binPath('python') +
                '--site-dirs=%s ' % zenPackDir +
                '-d %s' % zenPackDir)
        returncode, out, err = None, '', ''
        for attempt in range(3):
            p = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True,
                                cwd=eggPath)
            out, err = p.communicate()
            p.wait()
            returncode = p.returncode
            if returncode:
                log.info("Error installing the egg (%s): %s",
                         returncode, err)
                try:
                    DoEasyUninstall(eggPath)
                except Exception:
                    pass
            else:
                break
        if returncode:
            raise ZenPackException('Error installing the egg (%s): %s' %
                                   (returncode, err))
        zpDists = AddDistToWorkingSet(eggPath)
    else:
        try:
            zpDists = DoEasyInstall(eggPath)
        except Exception:
            DoEasyUninstall(eggPath)
            raise
        # cmd = 'easy_install --always-unzip --site-dirs=%s -d %s %s' % (
        #             zenPackDir,
        #             zenPackDir,
        #             eggPath)
        # p = subprocess.Popen(cmd,
        #                     stdout=subprocess.PIPE,
        #                     stderr=subprocess.PIPE,
        #                     shell=True)
        # p.wait()
        # eggName = os.path.split(eggPath)[1]
        # eggPath = os.path.join(zenPackDir, eggName)
    return zpDists


# def GetZenPackNamesFromEggPath(eggPath):
#     """
#     Given a path to a ZenPack egg (installed or not) return the 
#     name of the ZenPack it contains.
#     """
#     zpNames = []
#     for d in pkg_resources.find_distributions(eggPath)
#         if d.project_name.startswith('ZenPacks.'):
#             zpNames.append(d.project_name)
#     return zpNames


def InstallDistAsZenPack(dmd, dist, eggPath, link=False, filesOnly=False,
                         previousVersion=None, forceRunExternal=False,
                         fromUI=False, serviceId=None, ignoreServiceInstall=False):
    """
    Given an installed dist, install it into Zenoss as a ZenPack.
    Return the ZenPack instance.
    """

    @transact
    def transactional_actions():
        # Instantiate ZenPack
        entryMap = pkg_resources.get_entry_map(dist, ZENPACK_ENTRY_POINT)
        if not entryMap or len(entryMap) > 1:
            raise ZenPackException('A ZenPack egg must contain exactly one'
                    ' zenoss.zenpacks entry point.  This egg appears to contain'
                    ' %s such entry points.' % len(entryMap))
        packName, packEntry = entryMap.items()[0]
        runExternalZenpack = True
        #if zenpack with same name exists we can't load both modules
        #installing new egg zenpack will be done in a sub process
        def doesExist():
            existing = dmd.ZenPackManager.packs._getOb(packName, None)
            if existing:
                log.info("Previous ZenPack exists with same name %s", packName)
            return existing
        if filesOnly or not doesExist():
            if filesOnly:
                log.info("ZenPack files only install: %s", packName)
            #running files only or zenpack by same name doesn't already exists
            # so no need to install the zenpack in an external process
            runExternalZenpack = False
            module = packEntry.resolve()
            if hasattr(module, 'ZenPack'):
                zenPack = module.ZenPack(packName)
            else:
                zenPack = ZenPack(packName)
            zenPack.eggPack = True
            CopyMetaDataToZenPackObject(dist, zenPack)
            if filesOnly:
                for loader in (ZPL.ZPLDaemons(), ZPL.ZPLBin(), ZPL.ZPLLibExec()):
                    loader.load(zenPack, None)
            if fromUI and not zenPack.installableFromUI:
                raise ZenPackException("This ZenPack cannot be installed through the UI.")

        if not filesOnly:
            # Look for an installed ZenPack to be upgraded.  In this case
            # upgraded means that it is removed before the new one is installed
            # but that its objects are not removed and the packables are
            # copied to the new instance.
            existing = dmd.ZenPackManager.packs._getOb(packName, None)
            if not existing and zenPack.prevZenPackName:
                existing = dmd.ZenPackManager.packs._getOb(
                                    zenPack.prevZenPackName, None)

            deferFileDeletion = False
            packables = []
            upgradingFrom = None
            if existing:
                upgradingFrom = existing.version
                for p in existing.packables():
                    packables.append(p)
                    existing.packables.removeRelation(p)
                if existing.isEggPack():
                    forceNoFileDeletion = existing.eggPath() == dist.location
                    RemoveZenPack(dmd, existing.id,
                                    skipDepsCheck=True, leaveObjects=True,
                                    forceNoFileDeletion=forceNoFileDeletion,
                                    uninstallEgg=False)
                else:
                    # Don't delete files, might still be needed for
                    # migrate scripts to be run below.
                    deferFileDeletion = True
                    oldzenpack.RemoveZenPack(dmd, existing.id,
                                    skipDepsCheck=True, leaveObjects=True,
                                    deleteFiles=False)

            if runExternalZenpack or forceRunExternal:
                log.info("installing zenpack %s; launching process", packName)
                cmd = [binPath('zenpack')]
                if link:
                    cmd += ["--link"]
                cmd += ["--install", eggPath]
                if upgradingFrom:
                    cmd += ['--previousversion', upgradingFrom]
                if fromUI:
                    cmd += ["--fromui"]
                if serviceId:
                    cmd += ['--service-id', serviceId]
                if ignoreServiceInstall:
                    cmd += ['--ignore-service-install']

                cmdStr = " ".join(cmd)
                log.debug("launching sub process command: %s", cmdStr)
                p = subprocess.Popen(cmdStr,
                                shell=True)
                out, err = p.communicate()
                p.wait()
                if p.returncode:
                    raise ZenPackException('Error installing the egg (%s): %s' %
                                           (p.returncode, err))
                dmd._p_jar.sync()
            else:
                dmd.ZenPackManager.packs._setObject(packName, zenPack)
                zenPack = dmd.ZenPackManager.packs._getOb(packName)
                #hack because ZenPack.install is overridden by a lot of zenpacks
                #so we can't change the signature of install to take the
                #previousVerison
                zenPack.prevZenPackVersion = previousVersion
                if ignoreServiceInstall:
                    ZenPack.ignoreServiceInstall = True
                zenPack.install(dmd)
                zenPack.prevZenPackVersion = None

            try:
                zenPack = dmd.ZenPackManager.packs._getOb(packName)
                for p in packables:
                    pId = p.getPrimaryId()
                    try:
                        # make sure packable still exists; could be deleted by a
                        # migrate
                        getObjByPath(dmd, pId)
                        log.debug("adding packable relation for id %s", pId)
                        zenPack.packables.addRelation(p)
                    except (KeyError, zExceptions.NotFound):
                        log.debug('did not find packable %s',pId)
            except AttributeError as e:
                # If this happens in the child process or during the non-upgrade
                # flow, reraise the exception
                if not runExternalZenpack:
                    raise

                # This specific error will occur when the version of the ZenPack
                # being installed subclasses Products.ZenModel.ZenPack, but the
                # previous version of the ZenPack did not.
                if str(e) == "'ZenPack' object has no attribute '__of__'":
                    zenPack = ZenPack(packName)
                else:
                    # This is the signature error of class-loading issues
                    # during zenpack upgrade.  The final state should be okay,
                    # except that modified packables may be lost.
                    message = "There has been an error during the post-" + \
                              "installation steps for the zenpack %s.  In " + \
                              "most cases, no further action is required.  If " + \
                              "issues persist, please reinstall this zenpack."
                    message = message % packName
                    log.warning( message )
                    raise NonCriticalInstallError( message )

            cleanupSkins(dmd)
            return zenPack, deferFileDeletion, existing
        else:
            return zenPack, False, True

    info = ReadZenPackInfo(dist)
    if ('compatZenossVers' in info):
        vers = info['compatZenossVers']
        if vers[0] in string.digits:
            vers = '==' + vers
        try:
            req = pkg_resources.Requirement.parse('zenoss%s' % vers)
        except ValueError:
            raise ZenPackException("Couldn't parse requirement zenoss%s" % vers)
        if not req.__contains__(ZENOSS_VERSION):
            raise ZenPackException("Incompatible Zenoss Version %s, need %s" % (ZENOSS_VERSION, vers))

    ZenPack.currentServiceId = serviceId
    zenPack, deferFileDeletion, existing = transactional_actions()
    packInfos = {}
    oldPacksDump = getPacksDump()
    for pack in dmd.ZenPackManager.packs():
        try:
            eggPath = ""
            eggPath = pack.eggPath()
        except Exception:
            if pack.id in oldPacksDump:
                eggPath = oldPacksDump[pack.id]
        packInfos[pack.id] = {
            "id": pack.id,
            "version": pack.version,
            "dependencies": pack.dependencies,
            "eggPack": pack.eggPack,
            "eggPath": eggPath,
            "compatZenossVers": pack.compatZenossVers,
            "createdTime": pack.createdTime.ISO8601(),
        }
    atomicWrite(PACKS_DUMP, json.dumps(packInfos))

    if not filesOnly and deferFileDeletion:
        # We skipped deleting the existing files from filesystem
        # because maybe they'd be needed in migrate scripts.
        # Delete them now
        oldZpDir = os.path.join(Products.__path__[-1], existing.id)
        if os.path.islink(oldZpDir):
            os.remove(oldZpDir)
        else:
            shutil.rmtree(oldZpDir)

    return zenPack

def getPacksDump():
    packs = {}
    if os.path.isfile(PACKS_DUMP):
        with open(PACKS_DUMP, "r") as f:
            return json.load(f)
    return packs

def DiscoverEggs(dmd, zenPackId):
    """
    Find installed eggs that provide a zenoss.zenpacks entry point.
    Return a list of distributions whose ZenPacks need to be installed
    or upgraded.  The list is sorted into the order in which this needs to
    happen.
    """
    # Create a set of all available zenoss.zenpack entries that aren't
    # already installed in zenoss or need to be upgraded in zenoss.
    entries = set()
    parse_version = pkg_resources.parse_version
    for entry in pkg_resources.iter_entry_points(ZENPACK_ENTRY_POINT):
        packName = entry.name
        packVers = entry.dist.version
        existing = dmd.ZenPackManager.packs._getOb(packName, None)
        if existing and existing.isEggPack():
            # We use >= to allow migrate to be run on currently installed
            # zenpacks whose version has been changed or for whom new
            # migrates have been added.
            if parse_version(packVers) >= parse_version(existing.version):
                entries.add(entry)
        else:
            entries.add(entry)

    # Starting with the entry representing zenPackId create a list of
    # all entrypoints

    # orderedEntries lists entries in the opposite order of that in which
    # they need to be installed.  This is simply for convenience of using
    # .append() in code below.
    orderedEntries = []
    entriesByName = dict((e.name, e) for e in entries)

    def AddEntryAndProcessDeps(e):
        orderedEntries.append(e)
        for name in [r.project_name for r in e.dist.requires()]:
            if name in [e.name for e in orderedEntries]:
                # This entry depends on something that we've already processed.
                # This might be a circular dependency, might not be.
                # We are just going to bail however.  This should be
                # very unusual and the user can install deps first to work
                # around.
                raise ZenPackException('Unable to resolve ZenPack dependencies.'
                    ' Try installing dependencies first.')
            if name in entriesByName:
                # The requirement is an entry that has not yet been processed
                # here.  Add it to the list of entries to install/upgrade.
                AddEntryAndProcessDeps(entriesByName[name])
            else:
                # The requirement is not in the entries generated above.
                # This either means that the dep is already installed (this
                # is likely) or that easy_install missed something and the dep
                # is not installed/available (this should be unlikely.)
                pass

    if zenPackId not in entriesByName:
        if zenPackId in dmd.ZenPackManager.packs.objectIds():
            return []
        else:
            raise ZenPackException('Unable to discover ZenPack named %s' %
                                    zenPackId)
    AddEntryAndProcessDeps(entriesByName[zenPackId])
    orderedEntries.reverse()
    return [e.dist for e in orderedEntries]


def AddDistToWorkingSet(distPath):
    """
    Given the path to a dist (an egg) add it to the current working set.
    This is basically a pkg_resources-friendly way of adding it to
    sys.path.
    Return a list of all distributions on distPath that appear to
    be ZenPacks.
    """
    zpDists = []
    for d in pkg_resources.find_distributions(distPath):
        pkg_resources.working_set.add(d, replace=True)
        pkg_resources.require(d.project_name)
        if d.project_name.startswith('ZenPacks.'):
            zpDists.append(d)
    return zpDists


def ReadZenPackInfo(dist):
    """
    Return a dictionary containing the egg metadata
    """
    info = {}
    if dist.has_metadata('PKG-INFO'):
        lines = dist.get_metadata('PKG-INFO')
        for line in pkg_resources.yield_lines(lines):
            key, value = line.split(':', 1)
            info[key.strip()] = value.strip()
    if dist.has_metadata('zenpack_info'):
        lines = dist.get_metadata('zenpack_info')
        for line in pkg_resources.yield_lines(lines):
            key, value = line.split(':', 1)
            info[key.strip()] = value.strip()
    return info


def CopyMetaDataToZenPackObject(dist, pack):
    """
    Copy metadata type stuff from the distribution to the zp object.
    """
    # Version
    pack.version = dist.version

    # Egg Info
    info = ReadZenPackInfo(dist)
    pack.author = info.get('Author', '')
    if pack.author == 'UNKNOWN':
        pack.author = ''

    pack.license = info.get('License', '')
    if pack.license == 'UNKNOWN':
        pack.license = ''

    pack.compatZenossVers = info.get('compatZenossVers', '')
    pack.prevZenPackName = info.get('prevZenPackName', '')

    # Requires
    pack.dependencies = {}
    for r in dist.requires():
        name = r.project_name
        spec = str(r)[len(name):]
        pack.dependencies[name] = spec


def CreateZenPacksDir():
    """
    Make sure $ZENHOME/ZenPacks exists
    """
    zpDir = zenPath('ZenPacks')
    if not os.path.isdir(zpDir):
        os.mkdir(zpDir, 0o750)


def DoEasyInstall(eggPath):
    """
    Use easy_install to install an egg from the filesystem.
    easy_install will install the egg, but does not install it into
    Zenoss as ZenPacks.
    Returns a list of distributions that were installed that appear
    to be ZenPacks.
    """
    from setuptools.command import easy_install
    
    # Make sure $ZENHOME/ZenPacks exists
    CreateZenPacksDir()
    
    # Create temp file for easy_install to write results to
    _, tempPath = tempfile.mkstemp(prefix='zenpackcmd-easyinstall')
    # eggPaths is a set of paths to eggs that were installed.  We need to
    # add them to the current workingset so we can discover their
    # entry points.
    eggPaths = set()
    try:
        # Execute the easy_install
        args = ['--site-dirs', zenPath('ZenPacks'),
            '-d', zenPath('ZenPacks'),
            '--allow-hosts', 'None',
            '--record', tempPath,
            '--quiet',
            eggPath]
        easy_install.main(args)
        # Collect the paths for eggs that were installed
        f = open(tempPath, 'r')
        marker = '.egg/'
        markerOffset = len(marker)-1
        for l in f.readlines():
            i = l.find(marker)
            if i > 0:
                eggPaths.add(l[:i+markerOffset])
    finally:
        os.remove(tempPath)
    # Add any installed eggs to the current working set
    zpDists = []
    for path in eggPaths:
        zpDists += AddDistToWorkingSet(path)
    return zpDists



def ExportZenPack(dmd, packName):
    """
    Export the zenpack to $ZENHOME/export
    """
    zp = dmd.ZenPackManager.packs._getOb(packName, None)
    if not zp:
        raise ZenPackException('No ZenPack named %s' % packName)

    # Export the zenpack
    return zp.manage_exportPack()

########################################
#   Zenoss.Net
########################################


def FetchAndInstallZenPack(dmd, zenPackName, sendEvent=True):
    """
    Fetch the named zenpack and all its dependencies and install them.
    Return a list of the ZenPacks that were installed.
    """
    zenPacks = []
    try:
        zpDists = FetchZenPack(dmd, zenPackName)
        for d in zpDists:
            zenPacks.append(InstallDistAsZenPack(dmd, d, d.location))
    except Exception as ex:
        log.exception("Error fetching ZenPack %s", zenPackName)
        if sendEvent:
            ZPEvent(dmd, SEVERITY_ERROR, 'Failed to install ZenPack %s' % zenPackName,
                '%s: %s' % sys.exc_info()[:2])

        raise ex
    if sendEvent:
        zenPackIds = [z.id for z in zenPacks]
        if zenPackIds:
            ZPEvent(dmd, 2, 'Installed ZenPacks: %s' % ', '.join(zenPackIds))
        if zenPackName not in zenPackIds:
            ZPEvent(dmd, SEVERITY_ERROR, 'Unable to install ZenPack %s' % zenPackName)
    return zenPacks


def FetchZenPack(dmd, zenPackName):
    """
    Use easy_install to retrieve the given zenpack and any dependencies.
    easy_install will install the eggs, but does not install them into
    Zenoss as ZenPacks.
    Return a list of distributions just installed that appear to be
    ZenPacks.

    NB: This should be refactored.  It shares most of its code with
    DoEasyInstall()
    """
    from setuptools.command import easy_install

    # Make sure $ZENHOME/ZenPacks exists
    CreateZenPacksDir()

    # Create the proper package index URL.
    index_url = '%s/%s/%s/' % (
        ZENPACKS_BASE_URL, dmd.uuid, ZVersion.VERSION)

    # Create temp file for easy_install to write results to
    _, tempPath = tempfile.mkstemp(prefix='zenpackcmd-easyinstall')
    # eggPaths is a set of paths to eggs that were installed.  We need to
    # add them to the current workingset so we can discover their
    # entry points.
    eggPaths = set()
    try:
        # Execute the easy_install
        args = [
            '--site-dirs', zenPath('ZenPacks'),
            '-d', zenPath('ZenPacks'),
            '-i', index_url,
            '--allow-hosts', urlparse(index_url).hostname,
            '--record', tempPath,
            '--quiet',
            zenPackName]
        easy_install.main(args)
        # Collect the paths for eggs that were installed
        f = open(tempPath, 'r')
        marker = '.egg/'
        markerOffset = len(marker) - 1
        for l in f.readlines():
            i = l.find(marker)
            if i > 0:
                eggPaths.add(l[:i + markerOffset])
    finally:
        os.remove(tempPath)
    # Add any installed eggs to the current working set
    zpDists = []
    for path in eggPaths:
        zpDists += AddDistToWorkingSet(path)
    return zpDists


def UploadZenPack(dmd, packName, project, description, znetUser, znetPass):
    """
    Upload the specified zenpack to the given project.
    Project is a string of the form 'enterprise/myproject' or
    'community/otherproject'.
    """
    zp = dmd.ZenPackManager.packs._getOb(packName, None)
    if not zp:
        raise ZenPackException('No ZenPack named %s' % packName)

    # Export the zenpack
    fileName = zp.manage_exportPack()

    # Login to Zenoss.net
    from DotNetCommunication import DotNetSession
    session = DotNetSession()
    session.login(znetUser, znetPass)

    # Upload
    zpFile = open(zenPath('export', fileName), 'r')
    try:
        response = session.open('%s/createRelease' % project.strip('/'), {
                'description': description,
                'fileStorage': zpFile,
                })
    finally:
        zpFile.close()
    if response:
        result = response.read()
        if "'success':true" not in result:
            raise ZenPackException('Upload failed')
    else:
        raise ZenPackException('Failed to connect to Zenoss.net')
    return


########################################
#   ZenPack Removal
########################################


def RemoveZenPack(dmd, packName, filesOnly=False, skipDepsCheck=False,
                    leaveObjects=False, sendEvent=True, 
                    forceNoFileDeletion=False, uninstallEgg=True):
    """
    Remove the given ZenPack from Zenoss.
    Whether the ZenPack will be removed from the filesystem or not
    depends on the result of the ZenPack's shouldDeleteFilesOnRemoval method.
    """
    try:
        if filesOnly:
            skipDepsCheck = True

        # Check for dependency implications here?
        if not skipDepsCheck:
            deps = GetDependents(dmd, packName)
            if deps:
                raise ZenPackDependentsException('%s cannot be removed ' % packName +
                        'because it is required by %s' % ', '.join(deps))

        if not filesOnly:
            # Fetch the zenpack, call its remove() and remove from packs
            zp = None
            try:
                zp = dmd.ZenPackManager.packs._getOb(packName)
            except AttributeError as ex:
                raise ZenPackNotFoundException('No ZenPack named %s is installed' %
                                                packName)
            # If zencatalog hasn't finished yet, we get ugly messages that don't
            # mean anything. Hide them.
            logFilter = None
            if not getattr(dmd.zport, '_zencatalog_completed', False):
                logFilter = CatalogLoggingFilter()
                logging.getLogger('Zope.ZCatalog').addFilter(logFilter)
            try:
                zp.remove(dmd, leaveObjects)
                dmd.ZenPackManager.packs._delObject(packName)
                transaction.commit()
            finally:
                # Remove our logging filter so we don't hide anything important
                if logFilter is not None:
                    logging.getLogger('Zope.ZCatalog').removeFilter(logFilter)

        # Uninstall the egg and possibly delete it
        # If we can't find the distribution then apparently the zp egg itself is
        # missing.  Continue on with the removal and swallow the
        # DistributionNotFound exception
        try:
            dist = zp.getDistribution()
        except pkg_resources.DistributionNotFound:
            dist = None
        if dist:
            # Determine deleteFiles before develop -u gets called.  Once
            # it is called the egg has problems figuring out some of it's state.
            deleteFiles = zp.shouldDeleteFilesOnRemoval()
            if uninstallEgg:
                if zp.isDevelopment():
                    zenPackDir = varPath('ZenPacks')
                    cmd = ('%s setup.py develop -u '
                            % binPath('python') +
                            '--site-dirs=%s ' % zenPackDir +
                            '-d %s' % zenPackDir)
                    p = subprocess.Popen(cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        shell=True,
                                        cwd=zp.eggPath())
                    out, err = p.communicate()
                    code = p.wait()
                    if code:
                        raise ZenPackException(err)
                else:
                    DoEasyUninstall(packName)
            # elif cleanupEasyInstallPth:
            #     # Do we need to call easy_install -m here?  It causes problems
            #     # because it tries to install deps.  Cleanup easy-install.pth
            #     # ourselves instead.
            #     # We don't want to cleanup easy-install.pth when a newer
            #     # version of the egg has already been installed (when doing
            #     # an upgrade or installing in new location.)
            #     eggLink = './%s' % zp.eggName()
            #     CleanupEasyInstallPth(eggLink)
            if deleteFiles and not forceNoFileDeletion:
                eggDir = zp.eggPath()
                if os.path.islink(eggDir):
                    os.remove(eggDir)
                else:
                    shutil.rmtree(eggDir)
        cleanupSkins(dmd)
        transaction.commit()
    except ZenPackDependentsException as ex:
        log.error(ex)
    except Exception as ex:
        # Get that exception out there in case it gets blown away by ZPEvent
        log.exception("Error removing ZenPack %s", packName)
        if sendEvent:
            ZPEvent(dmd, SEVERITY_ERROR, 'Error removing ZenPack %s' % packName,
                '%s: %s' % sys.exc_info()[:2])

        # Don't just raise, because if ZPEvent blew away exception context
        # it'll be None, which is bad. This manipulates the stack to look like
        # this is the source of the exception, but we logged it above so no
        # info is lost.
        raise ex
    if sendEvent:
        ZPEvent(dmd, 2, 'Removed ZenPack %s' % packName)

    audit('Shell.ZenPack.Remove', packName)

def DoEasyUninstall(name):
    """
    Execute the easy_install command to unlink the given egg.
    What this is really doing is switching the egg to be in
    multiple-version mode, however this is the first step in deleting
    an egg as described here:
    http://peak.telecommunity.com/DevCenter/EasyInstall#uninstalling-packages
    """
    from setuptools.command import easy_install
    args = ['--site-dirs', zenPath('ZenPacks'),
        '-d', zenPath('ZenPacks'),
        #'--record', tempPath,
        '--quiet',
        '-m',
        name]

    #Try to run the easy install command.  If this fails with an attribute
    #error, then we know that easy_install doesn't know about this ZenPack and
    #we can continue normally

    try:
        easy_install.main(args)
    except AttributeError:
        log.info("%s not found by easy_install.  Continuing to remove.", name)
        pass


def CanRemoveZenPacks(dmd, packNames):
    """
    Returns a tuple of (canRemove, otherDependents)
    canRemove is True if the listed zenPacks have no dependents not also
    listed in packNames, False otherwise.
    otherDependents is a list of zenpack names not in packNames that
    depend on one or more of the packs in packNames.
    """
    unhappy = set()
    for name in packNames:
        deps = GetDependents(dmd, name)
        unhappy.update(set(dep for dep in deps if dep not in packNames))
    return (not unhappy, list(unhappy))


# def CleanupEasyInstallPth(eggLink):
#     """
#     Remove the entry for the given egg from the 
#     $ZENHOME/ZenPacks/easy-install.pth file.  If this entry is left
#     in place in can cause problems during the next install of the same
#     egg.
#     """
#     # Remove the path from easy-install.pth
#     eggTail = os.path.split(eggLink)[1]
#     easyPth = zenPath('ZenPacks', 'easy-install.pth')
#     if os.path.isfile(easyPth):
#         needToWrite = False
#         newLines = []
#         f = open(easyPth, 'r')
#         for line in f:
#             if os.path.split(line.strip())[1] == eggTail:
#                 needToWrite = True
#             else:
#                 newLines.append(line)
#         f.close()
#         if needToWrite:
#             f = open(easyPth, 'w')
#             f.writelines(newLines)
#             f.close()


def GetDependents(dmd, packName):
    """
    Return a list of installed ZenPack ids that list packName as a dependency
    """
    return [zp.id for zp in dmd.ZenPackManager.packs()
                if zp.id != packName and packName in zp.dependencies]


########################################
#   __main__, dispatching, etc
########################################


def ZPEvent(dmd, severity, summary, message=None):
    """
    Send an event to Zenoss.
    """
    dmd.ZenEventManager.sendEvent(dict(
        device=FQDN,
        eventClass='/Unknown',
        severity=severity,
        summary=summary,
        message=message))


class ZenPackCmd(ZenScriptBase):
    """
    Utilities for creating, installing, removing ZenPacks.

    NOTE: Users will probably invoke zenpack from the command line, which
    runs zenpack.py rather than this file.  zenpack.py calls functions
    in this module when it detects that new-style (egg) ZenPacks are involved.
    The plan is that once support for old-style (non-egg) ZenPacks is dropped
    zenpack.py can go away and this will take its place.  Until then this
    script can be invoked directly via the zenpackcmd script if desired.
    Invoking this script directly has the benefit of slightly better
    progress/status output to stdout.
    """

    def run(self):
        """
        Execute the user's request.
        """

        self.connect()
        def PrintInstalled(installed, eggOnly=False):
            if installed:
                if eggOnly:
                    names = [i['id'] for i in installed]
                    what = 'ZenPack egg'
                else:
                    names = [i.id for i in installed]
                    what = 'ZenPack'
                print('Installed %s%s: %s' % (
                        what,
                        len(names) != 1 and 's' or '',
                        ', '.join(names)))
            else:
                print('No ZenPacks installed.')

        if not getattr(self.dmd, 'ZenPackManager', None):
            raise ZenPackNeedMigrateException('Your Zenoss database appears'
                ' to be out of date. Try running zenmigrate to update.')
        if self.options.eggOnly and self.options.eggPath:
            zpDists = InstallEgg(self.dmd, self.options.eggPath, 
                                            link=self.options.link)
            PrintInstalled([{'id':d.project_name} for d in zpDists], 
                            eggOnly=True)
        if self.options.eggPath:
            installed = InstallEggAndZenPack(
                                self.dmd, self.options.eggPath,
                                link=self.options.link,
                                filesOnly=self.options.filesOnly,
                                previousVersion= self.options.previousVersion)
            PrintInstalled(installed)

        elif self.options.exportPack:
            return ExportZenPack(self.dmd, self.options.exportPack)

        elif self.options.fetch:
            installed = FetchAndInstallZenPack(self.dmd, self.options.fetch)
            PrintInstalled(installed)
        elif self.options.upload:
            return UploadZenPack(self.dmd, self.options.upload,
                                    self.options.znetProject,
                                    self.options.uploadDesc,
                                    self.options.znetUser,
                                    self.options.znetPass)
        elif self.options.removePackName:
            try:
                RemoveZenPack(self.dmd, self.options.removePackName)
                print('Removed ZenPack: %s' % self.options.removePackName)
            except ZenPackNotFoundException as e:
                sys.stderr.write(str(e) + '\n')
        elif self.options.list:
            self.list()
        else:
            self.parser.print_help()


    def buildOptions(self):
        self.parser.add_option('--export',
                               dest='exportPack',
                               default=None,
                               help="name of the pack to export")
        self.parser.add_option('--install',
                               dest='eggPath',
                               default=None,
                               help="name of the pack to install")
#        self.parser.add_option('--fetch',
#                               dest='fetch',
#                               default=None,
#                               help='Name of ZenPack to retrieve from '
#                                    'Zenoss.net and install.')
#        self.parser.add_option('--fetch-vers',
#                               dest='fetchVers',
#                               default=None,
#                               help='Use with --fetch to specify a version'
#                                    ' for the ZenPack to download and install.')
#        self.parser.add_option('--znet-user',
#                               dest='znetUser',
#                               default=None,
#                               help='Use with --fetch or --upload to specify'
#                                    ' your Zenoss.net username.')
#        self.parser.add_option('--znet-pass',
#                               dest='znetPass',
#                               default=None,
#                               help='Use with --fetch or --upload to specify'
#                                    ' your Zenoss.net password.')
#        self.parser.add_option('--upload',
#                               dest='upload',
#                               default=None,
#                               help='Name of ZenPack to upload to '
#                                    'Zenoss.net')
#        self.parser.add_option('--znet-project',
#                               dest='znetProject',
#                               default=None,
#                               help='Use with --upload to specify'
#                                    ' which Zenoss.net project to create'
#                                    ' a release on.')
#        self.parser.add_option('--upload-desc',
#                               dest='uploadDesc',
#                               default=None,
#                               help='Use with --upload to provide'
#                                    ' a description for the new release.')
        self.parser.add_option('--link',
                               dest='link',
                               action='store_true',
                               default=False,
                               help='Install the ZenPack in its current '
                                'location, do not copy to $ZENHOME/ZenPacks. '
                                'Also mark ZenPack as editable. '
                                'This only works with source directories '
                                'containing setup.py files, not '
                                'egg files.')
        self.parser.add_option('--remove',
                               dest='removePackName',
                               default=None,
                               help="name of the pack to remove")
        self.parser.add_option('--leave-objects',
                               dest='leaveObjects',
                               default=False,
                               action='store_true',
                               help="When specified with --remove then objects"
                                    ' provided by the ZenPack and those'
                                    ' depending on the ZenPack are not deleted.'
                                    ' This may result in broken objects in your'
                                    ' database unless the ZenPack is'
                                    ' reinstalled.')
        self.parser.add_option('--files-only',
                               dest='filesOnly',
                               action="store_true",
                               default=False,
                               help='install onto filesystem but not into '
                                        'zenoss')
        self.parser.add_option('--previousversion',
                               dest='previousVersion',
                               default=None,
                               help="Previous version of the zenpack;"
                                    ' used during upgrades')
        self.parser.prog = "zenpack"
        ZenScriptBase.buildOptions(self)


if __name__ == '__main__':
    try:
        zp = ZenPackCmd()
        zp.run()
    except ZenPackException as e:
        sys.stderr.write('%s\n' % str(e))
        sys.exit(-1)
