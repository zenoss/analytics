##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import base64
import hashlib
import logging

from cryptography.fernet import Fernet
from twisted.spread import pb
from ZODB.transact import transact

from Products.ZenHub.errors import translateError
from Products.ZenHub.HubService import HubService
from Products.ZenHub.services.ThresholdMixin import ThresholdMixin
from Products.ZenModel.Device import Device
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.Zuul.utils import safe_hasattr as hasattr

from .error import trapException
from .optionsfilter import getOptionsFilter
from .push import UpdateCollectorMixin


class DeviceProxy(pb.Copyable, pb.RemoteCopy):
    """Used to proxy device objects to collection services."""

    @property
    def configId(self):
        """
        This is the ID used by the framework to keep track of configurations,
        what to run, delete etc...

        Use this instead of `id` since certain daemons can use a
        configuration ID that is different than the underlying device ID.
        """
        cfgId = getattr(self, "_config_id", None)
        return cfgId if (cfgId is not None) else self.id

    @property
    def deviceGuid(self):
        return getattr(self, "_device_guid", None)

    def __eq__(self, other):
        if isinstance(other, DeviceProxy):
            return self.configId == other.configId
        return NotImplemented

    def __hash__(self):
        return hash(self.configId)

    def __str__(self):
        return self.configId

    def __repr__(self):
        return "%s:%s" % (self.__class__.__name__, self.configId)


pb.setUnjellyableForClass(DeviceProxy, DeviceProxy)


# Default attributes copied to every device proxy.
BASE_ATTRIBUTES = (
    "id",
    "manageIp",
)


class CollectorConfigService(HubService, UpdateCollectorMixin, ThresholdMixin):
    """Base class for ZenHub configuration service classes."""

    def __init__(self, dmd, instance, deviceProxyAttributes=()):
        """
        Initializes a CollectorConfigService instance.

        :param dmd: the Zenoss DMD reference
        :param instance: the collector instance name
        :param deviceProxyAttributes: a tuple of names for device attributes
            that should be copied to every device proxy created
        :type deviceProxyAttributes: tuple
        """
        HubService.__init__(self, dmd, instance)
        UpdateCollectorMixin.__init__(self)

        self._deviceProxyAttributes = BASE_ATTRIBUTES + deviceProxyAttributes

        # Get the collector information (eg the 'localhost' collector)
        self.conf = self.dmd.Monitors.getPerformanceMonitor(self.instance)

    @property
    def configFilter(self):
        return None

    @translateError
    def remote_getConfigProperties(self):
        try:
            items = self.conf.propertyItems()
        finally:
            pass
        return items

    @translateError
    def remote_getDeviceNames(self, options=None):
        return [
            device.id
            for device in self._selectDevices(self.conf.devices(), options)
        ]

    @translateError
    def remote_getDeviceConfigs(self, deviceNames=None, options=None):
        if deviceNames:
            devices = _getDevicesByName(self.dmd.Devices, deviceNames)
        else:
            devices = self.conf.devices()
        selected_devices = self._selectDevices(devices, options)
        configs = []
        for device in selected_devices:
            proxies = trapException(self, self._createDeviceProxies, device)
            if proxies:
                configs.extend(proxies)

        trapException(self, self._postCreateDeviceProxy, configs)
        return configs

    def _selectDevices(self, devices, options):
        # _selectDevices is a generator function returning Device objects.
        # `devices` is an iterator returning Device objects.
        # `options` is a dict-like object.
        predicate = getOptionsFilter(options)
        for device in devices:
            try:
                if all(
                    (
                        predicate(device),
                        self._perfIdFilter(device),
                        self._filterDevice(device),
                    )
                ):
                    yield device
            except Exception as ex:
                if self.log.isEnabledFor(logging.DEBUG):
                    method = self.log.exception
                else:
                    method = self.log.warn
                method("error filtering device %r: %s", device, ex)

    @transact
    def _create_encryption_key(self):
        # Double-check to make sure somebody else hasn't created it
        collector = self.getPerformanceMonitor()
        key = getattr(collector, "_encryption_key", None)
        if key is None:
            key = collector._encryption_key = Fernet.generate_key()
        return key

    @translateError
    def remote_getEncryptionKey(self):
        # Get or create an encryption key for this collector
        key = getattr(
            self.getPerformanceMonitor(),
            "_encryption_key",
            self._create_encryption_key(),
        )

        # Hash the key with the daemon identifier to get unique key
        # per collector daemon.
        s = hashlib.sha256()
        s.update(key)
        s.update(self.name())
        return base64.urlsafe_b64encode(s.digest())

    def _postCreateDeviceProxy(self, deviceConfigs):
        pass

    def _createDeviceProxies(self, device):
        proxy = self._createDeviceProxy(device)
        return (proxy,) if (proxy is not None) else ()

    def _createDeviceProxy(self, device, proxy=None):
        """
        Creates a device proxy object that may be copied across the network.

        Subclasses should override this method, call it for a basic DeviceProxy
        instance, and then add any additional data to the proxy as their needs
        require.

        :param device: the regular device object to create a proxy from
        :type device: Products.ZenModel.Device
        :return: a new device proxy object, or None if no proxy can be created
        :rtype: DeviceProxy
        """
        proxy = DeviceProxy() if proxy is None else proxy

        # copy over all the attributes requested
        for attrName in self._deviceProxyAttributes:
            setattr(proxy, attrName, getattr(device, attrName, None))

        if isinstance(device, Device):
            guid = IGlobalIdentifier(device).getGUID()
            if guid:
                proxy._device_guid = guid
        return proxy

    def _filterDevice(self, device):
        """
        Determines if the specified device should be included for consideration
        in being sent to the remote collector client.

        Subclasses should override this method, call it for the default
        filtering behavior, and then add any additional filtering as needed.

        @param device: the device object to filter
        @return: True if this device should be included for further processing
        @rtype: boolean
        """
        try:
            return device.monitorDevice() and (
                not self.configFilter or self.configFilter(device)
            )
        except AttributeError as e:
            self.log.warn("No such attribute  device=%r error=%s", device, e)
        return False

    def _perfIdFilter(self, obj):
        """
        Return True if obj is not a device (has no perfServer attribute)
        or if the device's associated monitor has a name matching this
        collector's name.  Otherise, return False.
        """
        return (
            not hasattr(obj, "perfServer")
            or obj.perfServer.getRelatedId() == self.instance
        )


def _getDevicesByName(ctx, names):
    # Returns a generator that produces Device objects.
    return (
        device
        for device in (ctx.findDeviceByIdExact(name) for name in names)
        if device is not None
    )


class NullConfigService(CollectorConfigService):
    """
    The collector framework requires a configuration service, but some
    daemons do not need any configuration.
    """

    def __init__(self, dmd, instance):
        CollectorConfigService.__init__(self, dmd, instance)

    def _filterDevices(self, deviceList):
        return []
