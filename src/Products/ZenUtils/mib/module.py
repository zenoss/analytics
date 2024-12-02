import logging
import os
from zExceptions import BadRequest

__all__ = ("MibOrganizerPath", "ModuleManager", "getMibModuleMap")

log = logging.getLogger("zen.mib")
BASE_PATH = "/zport/dmd/Mibs"


class MibOrganizerPath(object):
    """Encapsulates a MibModule's organizer path in DMD.
    """

    def __init__(self, path="/"):
        """Initialize an instance of MibOrganizerPath.

        The path value can be a path relative to /zport/dmd/Mibs
        or a full path starting from /zport.

        @param {str} Path to module.
        """
        if path[0:len(BASE_PATH)] != BASE_PATH:
            if path.startswith("/"):
                path = path[1:]
            path = os.path.join(BASE_PATH, path) if len(path) else BASE_PATH
        self._path = path
        relpath = self._path[len(BASE_PATH):]
        self._relpath = relpath if relpath else "/"

    @property
    def path(self):
        """Returns the full path of the organizer.
        """
        return self._path

    @property
    def relative_path(self):
        """Returns the relative path of the organizer.
        """
        return self._relpath


def getMibModuleMap(dmd):
    """Return a dict mapping module names to their organizer in DMD.

    @returns {dict str:MibOrganizerPath}
    """
    registry = {}
    for module in dmd.Mibs.getSubInstancesGen("mibs"):
        path = module.getPrimaryPath()
        organizerPath, moduleName = "/".join(path[:-2]), path[-1]
        registry[moduleName] = MibOrganizerPath(organizerPath)
    return registry


_MODULE_ATTRIBUTES = ('language', 'contact', 'description')


def _getModuleAttributes(data):
    """Generates key/value pairs of the modules attributes.
    """
    for key in (k for k in _MODULE_ATTRIBUTES if k in data):
        yield (key, data.get(key))


class ModuleManager(object):
    """Manages the adding, updating, and deletion of MIB modules in DMD.
    """

    def __init__(self, dmd, registry):
        """Initialize an instance of ModuleManager.

        @param registry {dict} Initial module to organizer mapping.
        @param organizer {MibOrganizerPath} Add MibModules to this organizer.
        """
        self._dmd = dmd
        self._registry = registry
        self._organizers = set(self._registry.values())

    def add(self, module, organizer):
        """Add MIB module to DMD.
        """
        # 1. Add module to path if module doesn't already exist on some path.
        # 2. Add/update module attributes
        # 3. Add module nodes
        # 4. Add module notifications

        moduleName = module.get("moduleName")
        attributes = module.get(moduleName, {})
        isNew, mibmod = self._getMibModule(moduleName, organizer)

        for attr, value in _getModuleAttributes(attributes):
            setattr(mibmod, attr, value)

        nodecount = 0
        for name, values in module.get("nodes", {}).iteritems():
            self._addItem(
                mibmod.createMibNode, name, values, moduleName
            )
            nodecount += 1

        trapcount = 0
        for name, values in module.get("notifications", {}).iteritems():
            self._addItem(
                mibmod.createMibNotification, name, values, moduleName
            )
            trapcount += 1

        if isNew:
            log.info(
                "Created %s with %s nodes and %s notifications",
                '/'.join(mibmod.getPrimaryPath()), nodecount, trapcount
            )
        else:
            log.info(
                "Updated %s nodes and %s notifications on %s",
                nodecount, trapcount, '/'.join(mibmod.getPrimaryPath())
            )

    def _getMibModule(self, name, default_organizer):
        current_organizer = self._registry.get(name)
        if current_organizer:
            return (
                False,
                self._dmd.unrestrictedTraverse(
                    current_organizer.path + "/mibs/" + name
                )
            )
        return (
            True,
            self._dmd.Mibs.createMibModule(
                name, default_organizer.relative_path
            )
        )

    def _addItem(self, function, name, values, moduleName):
        try:
            function(name, logger=log, **values)
        except BadRequest:
            self.log.warn(
                "Unable to add %s id '%s' as this name is "
                "reserved for use by Zope", "node", name
            )
            newName = '_'.join([name, moduleName])
            self.log.warn(
                "Trying to add %s '%s' as '%s'",
                "node", name, newName
            )
            try:
                function(newName, logger=log, **values)
            except Exception:
                self.log.warn(
                    "Unable to add %s id '%s' -- skipping",
                    "node", newName
                )
            else:
                self.log.warn(
                    "Renamed '%s' to '%s' and added to MIB %s",
                    name, newName, "node"
                )
