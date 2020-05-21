##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import time
from pprint import pformat
import sys
import traceback
import importlib

from twisted.spread import pb

from Products.ZenRRD.zencommand import Cmd, DataPointConfig
from Products.ZenUtils.Utils import importClass
from Products.DataCollector.DeviceProxy import DeviceProxy as ModelDeviceProxy
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenHub.PBDaemon import RemoteException
from Products.ZenUtils.debugtools import profile


from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource \
    import PythonDataSource
from ZenPacks.zenoss.PythonCollector.services.PythonConfig \
    import PythonDataSourceConfig

from .utils import replace_prefix, all_parent_dcs
from .utils.tales import talesEvalStr
from .applydatamapper import ApplyDataMapper
from .db import get_nub_db
from .zobject import ZDeviceComponent, ZDevice


log = logging.getLogger('zen.hub')


def translateError(callable):
    """
    Decorator function to wrap remote exceptions into something
    understandable by our daemon.

    @parameter callable: function to wrap
    @type callable: function
    @return: function's return or an exception
    @rtype: various
    """
    def inner(*args, **kw):
        """
        Interior decorator
        """
        try:
            return callable(*args, **kw)
        except Exception, ex:
            log.exception(ex)
            raise RemoteException(
                'Remote exception: %s: %s' % (ex.__class__, ex),
                traceback.format_exc())
    return inner


class NubService(pb.Referenceable):

    def __init__(self):
        self.log = log
        self.listeners = []
        self.listenerOptions = {}
        self.callTime = 0
        self.db = get_nub_db()

    def remoteMessageReceived(self, broker, message, args, kw):
        self.log.debug("Servicing %s in %s", message, self.name())
        now = time.time()
        try:
            return pb.Referenceable.remoteMessageReceived(
                self, broker, message, args, kw
            )
        finally:
            secs = time.time() - now
            self.log.debug("Time in %s: %.2f", message, secs)
            self.callTime += secs

    def name(self):
        return self.__class__.__name__

    def addListener(self, remote, options=None):
        remote.notifyOnDisconnect(self.removeListener)
        self.log.debug(
            "adding listener for %s", self.name()
        )
        self.listeners.append(remote)
        if options:
            self.listenerOptions[remote] = options

    def removeListener(self, listener):
        self.log.debug(
            "removing listener for %s", self.name()
        )
        try:
            self.listeners.remove(listener)
        except ValueError:
            self.warning("Unable to remove listener... ignoring")

        self.listenerOptions.pop(listener, None)

    def sendEvents(self, events):
        return

    def sendEvent(self, event, **kw):
        return

    @translateError
    def remote_propertyItems(self):
        return [
            ('eventlogCycleInterval', 60),
            ('processCycleInterval', 180),
            ('statusCycleInterval', 60),
            ('winCycleInterval', 60),
            ('wmibatchSize', 10),
            ('wmiqueryTimeout', 100),
            ('configCycleInterval', 360),
            ('zenProcessParallelJobs', 10),
            ('pingTimeOut', 1.5),
            ('pingTries', 2),
            ('pingChunk', 75),
            ('pingCycleInterval', 60),
            ('maxPingFailures', 1440),
            ('modelerCycleInterval', 720),
            ('discoveryNetworks', ()),
            ('ccBacked', 1),
            ('description', ''),
            ('poolId', 'default'),
            ('iprealm', 'default'),
            ('renderurl', '/zport/RenderServer'),
            ('defaultRRDCreateCommand', (
                'RRA:AVERAGE:0.5:1:600',
                'RRA:AVERAGE:0.5:6:600',
                'RRA:AVERAGE:0.5:24:600',
                'RRA:AVERAGE:0.5:288:600',
                'RRA:MAX:0.5:6:600',
                'RRA:MAX:0.5:24:600',
                'RRA:MAX:0.5:288:600'))
        ]


class EventService(NubService):

    def remote_sendEvent(self, evt):
        pass

    def remote_sendEvents(self, evts):
        pass

    def remote_getDevicePingIssues(self, *args, **kwargs):
        return None

    def remote_getDeviceIssues(self, *args, **kwargs):
        return None

    def remote_getDefaultPriority(self):
        return 3


class ModelerService(NubService):

    @translateError
    def remote_getThresholdClasses(self):
        return []

    @translateError
    def remote_getCollectorThresholds(self):
        return []

    @translateError
    def remote_getClassCollectorPlugins(self):
        result = []
        for dc_name, dc in self.db.device_classes.iteritems():
            localPlugins = dc.zProperties.get('zCollectorPlugins', False)
            if not localPlugins:
                continue
            result.append((dc_name, localPlugins))
        return result

    @translateError
    def remote_getDeviceConfig(self, names, checkStatus=False):
        result = []
        for id in names:
            device = self.db.devices.get(id)
            if not device:
                continue

            proxy = ModelDeviceProxy()
            proxy.id = id
            proxy.skipModelMsg = ''
            proxy.manageIp = device.manageIp
            proxy.plugins = []
            proxy._snmpLastCollection = 0

            plugin_ids = device.getProperty('zCollectorPlugins')
            for plugin_id in plugin_ids:
                plugin = self.db.modelerplugin.get(plugin_id)
                if not plugin:
                    continue

                proxy.plugins.append(plugin.pluginLoader)
                for id in plugin.deviceProperties:
                    # zproperties
                    if device.hasProperty(id):
                        setattr(proxy, id, device.getProperty(id))

                    # modeled properties (TODO)
                    elif hasattr(device, id):
                        setattr(proxy, id, getattr(device, id))

                    else:
                        self.log.error("device property %s not found on %s", id, id)

            result.append(proxy)

        return result

    @translateError
    def remote_getDeviceListByMonitor(self, monitor=None):
        return [x.id for x in self.db.devices]

    @translateError
    def remote_getDeviceListByOrganizer(self, organizer, monitor=None, options=None):
        dc = replace_prefix(organizer, "/Devices", "/")
        if dc not in self.db.device_classes:
            return []
        return [x.id for x in self.db.child_devices[dc]]

    @translateError
    def remote_applyDataMaps(self, device, maps, devclass=None, setLastCollection=False):
        mapper = self.db.get_mapper(device)

        adm = ApplyDataMapper(mapper, self.db.devices[device])
        changed = False
        for datamap in maps:
            if adm.applyDataMap(device, datamap):
                changed = True

        self.log.debug("ApplyDataMaps Completed: New DataMapper: %s", pformat(mapper.objects))
        self.log.debug("ApplyDataMaps Changed: %s", changed)

        self.db.snapshot_device(device)

        return changed

    remote_singleApplyDataMaps = remote_applyDataMaps

    @translateError
    def remote_setSnmpLastCollection(self, device):
        return

    @translateError
    def remote_setSnmpConnectionInfo(self, device, version, port, community):
        return


class CollectorConfigService(NubService):
    def __init__(self, deviceProxyAttributes=()):
        """
        Constructs a new CollectorConfig instance.

        Subclasses must call this __init__ method but cannot do so with
        the super() since parents of this class are not new-style classes.

        @param deviceProxyAttributes: a tuple of names for device attributes
               that should be copied to every device proxy created
        @type deviceProxyAttributes: tuple
        """
        NubService.__init__(self)

        self._deviceProxyAttributes = ('id', 'manageIp',) + deviceProxyAttributes
        self.db = get_nub_db()

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
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, ex:
            msg = 'Unhandled exception in zenhub service %s: %s' % (
                self.__class__, str(ex))
            self.log.exception(msg)

        return None

    @translateError
    def remote_getConfigProperties(self):
        return self.remote_propertyItems()

    @translateError
    def remote_getDeviceNames(self, options=None):
        # (note, this should be filtered by _filterDevices)
        return [x.id for x in self.db.devices]

    @translateError
    def remote_getDeviceConfigs(self, deviceNames=None, options=None):
        # (note, the device list should be filtered)

        if deviceNames is None or len(deviceNames) == 0:
            deviceNames = self.db.devices.keys()

        deviceConfigs = []
        for deviceName in deviceNames:
            device = self.db.devices.get(deviceName, None)
            if device is None:
                log.error("Device ID %s not found", deviceName)
                continue

            proxies = self._wrapFunction(self._createDeviceProxies, device)
            if proxies:
                deviceConfigs.extend(proxies)

        return deviceConfigs

    @translateError
    def remote_getEncryptionKey(self):
        # if we actually use it, this should be persisted, not changed
        # every time.
        from cryptography.fernet import Fernet
        import hashlib
        import base64

        key = Fernet.generate_key()

        # Hash the key with the daemon identifier to get unique key per collector daemon
        s = hashlib.sha256()
        s.update(key)
        s.update(self.__class__.__name__)
        return base64.urlsafe_b64encode(s.digest())

    @translateError
    def remote_getThresholdClasses(self):
        return []

    @translateError
    def remote_getCollectorThresholds(self):
        return []

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
            if hasattr(device, attrName):
                setattr(proxy, attrName, getattr(device, attrName, None))
            elif device.hasProperty(attrName):
                setattr(proxy, attrName, device.getProperty(attrName))

        return proxy

    def component_getRRDTemplates(self, device, component_datum):
        clsname = component_datum["type"]
        if clsname not in self.db.classmodel:
            log.error("Unable to locate monitoring templates for components of unrecognized class %s", clsname)
            return []

        rrdTemplateName = self.db.classmodel[clsname].default_rrd_template_name
        seen = set()
        templates = []

        for dc in all_parent_dcs(device.device_class):
            for template_name, template in self.db.device_classes[dc].rrdTemplates.iteritems():
                if template_name in seen:
                    # lower level templates with the same name take precendence
                    continue
                seen.add(template_name)

                # this really should use getRRDTemplateName per instance,
                # but that is not available to us without zodb.   So we
                # use a single value that was determined by update_zenpacks.py
                if template_name == rrdTemplateName:
                    templates.append(template)

        return templates


class CommandPerformanceConfig(CollectorConfigService):
    dsType = 'COMMAND'

    def __init__(self):
        deviceProxyAttributes = (
            'zCommandPort',
            'zCommandUsername',
            'zCommandPassword',
            'zCommandLoginTimeout',
            'zCommandCommandTimeout',
            'zKeyPath',
            'zSshConcurrentSessions',
        )
        CollectorConfigService.__init__(self, deviceProxyAttributes)

    def _createDeviceProxy(self, device, proxy=None):
        proxy = CollectorConfigService._createDeviceProxy(
            self, device, proxy=proxy)

        # Framework expects a default value but zencommand uses cycles per datasource instead
        proxy.configCycleInterval = 0

        proxy.name = device.id
        proxy.device = device.id
        proxy.lastmodeltime = "n/a"
        proxy.lastChangeTime = float(0)

        commands = set()

        # First for the device....
        proxy.thresholds = []

        device_datum = self.db.get_mapper(device.id).get(device.id)
        self._safeGetComponentConfig(device.id, device_datum, device, commands)

        # And now for its components
        for compId, comp in device.getMonitoredComponents(collector='zencommand'):
            self._safeGetComponentConfig(compId, comp, device, commands)

        if commands:
            proxy.datasources = list(commands)
            return proxy
        return None

    def _safeGetComponentConfig(self, compId, comp, device, commands):
        """
        Catchall wrapper for things not caught at previous levels
        """

        try:
            self._getComponentConfig(compId, comp, device, commands)
        except Exception:
            msg = "Unable to process %s datasource(s) for device %s -- skipping" % (
                self.dsType, device.id)
            log.exception(msg)

    def _getComponentConfig(self, compId, comp, device, cmds):
        # comp is a mapper datum.  device is a Device model object.model

        for templ in self.component_getRRDTemplates(device, comp):
            for ds in templ.getRRDDataSources(self.dsType):

                # Ignore SSH datasources if no username set
                useSsh = getattr(ds, 'usessh', False)
                if useSsh and not device.getProperty('zCommandUsername'):
                    log.warning("Username not set on device %s" % device)
                    continue

                parserName = getattr(ds, "parser", "Auto")
                plugin = self.db.parserplugin.get(parserName)
                if plugin is None:
                    log.error("Could not find %s parser plugin", parserName)
                    continue
                ploader = plugin.pluginLoader

                cmd = Cmd()
                cmd.useSsh = useSsh
                cmd.name = "%s/%s" % (templ.id, ds.id)
                cmd.cycleTime = self._getDsCycleTime(device, templ, ds)
                cmd.component = comp.get('title') or compId

                # TODO: events are not supported currently.
                # cmd.eventClass = ds.eventClass
                # cmd.eventKey = ds.eventKey or ds.id
                # cmd.severity = ds.severity
                cmd.parser = ploader
                cmd.ds = ds.id
                cmd.points = self._getDsDatapoints(device, compId, comp, ds, ploader)

                # TODO: OSProcess component monitoring isn't supported currently.
                # if isinstance(comp, OSProcess):
                #     # save off the regex's specified in the UI to later run
                #     # against the processes running on the device
                #     cmd.includeRegex = comp.includeRegex
                #     cmd.excludeRegex = comp.excludeRegex
                #     cmd.replaceRegex = comp.replaceRegex
                #     cmd.replacement  = comp.replacement
                #     cmd.primaryUrlPath = comp.processClassPrimaryUrlPath()
                #     cmd.generatedId = comp.id
                #     cmd.displayName = comp.displayName
                #     cmd.sequence = comp.osProcessClass().sequence

                # If the datasource supports an environment dictionary, use it
                cmd.env = getattr(ds, 'env', None)

                try:
                    cmd.command = ds.getCommand(comp, device=device)
                except Exception as ex:  # TALES error
                    details = dict(
                        template=templ.id,
                        datasource=ds.id,
                        affected_device=device.id,
                        affected_component=compId,
                        tb_exception=str(ex),
                        resolution='Could not create a command to send to zencommand' +
                                   ' because TALES evaluation failed.  The most likely' +
                                   ' cause is unescaped special characters in the command.' +
                                   ' eg $ or %')
                    # This error might occur many, many times
                    log.warning("Event: %s", str(details))
                    continue

                cmds.add(cmd)

    def _getDsDatapoints(self, device, compId, comp, ds, ploader):
        """
        Given a component a data source, gather its data points
        """

        if compId is None:
            deviceDatum = self.db.get(device.id)
            mapper = self.db.get_mapper(device.id)
            deviceOrComponent = ZDevice(self.db, device, device.id)
        else:
            mapper = self.db.get_mapper(device.id)
            deviceOrComponent = ZDeviceComponent(self.db, device, compId)

        parser = ploader.create()
        points = []
        component_name = comp.get('title') or compId
        for dp_id, dp in ds.datapoints.iteritems():
            dpc = DataPointConfig()
            dpc.id = dp_id
            dpc.component = component_name
            dpc.dpName = dp_id
            dpc.data = self._dataForParser(parser, compId, comp, dp_id, dp)

            dpc.rrdPath = '/'.join((deviceOrComponent.rrdPath(), dp_id))
            dpc.metadata = deviceOrComponent.getMetricMetadata()
            # by default, metrics have the format <device id>/<metric name>.
            # Setting this to the datasource id, gives us ds/dp, which
            # the cloud metric publisher turns into ds_dp.  So it's important
            # for each collector daemon / config service to make sure that
            # its metrics do get formatted that way.
            dpc.metadata['metricPrefix'] = ds.id

            points.append(dpc)

        return points

    def _dataForParser(self, parser, compId, comp, dpId, dp):
        # LIMIT: Normally, this is a method on the parser, and its behavior
        # can be overridden to supply arbitrary model information to the parser

        if hasattr(parser, 'componentScanValue'):
            if parser.componentScanValue == 'id':
                return {'componentScanValue': compId}
            else:
                return {'componentScanValue': comp['properties'].get(parser.componentScanValue)}

        return {}

    def _getDsCycleTime(self, device, templ, ds):
        cycleTime = 300
        try:
            cycleTime = int(ds.getCycleTime(device))
        except ValueError:
            message = "Unable to convert the cycle time '%s' to an " \
                      "integer for %s/%s on %s" \
                      " -- setting to 300 seconds" % (
                          ds.cycletime, templ.id, ds.id, device.id)
            log.error(message)
        return cycleTime


class PythonConfig(CollectorConfigService):

    def __init__(self, modelerService):
        CollectorConfigService.__init__(self)
        self.modelerService = modelerService
        self.python_sourcetypes = set()
        for sourcetype, dsinfo in self.db.datasource.iteritems():
            dsClass = importClass(dsinfo.modulename, dsinfo.classname)
            if issubclass(dsClass, PythonDataSource):
                self.python_sourcetypes.add(sourcetype)

    # @profile
    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.datasources = list(self.device_datasources(device))

        for compId, _ in device.getMonitoredComponents():
            proxy.datasources += list(
                self.component_datasources(device, compId))

        if len(proxy.datasources) > 0:
            return proxy

        return None

    def device_datasources(self, device):
        return self._datasources(device, device.id, None)

    def component_datasources(self, device, compId):
        return self._datasources(device, device.id, compId)

    def _datasources(self, deviceModel, deviceId, componentId):
        known_point_properties = (
            'isrow', 'rrdmax', 'description', 'rrdmin', 'rrdtype', 'createCmd', 'tags')

        mapper = self.db.get_mapper(deviceId)
        if componentId is None:
            datum = mapper.get(deviceId)
            datumId = deviceId
            deviceOrComponent = ZDevice(self.db, deviceModel, datumId)
        else:
            datum = mapper.get(componentId)
            datumId = componentId
            deviceOrComponent = ZDeviceComponent(self.db, deviceModel, datumId)
            device = deviceOrComponent.device()

        for template in self.component_getRRDTemplates(deviceModel, datum):
            # Get all enabled datasources that are PythonDataSource or
            # subclasses thereof.
            datasources = [ds for ds in template.getRRDDataSources()
                           if ds.sourcetype in self.python_sourcetypes]

            device = deviceOrComponent.device()

            for ds in datasources:
                datapoints = []

                try:
                    ds_plugin_class = self._getPluginClass(ds)
                except Exception as e:
                    log.error(
                        "Failed to load plugin %r for %s/%s: %s",
                        ds.plugin_classname,
                        template.id,
                        ds.id,
                        e)

                    continue

                for dp_id, dp in ds.datapoints.iteritems():
                    dp_config = DataPointConfig()

                    dp_config.id = dp_id
                    dp_config.dpName = dp_id

                    dp_config.rrdPath = '/'.join((deviceOrComponent.rrdPath(), dp_id))
                    dp_config.metadata = deviceOrComponent.getMetricMetadata()

                    # by default, metrics have the format <device id>/<metric name>.
                    # Setting this to the datasource id, gives us ds/dp, which
                    # the cloud metric publisher turns into ds_dp.  So it's important
                    # for each collector daemon / config service to make sure that
                    # its metrics do get formatted that way.
                    dp_config.metadata['metricPrefix'] = ds.id

                    # Attach unknown properties to the dp_config
                    for key in dp.__dict__.keys():
                        if key in known_point_properties:
                            continue
                        try:
                            value = getattr(dp, key)
                            if isinstance(value, basestring) and '$' in value:
                                extra = {
                                    'device': device,
                                    'dev': device,
                                    'devname': device.id,
                                    'datasource': ds,
                                    'ds': ds,
                                    'datapoint': dp,
                                    'dp': dp,
                                }

                                value = talesEvalStr(
                                    value,
                                    deviceOrComponent,
                                    extra=extra)

                            setattr(dp_config, key, value)
                        except Exception:
                            pass

                    datapoints.append(dp_config)

                ds_config = PythonDataSourceConfig()
                ds_config.device = deviceId
                ds_config.manageIp = deviceModel.manageIp
                ds_config.component = componentId
                ds_config.plugin_classname = ds.plugin_classname
                ds_config.template = template.id
                ds_config.datasource = ds.id
                ds_config.config_key = self._getConfigKey(ds, deviceOrComponent)
                ds_config.params = self._getParams(ds, deviceOrComponent)
                ds_config.cycletime = ds.getCycleTime(deviceOrComponent)
                # ds_config.eventClass = ds.eventClass
                # ds_config.eventKey = ds.eventKey
                ds_config.eventKey = ""
                # ds_config.severity = ds.severity
                ds_config.points = datapoints

                # Populate attributes requested by plugin.
                for attr in ds_plugin_class.proxy_attributes:
                    value = getattr(deviceOrComponent, attr, None)
                    if callable(value):
                        value = value()

                    setattr(ds_config, attr, value)

                yield ds_config

    def _getPluginClass(self, ds):
        """Return plugin class referred to by self.plugin_classname."""

        class_parts = ds.plugin_classname.split('.')
        module_name = '.'.join(class_parts[:-1])
        class_name = class_parts[-1]
        if module_name not in sys.modules:
            importlib.import_module(module_name)

        return getattr(sys.modules[module_name], class_name)

    def _getConfigKey(self, ds, context):
        """Returns a tuple to be used to split configs at the collector."""
        if not ds.plugin_classname:
            return [context.id]

        return self._getPluginClass(ds).config_key(ds, context)

    def _getParams(self, ds, context):
        """Returns extra parameters needed for collecting this datasource."""
        if not ds.plugin_classname:
            return {}

        params = self._getPluginClass(ds).params(ds, context)

        return params

    def remote_applyDataMaps(self, device, datamaps):
        return self.modelerService.remote_applyDataMaps(device, datamaps)


