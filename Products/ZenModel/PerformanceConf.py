##############################################################################
#
# Copyright (C) Zenoss, Inc. 2006-2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""PerformanceConf
The configuration object for Performance servers
"""

import logging
import re

from ipaddr import IPAddress

log = logging.getLogger('zen.PerformanceConf')

from zope import component
from zope.component.factory import Factory
from zope.interface import implementer

from Products.ZenUtils.IpUtil import ipwrap

from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from Monitor import Monitor
from Products.Jobber.jobs import SubprocessJob
from Products.ZenRelations.RelSchema import ToMany, ToOne
from Products.ZenUtils.deprecated import deprecated
from Products.ZenUtils.path import binPath
from Products.ZenUtils.Utils import unused, isXmlRpc, executeCommand
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenModel.ZDeviceLoader import CreateDeviceJob
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit

from .StatusColor import StatusColor
from .interfaces import IMonitor

SUMMARY_COLLECTOR_REQUEST_TIMEOUT = float(
    getGlobalConfiguration().get('collectorRequestTimeout', 5))


def manage_addPerformanceConf(context, id, title=None, REQUEST=None,):
    """
    Make a device class

    @param context: Where you are in the Zope acquisition path
    @type context: Zope context object
    @param id: unique identifier
    @type id: string
    @param title: user readable label (unused)
    @type title: string
    @param REQUEST: Zope REQUEST object
    @type REQUEST: Zope REQUEST object
    @return:
    @rtype:
    """
    unused(title)
    # Use the factory to create the monitor.
    component.createObject(PerformanceConf.meta_type, context, id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')

addPerformanceConf = DTMLFile('dtml/addPerformanceConf', globals())


class PerformanceConfFactory(Factory):
    """
    IFactory implementation for PerformanceConf objects.

    The factory create the PerformanceConf instance and attaches it to
    the dmd.Monitor.Performance folder.
    """

    def __init__(self):
        super(PerformanceConfFactory, self).__init__(
            PerformanceConf, PerformanceConf.meta_type, "Performance Monitor"
        )

    def __call__(self, folder, monitorId, sourceId=None):
        """
        Creates a new PerformanceConf object, saves it to ZODB, and returns
        the new object.

        :param Folder folder: The new monitor is attached here.
        :param string monitorId: The ID/name of the monitor
        :param string sourceId: The ID/name of the monitor to copy
            properties from.
        :rtype PerformanceConf: The new monitor.
        """
        sourceId = sourceId if sourceId is not None else "localhost"
        monitor = folder.get(monitorId)
        if monitor:
            raise ValueError(
                "Performance Monitor with ID '%s' already exitsts."
                % (monitorId,)
            )
        source = folder.get(sourceId)
        if source is None:
            source = folder.get("localhost")
            if source:
                source = source.primaryAq()
        monitor = super(PerformanceConfFactory, self).__call__(monitorId)
        if source:
            sourceprops = dict(source.propertyItems())
            monitor.manage_changeProperties(**sourceprops)
        folder[monitorId] = monitor
        monitor = folder.get(monitorId)
        monitor.buildRelations()
        return monitor


@implementer(IMonitor)
class PerformanceConf(Monitor, StatusColor):
    """
    Configuration for Performance servers
    """
    portal_type = meta_type = 'PerformanceConf'
    monitorRootName = 'Performance'

    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    eventlogCycleInterval = 60
    perfsnmpCycleInterval = 300
    processCycleInterval = 180
    statusCycleInterval = 60
    winCycleInterval = 60
    wmibatchSize = 10
    wmiqueryTimeout = 100
    configCycleInterval = 6 * 60

    zenProcessParallelJobs = 10

    pingTimeOut = 1.5
    pingTries = 2
    pingChunk = 75
    pingCycleInterval = 60
    maxPingFailures = 1440

    modelerCycleInterval = 720
    discoveryNetworks = ()

    _properties = (
        {'id': 'eventlogCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'processCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'statusCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'winCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'wmibatchSize', 'type': 'int', 'mode': 'w',
         'description': "Number of data objects to retrieve in a single WMI query"},
        {'id': 'wmiqueryTimeout', 'type': 'int', 'mode': 'w',
         'description': "Number of milliseconds to wait for WMI query to respond"},
        {'id': 'configCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'zenProcessParallelJobs', 'type': 'int', 'mode': 'w'},
        {'id': 'pingTimeOut', 'type': 'float', 'mode': 'w'},
        {'id': 'pingTries', 'type': 'int', 'mode': 'w'},
        {'id': 'pingChunk', 'type': 'int', 'mode': 'w'},
        {'id': 'pingCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'maxPingFailures', 'type': 'int', 'mode': 'w'},
        {'id': 'modelerCycleInterval', 'type': 'int', 'mode': 'w'},
        {'id': 'discoveryNetworks', 'type': 'lines', 'mode': 'w'},
    )

    _relations = Monitor._relations + (
        ("devices", ToMany(ToOne, "Products.ZenModel.Device", "perfServer")),
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = ({
        'immediate_view': 'viewPerformanceConfOverview',
        'actions': ({
            'id':          'overview',
            'name':        'Overview',
            'action':      'viewPerformanceConfOverview',
            'permissions': (permissions.view,)
        }, {
            'id':          'edit',
            'name':        'Edit',
            'action':      'editPerformanceConf',
            'permissions': ("Manage DMD",)
        }, {
            'id':          'performance',
            'name':        'Performance',
            'action':      'viewDaemonPerformance',
            'permissions': (permissions.view,)
        },)
    },)

    def findDevice(self, deviceName):
        """
        Return the object given the name

        @param deviceName: Name of a device
        @type deviceName: string
        @return: device corresponding to the name, or None
        @rtype: device object
        """
        brains = self.dmd.Devices._findDevice(deviceName)
        if brains:
            return brains[0].getObject()

    def findDeviceByIdExact(self, deviceName):
        """
        Look up device in catalog and return it.  devicename
        must match device id exactly

        @param deviceName: Name of a device
        @type deviceName: string
        @return: device corresponding to the name, or None
        @rtype: device object
        """
        dev = self.dmd.Devices.findDeviceByIdExact(deviceName)
        if dev:
            return dev

    def getNetworkRoot(self, version=None):
        """
        Get the root of the Network object in the DMD

        @return: base DMD Network object
        @rtype: Network object
        """
        return self.dmd.Networks.getNetworkRoot(version)

    security.declareProtected('View', 'performanceDeviceList')
    def performanceDeviceList(self, force=True):
        """
        Return a list of URLs that point to our managed devices

        @param force: unused
        @type force: boolean
        @return: list of device objects
        @rtype: list
        """
        unused(force)
        devlist = []
        for dev in self.devices():
            dev = dev.primaryAq()
            if not dev.pastSnmpMaxFailures() and dev.monitorDevice():
                devlist.append(dev.getPrimaryUrlPath())
        return devlist

    security.declareProtected('View', 'performanceDataSources')
    def performanceDataSources(self):
        """
        Return a string that has all the definitions for the performance DS's.

        @return: list of Data Sources
        @rtype: string
        """
        dses = []
        oidtmpl = 'OID %s %s'
        dstmpl = """datasource %s
        rrd-ds-type = %s
        ds-source = snmp://%%snmp%%/%s%s
        """
        rrdconfig = self.getDmdRoot('Devices').rrdconfig
        for ds in rrdconfig.objectValues(spec='RRDDataSource'):
            if ds.isrow:
                inst = '.%inst%'
            else:
                inst = ''
            dses.append(oidtmpl % (ds.getName(), ds.oid))
            dses.append(dstmpl % (ds.getName(), ds.rrdtype,
                        ds.getName(), inst))
        return '\n'.join(dses)

    def setPerformanceMonitor(
            self, performanceMonitor=None, deviceNames=None, REQUEST=None):
        """
        Provide a method to set performance monitor from any organizer

        @param performanceMonitor: DMD object that collects from a device
        @type performanceMonitor: DMD object
        @param deviceNames: list of device names
        @type deviceNames: list
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        """
        if not performanceMonitor:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', 'No monitor was selected.',
                    priority=messaging.WARNING
                )
            return self.callZenScreen(REQUEST)
        if deviceNames is None:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', 'No devices were selected.',
                    priority=messaging.WARNING
                )
            return self.callZenScreen(REQUEST)
        for devName in deviceNames:
            dev = self.devices._getOb(devName)
            dev = dev.primaryAq()
            dev.setPerformanceMonitor(performanceMonitor)
            if REQUEST:
                audit(
                    'UI.Device.ChangeCollector',
                    dev, collector=performanceMonitor
                )
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Monitor Set',
                'Performance monitor was set to %s.' % performanceMonitor
            )
            if "oneKeyValueSoInstanceIsntEmptyAndEvalToFalse" in REQUEST:
                return REQUEST['message']
            else:
                return self.callZenScreen(REQUEST)

    security.declareProtected('View', 'getPingDevices')
    def getPingDevices(self):
        """
        Return devices associated with this monitor configuration.

        @return: list of devices for this monitor
        @rtype: list
        """
        devices = []
        for dev in self.devices.objectValuesAll():
            dev = dev.primaryAq()
            if dev.monitorDevice() and not dev.zPingMonitorIgnore:
                devices.append(dev)
        return devices

    def addCreateDeviceJob(
            self, deviceName, devicePath, title=None,
            discoverProto="none", manageIp="", performanceMonitor=None,
            rackSlot=0, productionState=1000, comments="",
            hwManufacturer="", hwProductName="", osManufacturer="",
            osProductName="", priority=3, locationPath="", systemPaths=[],
            groupPaths=[], tag="", serialNumber="",
            zProperties={}, cProperties={},):
        """
        Creating a device has two steps: creating a 'stub' device in the
        database, then (if requested) running zendisc to model the device.
        The modeling step can be skipped if the discoverProto argument
        is set to the string "none".

        @returns A list of JobRecord objects.
        """
        # Determine the name of the monitor to use.
        monitor = performanceMonitor or self.id

        # Check to see if we got passed in an IPv6 address
        try:
            IPAddress(deviceName)
            if not title:
                title = deviceName
            deviceName = ipwrap(deviceName)
        except ValueError:
            pass

        # Creating a device is, at most, a two-step process.  First a
        # device 'stub' is created in the database then, if the
        # discoverProto argument is not 'none', then zendisc is run to
        # discover and model the device.  The process is implemented using
        # two jobs.

        subjobs = [
            CreateDeviceJob.makeSubJob(
                args=(deviceName,),
                kwargs=dict(
                    devicePath=devicePath,
                    title=title,
                    discoverProto=discoverProto,
                    manageIp=manageIp,
                    performanceMonitor=monitor,
                    rackSlot=rackSlot,
                    productionState=productionState,
                    comments=comments,
                    hwManufacturer=hwManufacturer,
                    hwProductName=hwProductName,
                    osManufacturer=osManufacturer,
                    osProductName=osProductName,
                    priority=priority,
                    tag=tag,
                    serialNumber=serialNumber,
                    locationPath=locationPath,
                    systemPaths=systemPaths,
                    groupPaths=groupPaths,
                    zProperties=zProperties,
                    cProperties=cProperties,
                )
            )
        ]
        if discoverProto != 'none':
            zendiscCmd = self._getZenDiscCommand(
                deviceName, devicePath, monitor, productionState
            )
            subjobs.append(
                SubprocessJob.makeSubJob(
                    args=(zendiscCmd,),
                    description="Discover and model device %s as %s" % (
                        deviceName, devicePath
                    )
                )
            )
        # Set the 'immutable' flag to indicate that the result of the prior
        # job is not passed as arguments into the next job (basically, args
        # to the jobs are immutable).
        return self.dmd.JobManager.addJobChain(*subjobs, immutable=True)

    @deprecated
    def addDeviceCreationJob(
            self, deviceName, devicePath, title=None,
            discoverProto="none", manageIp="",
            performanceMonitor=None,
            rackSlot=0, productionState=1000, comments="",
            hwManufacturer="", hwProductName="",
            osManufacturer="", osProductName="", priority=3,
            locationPath="", systemPaths=[], groupPaths=[],
            tag="", serialNumber="", zProperties={}):
        """
        For backward compatibility.  Please use the addCreateDeviceJob
        method instead of the addDeviceCreationJob method.
        """
        result = self.addCreateDeviceJob(
            deviceName, devicePath, title=title,
            discoverProto=discoverProto, manageIp=manageIp,
            performanceMonitor=performanceMonitor, rackSlot=rackSlot,
            productionState=productionState, comments=comments,
            hwManufacturer=hwManufacturer, hwProductName=hwProductName,
            osManufacturer=osManufacturer, osProductName=osProductName,
            priority=priority, locationPath=locationPath,
            systemPaths=systemPaths, groupPaths=groupPaths, tag=tag,
            serialNumber=serialNumber, zProperties=zProperties
        )
        return result[-1]

    def _executeZenDiscCommand(
            self, deviceName, devicePath="/Discovered",
            performanceMonitor="localhost", productionState=1000,
            background=False, REQUEST=None):
        """
        Execute zendisc on the new device and return result

        @param deviceName: Name of a device
        @type deviceName: string
        @param devicePath: DMD path to create the new device in
        @type devicePath: string
        @param performanceMonitor: DMD object that collects from a device
        @type performanceMonitor: DMD object
        @param background: should command be scheduled job?
        @type background: boolean
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        @return:
        @rtype:
        """
        args = [deviceName, devicePath, performanceMonitor, productionState]
        if background:
            zendiscCmd = self._getZenDiscCommand(*args)
            result = self.dmd.JobManager.addJob(
                SubprocessJob, args=(zendiscCmd,),
                description="Discover and model device %s as %s" % (
                    args[0], args[1]
                )
            )
        else:
            args.append(REQUEST)
            zendiscCmd = self._getZenDiscCommand(*args)
            result = self._executeCommand(zendiscCmd, REQUEST)
        return result

    def _getZenDiscCommand(
            self, deviceName, devicePath,
            performanceMonitor, productionState, REQUEST=None, max_seconds=None):
        zm = binPath('zendisc')
        zendiscCmd = [zm]
        deviceName = self._escapeParentheses(deviceName)
        zendiscOptions = [
            'run', '--now', '-d', deviceName,
            '--monitor', performanceMonitor,
            '--deviceclass', devicePath,
            '--prod_state', str(productionState)
        ]
        if REQUEST:
            zendiscOptions.append("--weblog")
        zendiscCmd.extend(zendiscOptions)
        log.info('local zendiscCmd is "%s"', ' '.join(zendiscCmd))
        return zendiscCmd

    def getCollectorCommand(self, command):
        return [binPath(command)]

    def executeCollectorCommand(self, command, args, REQUEST=None):
        """
        Executes the collector based daemon command.

        @param command: the collector daemon to run, should not include path
        @type command: string
        @param args: list of arguments for the command
        @type args: list of strings
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        @return: result of the command
        @rtype: string
        """
        cmd = binPath(command)
        daemonCmd = [cmd]
        daemonCmd.extend(args)
        result = self._executeCommand(daemonCmd, REQUEST)
        return result

    def collectDevice(
            self, device=None, setlog=True, REQUEST=None,
            generateEvents=False, background=False, write=None,
            collectPlugins='', debug=False):
        """
        Collect the configuration of this device AKA Model Device

        @permission: ZEN_MANAGE_DEVICE
        @param device: Name of a device or entry in DMD
        @type device: string
        @param setlog: If true, set up the output log of this process
        @type setlog: boolean
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        @param generateEvents: unused
        @type generateEvents: string
        @param collectPlugins: (optional) Modeler plugins to use.
                               Takes a regular expression (default: '')
        @type  collectPlugins: string
        """
        xmlrpc = isXmlRpc(REQUEST)
        result = self._executeZenModelerCommand(device.id, self.id, background,
                                                REQUEST, write,
                                                collectPlugins=collectPlugins, debug=debug)
        if result and xmlrpc:
            return result
        log.info('configuration collected')

        if xmlrpc:
            return 0

    def _executeZenModelerCommand(
            self, deviceName, performanceMonitor="localhost", background=False,
            REQUEST=None, write=None, collectPlugins='', debug=False):
        """
        Execute zenmodeler and return result
        @param deviceName: The name of the device
        @type deviceName: string
        @param performanceMonitor: Name of the collector
        @type performanceMonitor: string
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        @param collectPlugins: (optional) Modeler plugins to use.
                               Takes a regular expression (default: '')
        @type  collectPlugins: string
        @return: results of command
        @rtype: string
        """
        args = [deviceName, performanceMonitor, collectPlugins]
        if background:
            zenmodelerCmd = self._getZenModelerCommand(*args)
            log.info('queued job: %s', " ".join(zenmodelerCmd))
            result = self.dmd.JobManager.addJob(
                SubprocessJob,
                description="Run zenmodeler %s" % ' '.join(zenmodelerCmd),
                args=(zenmodelerCmd,)
            )
        else:
            args.append(REQUEST)
            zenmodelerCmd = self._getZenModelerCommand(*args)
            if debug:
                zenmodelerCmd.append('-v10')
            result = self._executeCommand(zenmodelerCmd, REQUEST, write)
        return result

    def _getZenModelerCommand(
            self, deviceName, performanceMonitor,  collectPlugins='', REQUEST=None):
        zm = binPath('zenmodeler')
        cmd = [zm]
        deviceName = self._escapeParentheses(deviceName)
        options = [
            'run', '--now', '-d', deviceName, '--monitor', performanceMonitor,
            '--collect={}'.format(collectPlugins)
        ]
        cmd.extend(options)
        log.info('local zenmodelerCmd is "%s"', ' '.join(cmd))
        return cmd

    def _executeCommand(self, remoteCommand, REQUEST=None, write=None):
        result = executeCommand(remoteCommand, REQUEST, write)
        return result

    def runDeviceMonitor(
            self, device=None, REQUEST=None, write=None,
            collection_daemons=None, debug=False):
        """
        Run collection daemons against specific device
        """
        xmlrpc = isXmlRpc(REQUEST)
        result = self._executeMonitoringCommands(device.id, self.id, write,
                                                 REQUEST, collection_daemons,
                                                 debug)
        if result and xmlrpc:
            return result
        log.info('configuration collected')

        if xmlrpc:
            return 0

    def runDeviceMonitorPerDatasource(
            self, device=None, REQUEST=None, write=None,
            collection_daemon=None, parameter='', value=''):
        """
        Run collection daemon against specific datasource
        """
        xmlrpc = isXmlRpc(REQUEST)
        monitoringCmd = self._getMonitoringCommand(device.id, self.id, write,
                                                   collection_daemon,
                                                   parameter, value)
        result = self._executeCommand(monitoringCmd, REQUEST, write)
        if result and xmlrpc:
            return result
        log.info('configuration collected')

        if xmlrpc:
            return 0

    def _executeMonitoringCommands(
            self, deviceName, performanceMonitor="localhost",
            write=None, REQUEST=None, collection_daemons=None, debug=False):
        """
        Execure monitoring daemon command
        """
        for daemon in collection_daemons:
            monitoringCmd = self._getMonitoringCommand(deviceName,
                                                       performanceMonitor,
                                                       write, daemon)
            if debug:
                monitoringCmd.append('-v10')
            result = self._executeCommand(monitoringCmd, REQUEST, write)
        return result

    def _getMonitoringCommand(
            self, deviceName, performanceMonitor, write=None, daemon=None,
            parameter='', value=''):
        """
        Get monitoring command and create command to run
        """
        cmd = [binPath(daemon)]
        deviceName = self._escapeParentheses(deviceName)
        options = [
            'run', '-d', deviceName, '--monitor', performanceMonitor,
            parameter, value
        ]
        cmd.extend(options)
        log_message = 'local monitoring cmd is "%s"\n' % ' '.join(cmd)
        if write:
            write(log_message)
        log.info(log_message)
        return cmd


    def _escapeParentheses(self, string):
        """
        Escape unascaped parentheses.
        """
        compiled = re.compile(r'(?<!\\)(?P<char>[()])')
        return compiled.sub(r'\\\g<char>', string)


class RenderURLUtilContext(object):
    """
    Deprecated
    """
    pass


class RenderURLUtil(object):
    """
    Deprecated
    This is no longer used but the stub class so zenpacks will
    work on an upgrade.
    """
    pass

InitializeClass(PerformanceConf)
