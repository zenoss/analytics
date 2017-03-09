##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from twisted.internet import defer
from twisted.spread import pb
import logging
import hashlib
import base64

from Acquisition import aq_parent
from zope import component
from ZODB.transact import transact

from cryptography.fernet import Fernet
from Products.ZenHub.HubService import HubService
from Products.ZenHub.PBDaemon import translateError
from Products.ZenHub.services.Procrastinator import Procrastinate
from Products.ZenHub.services.ThresholdMixin import ThresholdMixin
from Products.ZenHub.zodb import onUpdate, onDelete
from Products.ZenHub.interfaces import IBatchNotifier

from Products.ZenCollector.interfaces import IConfigurationDispatchingFilter
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenModel.ZenPack import ZenPack
from Products.ZenModel.ThresholdClass import ThresholdClass
from Products.ZenModel.privateobject import is_private
from Products.ZenUtils.AutoGCObjectReader import gc_cache_every
from Products.ZenUtils.picklezipper import Zipper
from Products.Zuul.utils import safe_hasattr as hasattr


class DeviceProxy(pb.Copyable, pb.RemoteCopy):
    def __init__(self):
        """
        Do not use base classes initializers
        """

    @property
    def configId(self):
        """
        This is the id used by the framework to keep track of configurations,
        what to run, delete etc...
        Use this instead of id since certain daemons can use a
        configuration id that is different than the underlying device id.
        """
        retval = getattr(self, "_config_id", None)
        return retval if (retval is not None) else self.id

    @property
    def deviceGuid(self):
        """
        """
        return getattr(self, "_device_guid", None)


    def __str__(self):
        return self.id

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.id)

pb.setUnjellyableForClass(DeviceProxy, DeviceProxy)


# TODO: doc me!
BASE_ATTRIBUTES = ('id',
                   'manageIp',
                   )


class CollectorConfigService(HubService, ThresholdMixin):
    def __init__(self, dmd, instance, deviceProxyAttributes=()):
        """
        Constructs a new CollectorConfig instance.

        Subclasses must call this __init__ method but cannot do so with
        the super() since parents of this class are not new-style classes.

        @param dmd: the Zenoss DMD reference
        @param instance: the collector instance name
        @param deviceProxyAttributes: a tuple of names for device attributes
               that should be copied to every device proxy created
        @type deviceProxyAttributes: tuple
        """
        HubService.__init__(self, dmd, instance)

        self._deviceProxyAttributes = BASE_ATTRIBUTES + deviceProxyAttributes

        # Get the collector information (eg the 'localhost' collector)
        self._prefs = self.dmd.Monitors.Performance._getOb(self.instance)
        self.config = self._prefs # TODO fix me, needed for ThresholdMixin
        self.configFilter = None

        # When about to notify daemons about device changes, wait for a little
        # bit to batch up operations.
        self._procrastinator = Procrastinate(self._pushConfig)
        self._reconfigProcrastinator = Procrastinate(self._pushReconfigure)

        self._notifier = component.getUtility(IBatchNotifier)

    def _wrapFunction(self, functor, *args, **kwargs):
        """
        Call the functor using the arguments, and trap any unhandled exceptions.

        @parameter functor: function to call
        @type functor: method
        @parameter args: positional arguments
        @type args: array of arguments
        @parameter kwargs: keyword arguments
        @type kwargs: dictionary
        @return: result of functor(*args, **kwargs) or None if failure
        @rtype: result of functor
        """
        try:
            return functor(*args, **kwargs)
        except (SystemExit, KeyboardInterrupt): raise
        except Exception, ex:
            msg = 'Unhandled exception in zenhub service %s: %s' % (
                      self.__class__, str(ex))
            self.log.exception(msg)

            import traceback
            from Products.ZenEvents.ZenEventClasses import Critical

            evt = dict(
                severity=Critical,
                component=str(self.__class__),
                traceback=traceback.format_exc(),
                summary=msg,
                device=self.instance,
                methodCall="%s(%s, %s)" % (functor.__name__, args, kwargs)
            )
            self.sendEvent(evt)
        return None

    @onUpdate(PerformanceConf)
    def perfConfUpdated(self, object, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            if object.id == self.instance:
                for listener in self.listeners:
                    listener.callRemote('setPropertyItems', object.propertyItems())

    @onUpdate(ZenPack)
    def zenPackUpdated(self, object, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            for listener in self.listeners:
                try:
                    listener.callRemote('updateThresholdClasses',
                                        self.remote_getThresholdClasses())
                except Exception, ex:
                    self.log.warning("Error notifying a listener of new classes")

    @onUpdate(Device)
    def deviceUpdated(self, object, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            self._notifyAll(object)

    @onUpdate(None) # Matches all
    def notifyAffectedDevices(self, object, event):
        # FIXME: This is horrible
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            if isinstance(object, self._getNotifiableClasses()):
                self._reconfigureIfNotify(object)
            else:
                if isinstance(object, Device):
                    return
                # something else... mark the devices as out-of-date
                template = None
                while object:
                    # Don't bother with privately managed objects; the ZenPack
                    # will handle them on its own
                    if is_private(object):
                        return
                    # walk up until you hit an organizer or a device
                    if isinstance(object, RRDTemplate):
                        template = object
                    if isinstance(object, DeviceClass):
                        uid = (self.__class__.__name__, self.instance)
                        devfilter = None
                        if template:
                            def hasTemplate(device):
                                if issubclass(template.getTargetPythonClass(), Device):
                                    result = template in device.getRRDTemplates()
                                    if result:
                                        self.log.debug("%s bound to template %s", device.getPrimaryId(), template.getPrimaryId())
                                    else:
                                        self.log.debug("%s not bound to template %s", device.getPrimaryId(), template.getPrimaryId())
                                    return result
                                else:
                                    # check components, Too expensive?
                                    for comp in device.getMonitoredComponents(type=template.getTargetPythonClass().meta_type):
                                        result = template in comp.getRRDTemplates()
                                        if result:
                                            self.log.debug("%s bound to template %s", comp.getPrimaryId(), template.getPrimaryId())
                                            return True
                                        else:
                                            self.log.debug("%s not bound to template %s", comp.getPrimaryId(), template.getPrimaryId())
                                    return False
                            devfilter = hasTemplate
                        self._notifier.notify_subdevices(object, uid, self._notifyAll, devfilter)
                        break

                    if isinstance(object, Device):
                        self._notifyAll(object)
                        break

                    object = aq_parent(object)

    @onDelete(Device)
    def deviceDeleted(self, object, event):
        with gc_cache_every(1000, db=self.dmd._p_jar._db):
            devid = object.id
            collector = object.getPerformanceServer().getId()
            # The invalidation is only sent to the collector where the deleted device was
            if collector == self.instance:
                self.log.debug('Invalidation: Performing remote call to delete device {0} from collector {1}'.format(devid, self.instance))
                for listener in self.listeners:
                    listener.callRemote('deleteDevice', devid)
            else:
                self.log.debug('Invalidation: Skipping remote call to delete device {0} from collector {1}'.format(devid, self.instance))


    @translateError
    def remote_getConfigProperties(self):
        return self._prefs.propertyItems()

    @translateError
    def remote_getDeviceNames(self, options=None):
        devices = self._getDevices(deviceFilter=self._getOptionsFilter(options))
        return [x.id for x in self._filterDevices(devices)]

    def _getDevices(self, deviceNames=None, deviceFilter=None):

        if not deviceNames:
            devices = filter(deviceFilter, self._prefs.devices())
        else:
            devices = []
            for name in deviceNames:
                device = self.dmd.Devices.findDeviceByIdExact(name)
                if not device:
                    continue
                else:
                    if deviceFilter(device):
                        devices.append(device)
        return devices

    @translateError
    def remote_getDeviceConfigs(self, deviceNames=None, options=None):
        deviceFilter = self._getOptionsFilter(options)
        devices = self._getDevices(deviceNames, deviceFilter)
        devices = self._filterDevices(devices)

        deviceConfigs = []
        for device in devices:
            proxies = self._wrapFunction(self._createDeviceProxies, device)
            if proxies:
                deviceConfigs.extend(proxies)

        self._wrapFunction(self._postCreateDeviceProxy, deviceConfigs)
        return deviceConfigs

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
        collector = self.getPerformanceMonitor()
        key = getattr(self.getPerformanceMonitor(), "_encryption_key", self._create_encryption_key())

        # Hash the key with the daemon identifier to get unique key per collector daemon
        s = hashlib.sha256()
        s.update(key)
        s.update(self.__class__.__name__)
        s.update(self.instance)
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

        @param device: the regular device object to create a proxy from
        @return: a new device proxy object, or None if no proxy can be created
        @rtype: DeviceProxy
        """
        proxy = proxy if (proxy is not None) else DeviceProxy()

        # copy over all the attributes requested
        for attrName in self._deviceProxyAttributes:
            setattr(proxy, attrName, getattr(device, attrName, None))

        if isinstance(device, Device):
            from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
            guid = IGlobalIdentifier(device).getGUID()
            if guid:
                setattr(proxy,'_device_guid', guid)
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
            return device.monitorDevice() and \
                   (not self.configFilter or self.configFilter(device))
        except AttributeError as e:
            self.log.warn("got an attribute exception on device.monitorDevice()")
            self.log.debug(e)
        return False

    def _getOptionsFilter(self, options):
        deviceFilter = lambda x: True
        if options:
            dispatchFilterName = options.get('configDispatch', '') if options else ''
            filterFactories = dict(component.getUtilitiesFor(IConfigurationDispatchingFilter))
            filterFactory = filterFactories.get(dispatchFilterName, None) or \
                            filterFactories.get('', None)
            if filterFactory:
                deviceFilter = filterFactory.getFilter(options) or deviceFilter
        return deviceFilter


    def _filterDevices(self, devices):
        """
        Filters out devices from the provided list that should not be
        converted into DeviceProxy instances and sent back to the collector
        client.

        @param device: the device object to filter
        @return: a list of devices that are to be included
        @rtype: list
        """
        filteredDevices = []

        for dev in filter(None, devices):
            try:
                device = dev.primaryAq()

                if self._perfIdFilter(device) and self._filterDevice(device):
                    filteredDevices.append(device)
                    self.log.debug("Device %s included by filter", device.id)
                else:
                    # don't use .id just in case there is something crazy returned
                    self.log.debug("Device %r excluded by filter", device)
            except Exception as e:
                if self.log.isEnabledFor(logging.DEBUG):
                    self.log.exception("Got an exception filtering %r", dev)
                else:
                    self.log.warn("Got an exception filtering %r", dev)
        return filteredDevices

    def _perfIdFilter(self, obj):
        """
        Return True if obj is not a device (has no perfServer attribute)
        or if the device's associated monitor has a name matching this
        collector's name.  Otherise, return False.
        """
        return (not hasattr(obj, 'perfServer')
                or obj.perfServer.getRelatedId() == self.instance)

    def _notifyAll(self, object):
        """
        Notify all instances (daemons) of a change for the device
        """
        # procrastinator schedules a call to _pushConfig
        self._procrastinator.doLater(object)

    def _pushConfig(self, device):
        """
        push device config and deletes to relevent collectors/instances
        """
        deferreds = []

        if self._perfIdFilter(device) and self._filterDevice(device):
            proxies = self._wrapFunction(self._createDeviceProxies, device)
            if proxies:
                self._wrapFunction(self._postCreateDeviceProxy, proxies)
        else:
            proxies = None

        prev_collector = device.dmd.Monitors.primaryAq().getPreviousCollectorForDevice(device.id)
        for listener in self.listeners:
            if not proxies:
                if hasattr(device, 'getPerformanceServer'):
                    # The invalidation is only sent to the previous and current collectors
                    if self.instance in ( prev_collector, device.getPerformanceServer().getId() ):
                        self.log.debug('Invalidation: Performing remote call for device {0} on collector {1}'.format(device.id, self.instance))
                        deferreds.append(listener.callRemote('deleteDevice', device.id))
                    else:
                        self.log.debug('Invalidation: Skipping remote call for device {0} on collector {1}'.format(device.id, self.instance))
                else:
                    deferreds.append(listener.callRemote('deleteDevice', device.id))
                    self.log.debug('Invalidation: Performing remote call for device {0} on collector {1}'.format(device.id, self.instance))
            else:
                options = self.listenerOptions.get(listener, None)
                deviceFilter = self._getOptionsFilter(options)
                for proxy in proxies:
                    if deviceFilter(proxy):
                        deferreds.append(self._sendDeviceProxy(listener, proxy))

        return defer.DeferredList(deferreds)

    def _sendDeviceProxy(self, listener, proxy):
        """
        TODO
        """
        return listener.callRemote('updateDeviceConfig', proxy)

    def sendDeviceConfigs(self, configs):
        deferreds = []

        def errback(failure):
            self.log.critical("Unable to update configs for service instance %s: %s"
                              % (self.__class__.__name__, failure))

        for listener in self.listeners:
            options = self.listenerOptions.get(listener, None)
            deviceFilter = self._getOptionsFilter(options)
            filteredConfigs = filter(deviceFilter, configs)
            args = Zipper.dump(filteredConfigs)
            d = listener.callRemote('updateDeviceConfigs', args).addErrback(errback)
            deferreds.append(d)
        return deferreds


    # FIXME: Don't use _getNotifiableClasses, use @onUpdate(myclasses)
    def _getNotifiableClasses(self):
        """
        a tuple of classes. When any object of a type in the sequence is
        modified the collector connected to the service will be notified to
        update its configuration

        @rtype: tuple
        """
        return ()

    def _pushReconfigure(self, value):
        """
        notify the collector to reread the entire configuration
        """
        #value is unused but needed for the procrastinator framework
        for listener in self.listeners:
            listener.callRemote('notifyConfigChanged')
        self._reconfigProcrastinator.clear()

    def _reconfigureIfNotify(self, object):
        ncc = self._notifyConfigChange(object)
        self.log.debug("services/config.py _reconfigureIfNotify object=%r _notifyConfigChange=%s" % (object, ncc))
        if ncc:
            self.log.debug('scheduling collector reconfigure')
            self._reconfigProcrastinator.doLater(True)

    def _notifyConfigChange(self, object):
        """
        Called when an object of a type from _getNotifiableClasses is
        encountered
        @return: should a notify config changed be sent
        @rtype: boolean
        """
        return True


class NullConfigService(CollectorConfigService):
    """
    The collector framework requires a configuration service, but some
    daemons do not need any configuration.
    """
    def __init__(self, dmd, instance):
        CollectorConfigService.__init__(self, dmd, instance)

    def _filterDevices(self, deviceList):
        return []
