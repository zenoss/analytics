import logging

from zope.interface import implementer

from Products.ZenCollector.interfaces import IConfigurationListener

log = logging.getLogger("zen.daemon.listeners")


@implementer(IConfigurationListener)
class DummyListener(object):
    """
    No-op implementation of a listener that can be registered with instances
    of ConfigListenerNotifier class.
    """

    def deleted(self, configurationId):
        log.debug("DummyListener: configuration %s deleted", configurationId)

    def added(self, configuration):
        log.debug("DummyListener: configuration %s added", configuration)

    def updated(self, newConfiguration):
        log.debug("DummyListener: configuration %s updated", newConfiguration)


@implementer(IConfigurationListener)
class ConfigListenerNotifier(object):
    """
    Registers other IConfigurationListener objects and notifies them when
    this object is notified of configuration removals, adds, and updates.
    """

    _listeners = []

    def addListener(self, listener):
        self._listeners.append(listener)

    def deleted(self, configurationId):
        """
        Notify listener when a configuration is deleted.

        :param configurationId: The ID of the deleted configuration.
        :type configurationId: str
        """
        for listener in self._listeners:
            listener.deleted(configurationId)

    def added(self, configuration):
        """
        Notify the listeners when a configuration is added.

        :param configuration: The added configuration object.
        :type configuration: DeviceProxy
        """
        for listener in self._listeners:
            listener.added(configuration)

    def updated(self, newConfiguration):
        """
        Notify the listeners when a configuration has changed.

        :param newConfiguration: The updated configuration object.
        :type newConfiguration: DeviceProxy
        """
        for listener in self._listeners:
            listener.updated(newConfiguration)


@implementer(IConfigurationListener)
class DeviceGuidListener(object):
    """
    Manages configuration IDs on the given 'daemon' object, making the
    necessary changes when notified of configuration additions, removals,
    and updates.
    """

    def __init__(self, daemon):
        """
        Initialize a DeviceGuidListener instance.

        :param daemon: The daemon object.
        :type daemon: CollectorDaemon
        """
        self._daemon = daemon

    def deleted(self, configurationId):
        self._daemon._deviceGuids.pop(configurationId, None)

    def added(self, configuration):
        deviceGuid = getattr(configuration, "deviceGuid", None)
        if deviceGuid:
            self._daemon._deviceGuids[configuration.id] = deviceGuid

    def updated(self, newConfiguration):
        deviceGuid = getattr(newConfiguration, "deviceGuid", None)
        if deviceGuid:
            self._daemon._deviceGuids[newConfiguration.id] = deviceGuid
