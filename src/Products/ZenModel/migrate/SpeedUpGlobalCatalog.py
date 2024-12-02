##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""
Need to make the following three changes to the global catalog
   1. Remove Interfaces from Object Implements
      This was causing the index to be too large and was not necessary
   2. Make sure only System, Location, Group and DeviceClasses paths are
      available for devices in the path index
   3. Remove Software and Operating Systems from the catalog
"""
from zope.dottedname.resolve import resolve
from zope.interface import Interface
from Products.ZenModel.Device import Device
from Products.Zuul.interfaces import ICatalogTool
from Products.ZenModel.Software import Software
from Products.ZenModel.OperatingSystem import OperatingSystem
import Migrate


import logging
log = logging.getLogger("zen.migrate")


class DummyDevice(object):

    def __init__(self, brain):
        self.brain = brain

    def getPrimaryPath(self):
        return self.brain.getPath().split('/')

class SpeedUpGlobalCatalog(Migrate.Step):
    version = Migrate.Version(3, 0, 3)

    def shouldRemoveClass(self, classPath):
        """
        Returns true if this is an interface class that we should not index
        """
        # don't look it up if we have already
        if self._importedClasses.has_key(classPath):
            return self._importedClasses[classPath]
        # see if the class descends from Interface
        try:
            klass = resolve(classPath)
            self._importedClasses[classPath] = issubclass(klass, Interface)
        except ImportError:
            # be safe and not remove it
            self._importedClasses[classPath] = False
        return self._importedClasses[classPath]

    def removeClassesFromIndex(self, rid, idx):
        """
        Removes every class in self.removeClasses
        from the index specified by idx and the object
        specified by rid
        """
        classSet = idx._unindex[rid]
        for className in self.removedClasses:
            if classSet.has_key(className):
                classSet.remove(className)

    def removeInterfacesFromObjectImplements(self, dmd):
        """
        For every object keep track of which interfaces
        it implements and the remove it
        """
        self._importedClasses = {}
        self.removedClasses = set()
        idx = dmd.global_catalog._catalog.indexes['objectImplements']
        # unfortunately we have to go through every
        # item in the catalog
        for brain in dmd.global_catalog():
            has_classes = False
            rid = brain.getRID()
            # prune our interface paths
            for classPath in idx._unindex[rid]:
                if self.shouldRemoveClass(classPath):
                    has_classes = True
                    self.removedClasses.add(classPath)

            if has_classes:
                self.removeClassesFromIndex(rid, idx)

        # remove index for Interfaces clases
        for className in self.removedClasses:
            del idx._index[className]

    def keepDevicePath(self, path):
        """
        Only keep device paths if in systems locations groups or device class
        """
        if path.startswith(('Devices', 'Systems', 'Locations', 'Groups'), len('/zport/dmd/')):
            return True
        return False

    def cleanDevicePath(self, dmd):
        """
        Make sure only groups systems and locations and device classes
        are the only thing indexed by the path
        """
        cat = ICatalogTool(dmd)
        brains = cat.search(types=(Device,))
        idx = dmd.global_catalog._catalog.indexes['path']
        for brain in brains:
            badPaths = []
            for path in idx._unindex[brain.getRID()]:
                if not self.keepDevicePath(path):
                    badPaths.append(path)
            if badPaths:
                dmd.global_catalog.unindex_object_from_paths(DummyDevice(brain), badPaths)

    def removeSoftwareAndOperatingSystems(self, dmd):
        """
        Find everything that is an OperationSystem Or
        Software and unindex it
        """
        cat = ICatalogTool(dmd)
        brains = cat.search(types=(OperatingSystem,Software))
        for brain in brains:
            dmd.global_catalog.uncatalog_object(brain.getPath())
            
    def cutover(self, dmd):
        """
        """
        log.info("Removing Software and Operating Systems from catalog")
        self.removeSoftwareAndOperatingSystems(dmd)
        log.info("Removing Interfaces from 'objectImplements'")
        self.removeInterfacesFromObjectImplements(dmd)
        log.info("Cleaning Device Path")
        self.cleanDevicePath(dmd)

SpeedUpGlobalCatalog()
