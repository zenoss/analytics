##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """zenbatchload

zenbatchload loads a list of devices read from a file.
"""

import sys
import re
from traceback import format_exc
import socket

from ZODB.POSException import ConflictError
from ZODB.transact import transact
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.event import notify

from zExceptions import BadRequest

from ZPublisher.Converters import type_converters
from Products.ZenModel.interfaces import IDeviceLoader
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenModel.Device import Device
from Products.ZenRelations.ZenPropertyManager import iszprop
from Products.ZenModel.ZenModelBase import iscustprop
from Products.ZenEvents.ZenEventClasses import Change_Add
from Products.Zuul.catalog.events import IndexingEvent
from Products.ZenUtils.Utils import unused
# import DateTime to set properties of type DateTime in the zenbatchload
from DateTime import DateTime

unused(DateTime)

from Products.ZenUtils.IpUtil import isip

from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_INFO, SEVERITY_ERROR


def transactional(f):
    def wrapper(obj, *args, **kwargs):
        if obj.options.nocommit:
            return f.__call__(obj, *args, **kwargs)
        else:
            return transact(f).__call__(obj, *args, **kwargs)

    return wrapper


class BatchDeviceLoader(ZCmdBase):
    """
    Base class wrapping around dmd.DeviceLoader
    """

    # ZEN-9930 - Pulled these options from sample config
    # setHWProduct=('myproductName','manufacturer')
    # setOSProduct=('OS Name','manufacturer')

    sample_configs = """#
# Example zenbatchloader file (Groups, Systems Locations, Devices, etc.)
#
# This file is formatted with one entry per line, like this:
#
#  /Devices/device_class_name Python-expression
#  hostname Python-expression
#
# For organizers (for example, the /Devices path), the Python-expression
# is used to define defaults to be used for devices listed
# after the organizer. The defaults that can be specified are:
#
#   * loader arguments (use the --show_options flag to show these)
#
#   * zProperties (from a device, use the 'Configuration Properties'
#      menu item to see the available ones.)
#
#      NOTE: new zProperties *cannot* be created through this file
#
#   * cProperties (from a device, use the 'Custom Properties'
#      menu item to see the available ones.)
#
#      NOTE: new cProperties *cannot* be created through this file
#
#  The Python-expression is used to create a dictionary of settings.
#  device_settings = eval( 'dict(' + python-expression + ')' )
#

# Defining groups
/Groups/Admin
/Groups/Support

#Defining systems
/Systems/Production
/Systems/Staging

# Defining locations
/Locations/Canada address="Canada"
/Locations/Canada/Alberta address="Alberta, Canada"
/Locations/Canada/Alberta/Calgary address="Calgary, Alberta, Canada"

# If no organizer is specified at the beginning of the file,
# defaults to the /Devices/Discovered device class.
device0 comments="A simple device"
# All settings must be seperated by a comma.
device1 comments="A simple device", zSnmpCommunity='blue', zSnmpVer='v1'

# Notes for this file:
#  * Oraganizer names *must* start with '/'
#
/Devices/Server/Linux zSnmpPort=1543
# Python strings can use either ' or " -- there's no difference.
# As a special case, it is also possible to specify the IP address
linux_device1 setManageIp='10.10.10.77', zSnmpCommunity='blue', zSnmpVer="v2c"
# A '\' at the end of the line allows you to place more
# expressions on a new line. Don't forget the comma...
linux_device2 zLinks="<a href='http://example.org'>Support site</a>",  \
zTelnetEnable=True, \
zTelnetPromptTimeout=15.3

# A new organizer drops all previous settings, and allows
# for new ones to be used.
/Devices/Server/Windows zWinUser="administrator", zWinPassword='fred'
# Bind templates
windows_device1 zDeviceTemplates=[ 'Device', 'myTemplate' ], rackSlot=1
# Override the default from the organizer setting.
windows_device2 zWinUser="administrator", zWinPassword='thomas', setProdState=500, \
  rackSlot=2, settingsDevice setManageIp='10.10.10.77', setLocation="123 Elm Street", \
  setSystems=['/mySystems'], setPerformanceMonitor='remoteCollector1', \
  setHWSerialNumber="abc123456789", setGroups=['/myGroup'], \
# Apply custom schema properties (c-properties) to a device
windows_device7 cDateTest='2010/02/28'

# If the device or device class contains a space, then it must be quoted (either ' or ")
"/Server/Windows/WMI/Active Directory/2008"
windows_device_3 setTitle="Windows AD Server 1", setHWTag="service-tag-ABCDEF", setPriority=2

# Now, what if we have a device that isn't really a device, and requires
# a special loader?
# The 'loader' setting requires a registered utility, and 'loader_arg_keys' is
# a list from which any other settings will be passed into the loader callable.
#
# Here is a commmented-out example of how a VMware endpoint might be added:
#
#/Devices/VMware loader='vmware', loader_arg_keys=['host', 'username', 'password', 'useSsl', 'id']
#esxwin2 id='esxwin2', host='esxwin2.zenoss.loc', username='testuser', password='password', useSsl=True

# The following are wrapper methods that specifically set properties on a device:
#   setManageIp
#   setPerformanceMonitor
#   setTitle
#   setHWTag
#   setHWSerialNumber
#   setProdState
#   setPriority
#   setGroups
#   setSystems
"""

    def __init__(self, *args, **kwargs):
        ZCmdBase.__init__(self, *args, **kwargs)
        self.defaults = {}
        self.collectorNames = self.dmd.Monitors.getPerformanceMonitorNames()
        self.loader = self.dmd.DeviceLoader.loadDevice
        self.fqdn = socket.getfqdn()
        self.baseEvent = dict(
            device=self.fqdn,
            component='',
            agent='zenbatchload',
            monitor='localhost',
            manager=self.fqdn,
            severity=SEVERITY_ERROR,
            # Note: Change_Add events get sent to history
            # by the event class' Zen property
            eventClass=Change_Add,
        )

        # Create the list of options we want people to know about
        self.loader_args = dict.fromkeys(self.loader.func_code.co_varnames)
        unsupportable_args = [
            'REQUEST', 'device', 'self', 'xmlrpc', 'e', 'handler',
        ]
        for opt in unsupportable_args:
            if opt in self.loader_args:
                del self.loader_args[opt]

    def loadDeviceList(self, args=None):
        """
        Read through all of the files listed as arguments and
        return a list of device entries.

        @parameter args: list of filenames (uses self.args is this is None)
        @type args: list of strings
        @return: list of device specifications
        @rtype: list of dictionaries
        """
        if args is None:
            args = self.args

        device_list = []
        unparseable = []
        for filename in args:
            if filename.strip() != '':
                try:
                    data = open(filename, 'r').readlines()
                except IOError:
                    msg = "Unable to open the file '%s'" % filename
                    self.reportException(msg)
                    continue

                temp_dev_list, temp_unparseable = self.parseDevices(data)
                if temp_dev_list:
                    device_list += temp_dev_list
                if temp_unparseable:
                    unparseable += temp_unparseable

        return device_list, unparseable

    def applyZProps(self, device, device_specs):
        """
        Apply zProperty settings (if any) to the device.

        @parameter device: device to modify
        @type device: DMD device object
        @parameter device_specs: device creation dictionary
        @type device_specs: dictionary
        """
        self.log.debug("Applying zProperties...")
        # Returns a list of (key, value) pairs.
        # Convert it to a dictionary.
        dev_zprops = dict(device.zenPropertyItems())

        for zprop, value in device_specs.items():
            self.log.debug(
                "Evaluating zProperty <%s -> %s> on %s",
                zprop, value, device.id
            )
            if not iszprop(zprop):
                self.log.debug(
                    "Evaluating zProperty <%s -> %s> on %s: not iszprop()",
                    zprop, value, device.id
                )
                continue

            if zprop in dev_zprops:
                try:
                    self.log.debug(
                        "Setting zProperty <%s -> %s> on %s "
                        "(currently set to %s)",
                        zprop, value, device.id,
                        getattr(device, zprop, 'notset')
                    )
                    device.setZenProperty(zprop, value)
                except BadRequest:
                    self.log.warn(
                        "Object %s zproperty %s is invalid or duplicate",
                        device.titleOrId(), zprop
                    )
                except Exception as ex:
                    self.log.warn(
                        "Object %s zproperty %s not set (%s)",
                        device.titleOrId(), zprop, ex
                    )
                self.log.debug(
                    "Set zProperty <%s -> %s> on %s (now set to %s)",
                    zprop, value, device.id, getattr(device, zprop, 'notset')
                )
            else:
                self.log.warn(
                    "The zproperty %s doesn't exist in %s",
                    zprop, device_specs.get('deviceName', device.id)
                )

    def applyCustProps(self, device, device_specs):
        """
        Custom schema properties
        """
        self.log.debug("Applying custom schema properties...")
        dev_cprops = device.custPropertyMap()

        for cprop, value in device_specs.items():
            if not iscustprop(cprop):
                continue

            matchProps = [prop for prop in dev_cprops if prop['id'] == cprop]
            if matchProps:
                ctype = matchProps[0]['type']
                if ctype == 'password':
                    ctype = 'string'
                if ctype in type_converters and value:
                    value = type_converters[ctype](value)
                device.setZenProperty(cprop, value)
            else:
                self.log.warn(
                    "The cproperty %s doesn't exist in %s",
                    cprop, device_specs.get('deviceName', device.id)
                )

    def addAllLGSOrganizers(self, device_specs):
        location = device_specs.get('setLocation')
        if location:
            self.addLGSOrganizer('Locations', (location,))

        systems = device_specs.get('setSystems')
        if systems:
            if not isinstance(systems, list) \
                    and not isinstance(systems, tuple):
                systems = (systems,)
            self.addLGSOrganizer('Systems', systems)

        groups = device_specs.get('setGroups')
        if groups:
            if not isinstance(groups, list) and not isinstance(groups, tuple):
                groups = (groups,)
            self.addLGSOrganizer('Groups', groups)

    def addLGSOrganizer(self, lgsType, paths=()):
        """
        Add any new locations, groups or organizers
        """
        prefix = '/zport/dmd/' + lgsType
        base = getattr(self.dmd, lgsType)
        if hasattr(base, 'sync'):
            base.sync()
        existing = [x.getPrimaryUrlPath().replace(prefix, '')
                    for x in base.getSubOrganizers()]
        for path in paths:
            if path in existing:
                continue
            try:
                base.manage_addOrganizer(path)
            except BadRequest:
                pass

    @transactional
    def addOrganizer(self, device_specs):
        """
        Add any organizers as required, and apply zproperties to them.
        """
        path = device_specs.get('devicePath')
        baseOrg = path.split('/', 2)[1]
        base = getattr(self.dmd, baseOrg, None)
        if base is None:
            self.log.error(
                "The base of path %s (%s) does not exist -- skipping",
                baseOrg, path
            )
            return

        try:
            org = base.getDmdObj(path)
        except KeyError:
            try:
                self.log.info("Creating organizer %s", path)

                @transactional
                def inner(self):
                    base.manage_addOrganizer(path)

                inner(self)
                org = base.getDmdObj(path)
            except IOError:
                self.log.error(
                    "Unable to create organizer! "
                    "Is Rabbit up and configured correctly?"
                )
                sys.exit(1)
        self.applyZProps(org, device_specs)
        self.applyCustProps(org, device_specs)
        self.applyOtherProps(org, device_specs)

    def applyOtherProps(self, device, device_specs):
        """
        Apply non-zProperty settings (if any) to the device.

        @parameter device: device to modify
        @type device: DMD device object
        @parameter device_specs: device creation dictionary
        @type device_specs: dictionary
        """
        self.log.debug("Applying other properties...")
        internalVars = [
            'deviceName', 'devicePath', 'loader', 'loader_arg_keys', 'manageIp',
        ]

        @transactional
        def setNamedProp(self, org, name, description):
            setattr(org, name, description)

        for functor, value in device_specs.items():
            if iszprop(functor) or \
                    iscustprop(functor) or functor in internalVars:
                continue

            # Special case for organizers which can take a description
            if functor in ('description', 'address', 'comments', 'rackSlot'):
                if hasattr(device, functor):
                    setNamedProp(self, device, functor, value)
                continue

            try:
                self.log.debug(
                    "For %s, calling device.%s(%s)",
                    device.id, functor, value
                )
                func = getattr(device, functor, None)
                if func is None or not callable(func):
                    self.log.warn(
                        "The function '%s' for device %s is not found.",
                        functor, device.id
                    )
                elif isinstance(value, (list, tuple)):
                    # The function either expects a list or arguments
                    # So, try as an arguments
                    try:
                        func(*value)
                    # Try as a list
                    except TypeError:
                        func(value)
                else:
                    func(value)
            except ConflictError:
                raise
            except Exception:
                msg = "Device %s device.%s(%s) failed" % (
                    device.id, functor, value
                )
                self.reportException(msg, device.id)

    def runLoader(self, loader, device_specs):
        """
        It's up to the loader now to figure out what's going on.

        @parameter loader: device loader
        @type loader: callable
        @parameter device_specs: device entries
        @type device_specs: dictionary
        """
        argKeys = device_specs.get('loader_arg_keys', [])
        loader_args = {}
        for key in argKeys:
            if key in device_specs:
                loader_args[key] = device_specs[key]

        result = loader().load_device(self.dmd, **loader_args)

        # If the loader returns back a device object, carry
        # on processing
        if isinstance(result, Device):
            return result
        return None

    def processDevices(self, device_list):
        """
        Read the input and process the devices
          * create the device entry
          * set zproperties
          * set custom schema properties
          * model the device

        @parameter device_list: list of device entries
        @type device_list: list of dictionaries
        @return: status of device loading
        @rtype: dictionary
        """

        # If nocommit is set, tell the DistributedCollector
        # not to modify the controlplane services
        if self.options.nocommit:
            try:
                from ZenPacks.zenoss.DistributedCollector import \
                    ExtendedControlPlaneClient
                ExtendedControlPlaneClient.readonly = True
            except ImportError:
                pass

        processed = {'processed': 0, 'errors': 0, 'no_IP': 0}

        @transactional
        def _process(self, device_specs):
            # Get the latest bits
            self.dmd.zport._p_jar.sync()

            loaderName = device_specs.get('loader')
            if loaderName is not None:
                try:
                    orgName = device_specs['devicePath']
                    organizer = self.dmd.getObjByPath('dmd' + orgName)
                    deviceLoader = getUtility(
                        IDeviceLoader, loaderName, organizer
                    )
                    devobj = self.runLoader(deviceLoader, device_specs)
                except ConflictError:
                    raise
                except ComponentLookupError:
                    self.log.critical(
                        "Unknown device loader '%s'", loaderName
                    )
                    sys.exit(1)
                except Exception:
                    devName = device_specs.get(
                        'device_specs', 'Unknown Device'
                    )
                    msg = "Ignoring device loader issue for %s" % devName
                    self.reportException(
                        msg, devName, specs=str(device_specs)
                    )
                    processed['errors'] += 1
                    return
            else:
                deviceLoader = None
                devobj = None
                if self.validDeviceSpec(processed, device_specs):
                    try:
                        device_specs['manageIp'] = \
                            device_specs.pop('setManageIp')
                    except KeyError:
                        pass
                    devobj = self.getDevice(device_specs)

            if devobj is None:
                if deviceLoader is not None:
                    processed['processed'] += 1
            else:
                self.addAllLGSOrganizers(device_specs)
                self.applyZProps(devobj, device_specs)
                self.applyCustProps(devobj, device_specs)
                self.applyOtherProps(devobj, device_specs)

                if not self.options.nocommit and isinstance(devobj, Device):
                    notify(IndexingEvent(devobj))

            return devobj

        @transactional
        def _snmp_community(self, device_specs, devobj):
            # Discover the SNMP community if it isn't explicitly set.
            if 'zSnmpCommunity' not in device_specs:
                self.log.debug('Discovering SNMP version and community')
                devobj.manage_snmpCommunity()

        @transactional
        def _model(self, devobj):
            try:
                devobj.collectDevice(setlog=self.options.showModelOutput)
            except ConflictError:
                raise
            except Exception as ex:
                msg = "Modeling error for %s" % devobj.id
                self.reportException(msg, devobj.id, exception=str(ex))
                processed['errors'] += 1
            processed['processed'] += 1

        for device_specs in device_list:
            devobj = _process(self, device_specs)

            # We need to commit in order to model, so don't bother
            # trying to model unless we can do both
            if devobj and not self.options.nocommit \
                    and not self.options.nomodel:
                _snmp_community(self, device_specs, devobj)
                _model(self, devobj)

        processed['total'] = len(device_list)

        # This should be unnecessary, but just to be safe:
        if self.options.nocommit:
            try:
                from ZenPacks.zenoss.DistributedCollector import \
                    ExtendedControlPlaneClient
                ExtendedControlPlaneClient.readonly = False
            except ImportError:
                pass

        return processed

    def validDeviceSpec(self, processed, device_specs):
        if 'deviceName' not in device_specs:
            return False

        if self.options.must_be_resolvable \
                and 'setManageIp' not in device_specs \
                and not isip(device_specs['deviceName']):
            try:
                socket.gethostbyname(device_specs['deviceName'])
            except socket.error:
                processed['no_IP'] += 1
                return False

        return True

    def reportException(self, msg, devName='', **kwargs):
        """
        Report exceptions back to the the event console
        """
        self.log.exception(msg)
        if not self.options.nocommit:
            evt = self.baseEvent.copy()
            evt.update(dict(
                summary=msg,
                traceback=format_exc()
            ))
            evt.update(kwargs)
            if devName:
                evt['device'] = devName
            self.dmd.ZenEventManager.sendEvent(evt)

    def reportResults(self, processed):
        """
        Report the success + total counts from loading devices.
        """
        msg = "Processed %d of %d devices, with %d errors" % (
            processed['processed'], processed['total'], processed['errors'])
        self.log.info(msg)
        self.log.info("Unable to process %d entries", processed['unparseable'])

        if not self.options.nocommit:
            evt = self.baseEvent.copy()
            evt.update(dict(
                severity=SEVERITY_INFO,
                summary=msg,
                modeled=processed['processed'],
                errors=processed['errors'],
                total=processed['total'],
                unparseable=processed['unparseable'],
            ))
            self.dmd.ZenEventManager.sendEvent(evt)

    def notifyNewDeviceCreated(self, deviceName):
        """
        Report that we added a new device.
        """
        if not self.options.nocommit:
            evt = self.baseEvent.copy()
            evt.update(dict(
                severity=SEVERITY_INFO,
                summary="Added new device %s" % deviceName
            ))
            self.dmd.ZenEventManager.sendEvent(evt)

    def getDevice(self, device_specs):
        """
        Find or create the specified device

        @parameter device_specs: device creation dictionary
        @type device_specs: dictionary
        @return: device or None
        @rtype: DMD device object
        """
        if 'deviceName' not in device_specs:
            return None
        name = device_specs['deviceName']
        devobj = self.dmd.Devices.findDevice(name)
        if devobj is not None:
            self.log.info("Found existing device %s", name)
            return devobj

        specs = {}
        for key in self.loader_args:
            if key in device_specs:
                specs[key] = device_specs[key]

        try:
            self.log.info(
                "Creating initial device %s "
                "(customized properties are set after creation)", name
            )

            # Do NOT model at this time
            specs['discoverProto'] = 'none'

            self.loader(**specs)
            devobj = self.dmd.Devices.findDevice(name, commit_dirty=True)
            if devobj is None:
                self.log.error(
                    "Unable to find newly created device %s -- skipping", name
                )
            else:
                self.notifyNewDeviceCreated(name)

        except Exception:
            msg = "Unable to load %s -- skipping" % name
            self.reportException(msg, name)

        return devobj

    def buildOptions(self):
        """
        Add our command-line options to the basics
        """
        ZCmdBase.buildOptions(self)

        self.parser.add_option('--show_options',
                               dest="show_options", default=False,
                               action="store_true",
                               help="Show the various options understood by "
                                    "the loader")

        self.parser.add_option('--sample_configs',
                               dest="sample_configs", default=False,
                               action="store_true",
                               help="Show an example configuration file.")

        self.parser.add_option('--showModelOutput',
                               dest="showModelOutput", default=True,
                               action="store_false",
                               help="Show modelling activity")

        self.parser.add_option('--nocommit',
                               dest="nocommit", default=False,
                               action="store_true",
                               help="Don't commit changes to the ZODB. "
                                    "Use for verifying config file.")

        self.parser.add_option('--nomodel',
                               dest="nomodel", default=False,
                               action="store_true",
                               help="Don't model the remote devices. "
                                    "Must be able to commit changes.")

        self.parser.add_option('--reject_file', dest="reject_file",
                               help="If specified, use as the name of a file "
                                    "to store unparseable lines")

        self.parser.add_option('--must_be_resolvable',
                               dest="must_be_resolvable", default=False,
                               action="store_true",
                               help="Do device entries require an IP address "
                                    "or be DNS resolvable?")

    def parseDevices(self, data):
        """
        From the list of strings in rawDevices, construct a list
        of device dictionaries, ready to load into Zenoss.

        @parameter data: list of strings representing device entries
        @type data: list of strings
        @return: list of parsed device entries
        @rtype: list of dictionaries
        """
        if not data:
            return []

        comment = re.compile(r'^\s*#.*')

        defaults = {'devicePath': "/Discovered"}
        finalList = []
        unparseable = []
        i = 0
        while i < len(data):
            line = data[i]
            line = re.sub(comment, '', line).strip()
            if line == '':
                i += 1
                continue

            # Check for line continuation character '\'
            while line[-1] == '\\' and i < len(data):
                i += 1
                line = line[:-1] + data[i]
                line = re.sub(comment, '', line).strip()

            if line[0] == '/' or line[1] == '/':  # Found an organizer
                defaults = self.parseDeviceEntry(line, {})
                if defaults is None:
                    defaults = {'devicePath': "/Discovered"}
                else:
                    defaults['devicePath'] = defaults['deviceName']
                    del defaults['deviceName']
                self.addOrganizer(defaults)

            else:
                configs = self.parseDeviceEntry(line, defaults)
                if configs:
                    finalList.append(configs)
                else:
                    unparseable.append(line)
            i += 1

        return finalList, unparseable

    def parseDeviceEntry(self, line, defaults):
        """
        Build a dictionary of properties from one line's input

        @parameter line: string containing one device's info
        @type line: string
        @parameter defaults: dictionary of default settings
        @type defaults: dictionary
        @return: parsed device entry
        @rtype: dictionary
        """
        options = []
        # Note: organizers and device names can have spaces in them
        if line[0] in ["'", '"']:
            delim = line[0]
            eom = line.find(delim, 1)
            if eom == -1:
                self.log.error(
                    "While reading name, unable to parse the entry "
                    "for %s -- skipping", line
                )
                return None
            name = line[1:eom]
            options = line[eom + 1:]

        else:
            options = line.split(None, 1)
            name = options.pop(0)
            if options:
                options = options.pop(0)

        configs = defaults.copy()
        configs['deviceName'] = name

        if options:
            try:
                # Add a newline to allow for trailing comments
                evalString = 'dict(' + options + '\n)'
                optionsDict = eval(evalString)
                configs.update(optionsDict)

                collector = configs.get('performanceMonitor')
                if collector is not None:
                    if collector not in self.collectorNames:
                        self.log.warn(
                            "'%s' collector '%s' does not exist "
                            "-- resetting to 'localhost'", name, collector
                        )
                        del configs['performanceMonitor']

            except Exception:
                self.log.error(
                    "Unable to parse the entry for %s -- skipping", name
                )
                self.log.error("Raw string: %s", options)
                return None

        return configs

    def writeRejectFile(self, name, rejects):
        """
        Attempt to write out any unparseable or rejected devices to file
        """
        try:
            fd = open(name, 'w')
            for line in rejects:
                fd.write('%s\n' % line)
            fd.close()
        except IOError as ex:
            self.log.debug("Unable to write rejects to '%' because: %s",
                           name, ex)


if __name__ == '__main__':
    batchLoader = BatchDeviceLoader()
    if batchLoader.options.show_options:
        print "Options = %s" % sorted(batchLoader.loader_args.keys())
        help(batchLoader.loader)
        sys.exit(0)

    if batchLoader.options.sample_configs:
        print batchLoader.sample_configs
        sys.exit(0)

    device_list, unparseable = batchLoader.loadDeviceList()
    if unparseable and batchLoader.options.reject_file is not None:
        batchLoader.writeRejectFile(
            batchLoader.options.reject_file, unparseable
        )

    if not device_list:
        msg = "No device entries found to load"
        if unparseable:
            msg += " and %d unparseable lines" % len(unparseable)
        batchLoader.log.warn(msg)
        sys.exit(1)

    results = batchLoader.processDevices(device_list)
    results['unparseable'] = len(unparseable)
    batchLoader.reportResults(results)
    sys.exit(0)
