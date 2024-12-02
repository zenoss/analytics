##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""zenbatchdump

zenbatchdump dumps a list of devices to a file.
"""

from __future__ import absolute_import

import platform
import re
import sys

from collections import defaultdict
from datetime import datetime


from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer


class BatchDeviceDumper(ZCmdBase):
    sample_configs = """#
# zenbatchdump run on host zenoss41 on date 2011-10-16 16:34:23.569920
# with --root=Devices/Server/Linux
# To load this Device dump file, use:
#   zenbatchload <file>


'/Locations'
'/Locations/TestZenBatchDumper'
'/Locations/TestZenBatchDumper/City1'
'/Locations/TestZenBatchDumper/City1/Building1'
'/Locations/TestZenBatchDumper/City2'


'/Systems'
'/Systems/TestZenBatchDumper'
'/Systems/TestZenBatchDumper/System1'
'/Systems/TestZenBatchDumper/Scary/System2'
'/Systems/TestZenBatchDumper/Scary/System3'


'/Groups'
'/Groups/TestZenBatchDumper'
'/Groups/TestZenBatchDumper/Production'
'/Groups/TestZenBatchDumper/Production/Critical'
'/Groups/TestZenBatchDumper/Production/Secondary'
'/Groups/TestZenBatchDumper/TEST'
'/Groups/TestZenBatchDumper/DEV'

'/Devices/TestZenBatchDumper'  zCollectorPlugins=['zenoss.snmp.NewDeviceMap', 'zenoss.snmp.DeviceMap', 'HPDeviceMap', 'DellDeviceMap', 'zenoss.snmp.InterfaceMap', 'zenoss.snmp.RouteMap', 'zenoss.snmp.IpServiceMap', 'zenoss.snmp.HRFileSystemMap', 'zenoss.snmp.HRSWInstalledMap', 'zenoss.snmp.HRSWRunMap', 'zenoss.snmp.CpuMap', 'HPCPUMap', 'DellCPUMap', 'DellPCIMap'], zIcon='/zport/dmd/img/icons/server.png'

'/Devices/TestZenBatchDumper/Server'  zCollectorPlugins=['zenoss.snmp.NewDeviceMap', 'zenoss.snmp.DeviceMap', 'HPDeviceMap', 'DellDeviceMap', 'zenoss.snmp.InterfaceMap', 'zenoss.snmp.RouteMap', 'zenoss.snmp.IpServiceMap', 'zenoss.snmp.HRFileSystemMap', 'zenoss.snmp.HRSWInstalledMap', 'zenoss.snmp.HRSWRunMap', 'zenoss.snmp.CpuMap', 'HPCPUMap', 'DellCPUMap', 'DellPCIMap'], zIcon='/zport/dmd/img/icons/server.png'

'/Devices/TestZenBatchDumper/Server/Linux'  zCollectorPlugins=['zenoss.snmp.NewDeviceMap', 'zenoss.snmp.DeviceMap', 'HPDeviceMap', 'DellDeviceMap', 'zenoss.snmp.InterfaceMap', 'zenoss.snmp.RouteMap', 'zenoss.snmp.IpServiceMap', 'zenoss.snmp.HRFileSystemMap', 'zenoss.snmp.HRSWRunMap', 'zenoss.snmp.CpuMap', 'HPCPUMap', 'DellCPUMap', 'DellPCIMap'], zHardDiskMapMatch='^[hs]d[a-z]\\d+$|c\\d+t\\d+d\\d+s\\d+$|^cciss\\/c\\dd\\dp\\d$|^dm\\-\\d$', zIcon='/zport/dmd/img/icons/server-linux.png', zIpServiceMapMaxPort=8090

'localhost' setHWProductKey=('.1.3.6.1.4.1.8072.3.2.10', 'net snmp'), setHWSerialNumber='', setHWTag='', setLastChange=DateTime('2011/10/16 09:07:53.208444 GMT-7'), setManageIp='127.0.0.1', setOSProductKey='Linux 2.6.18-164.el5', setPriority=3, setProdState=1000, setPerformanceMonitor='localhost'

'thor' setLocation='/Locations/TestZenBatchDumper/City1', setSystems=['/Systems/TestZenBatchDumper/Scary/System2', '/Systems/TestZenBatchDumper/System1'], setGroups=['/Groups/TestZenBatchDumper/TEST', '/Groups/TestZenBatchDumper/DEV'], setHWProductKey=('.1.3.6.1.4.1.8072.3.2.10', 'net snmp'), setHWSerialNumber='', setHWTag='', setLastChange=DateTime('2011/10/16 09:22:59.450108 GMT-7'), setManageIp='192.168.55.225', setOSProductKey='Linux 2.6.32-25-server', setPriority=4, setProdState=1000, setPerformanceMonitor='localhost'

'loki' setLocation='/Locations/TestZenBatchDumper/City2', setSystems=['/Systems/TestZenBatchDumper/System1'], setGroups=['/Groups/TestZenBatchDumper/Production/Critical'], setHWProductKey=('.1.3.6.1.4.1.8072.3.2.10', 'net snmp'), setHWSerialNumber='', setHWTag='', setLastChange=DateTime('2011/10/16 09:19:59.450108 GMT-7'), setManageIp='192.168.55.223', setOSProductKey='Linux 2.6.32-25-server', setPriority=4, setProdState=1000, setPerformanceMonitor='localhost'

'/Devices/TestZenBatchDumper/Server/Windows'  zCollectorPlugins=['zenoss.snmp.NewDeviceMap', 'zenoss.snmp.DeviceMap', 'HPDeviceMap', 'DellDeviceMap', 'zenoss.snmp.InterfaceMap', 'zenoss.snmp.RouteMap', 'zenoss.snmp.IpServiceMap', 'zenoss.snmp.HRFileSystemMap', 'zenoss.snmp.HRSWInstalledMap', 'zenoss.snmp.HRSWRunMap', 'zenoss.snmp.CpuMap', 'HPCPUMap', 'DellCPUMap', 'DellPCIMap', 'zenoss.snmp.InformantHardDiskMap', 'zenoss.wmi.WinServiceMap'], zHardDiskMapMatch='.*', zIcon='/zport/dmd/img/icons/server-windows.png', zWinEventlog=True, zWmiMonitorIgnore=False

'/Devices/TestZenBatchDumper/Server/Windows/WMI'  zCollectorPlugins=['zenoss.wmi.WindowsDeviceMap', 'zenoss.wmi.WinServiceMap', 'zenoss.wmi.CpuMap', 'zenoss.wmi.FileSystemMap', 'zenoss.wmi.IpInterfaceMap', 'zenoss.wmi.IpRouteMap', 'zenoss.wmi.MemoryMap', 'zenoss.wmi.ProcessMap', 'zenoss.wmi.SoftwareMap'], zDeviceTemplates=['Device_WMI'], zWinPerfCycleSeconds=300, zWinPerfCyclesPerConnection=10

'192.168.5.219' zWinPassword='easyPassword', zWinUser='admin', setLocation='/Locations/TestZenBatchDumper/City1/Building1', setGroups=['/Groups/TestZenBatchDumper/Production/Secondary'], setHWProductKey=('Unknown', 'Chassis Manufacture'), setHWSerialNumber='Chassis Serial Number', setHWTag='Asset-1234567890', setLastChange=DateTime('2011/10/16 09:19:56.920976 GMT-7'), setManageIp='192.168.55.229', setOSProductKey=('Windows 7 Home Premium ', 'Microsoft'), setPriority=3, setProdState=1000, setPerformanceMonitor='localhost'


# Dumped:
#            Locations: 5
#               Groups: 7
#              Systems: 5
#        DeviceClasses: 5
#              Devices: 4
"""
    # Do not export out the following setter method data
    ignoreSetters = (
        "setLastPollSnmpUpTime",
        "setSnmpLastCollection",
        "setSiteManager",
        "setLocation",
        "setGroups",
        "setSystems",
        "setProperty",
        "setZenProperty",
    )

    _ucsTypes = {
        "UCS-Manager": "ucsmanager",
        "C-Series": "cimc-c",
        "E-Series": "cimc-e",
    }

    _ucsTypeMatcher = re.compile(
        r"/(%s)" % r"|".join(r"%s\b" % k for k in _ucsTypes.keys())
    )

    def __init__(self, *args, **kwargs):
        ZCmdBase.__init__(self, *args, **kwargs)
        self.defaults = {}
        self.emittedDeviceClasses = set()

    def _prepRoot(self):
        """
        initializes and verify the device root and prune options properly

        @return: was initialization successful
        @rtype: bool
        """
        if hasattr(self, "root"):
            return True

        if self.options.root == "":
            self.root = self.dmd.Devices
            self.options.prune = False
        else:
            try:
                self.root = self.dmd.unrestrictedTraverse(self.options.root)
            except KeyError:
                self.log.error(
                    "%s is not a valid DeviceOrganizer path under %s\n",
                    self.options.root,
                    self.dmd.getPrimaryUrlPath(),
                )
                return False

        self.rootPath = self.root.getPrimaryUrlPath()

        # Because it's possible to follow multiple routes through a tree,
        # ensure that at the end of the day we only process things from
        # our original root object
        self.cachedRootSubDevices = self.root.getSubDevices()
        return True

    def _emitProps(self, obj):
        """
        Returns string of object local zProperties, cProperties and "setter"
        properties suitable for ZenBatchLoader

        @parameter obj: a Device or DeviceClass (or perhaps Location later)
        @type obj: ZenModelRM
        @return: string containing local zProperties as documented in above sample
        @rtype str
        """
        props = []

        # description has neither setter nor getter so we special-case it here
        desc = getattr(obj, "description", "")
        if desc:
            props.append("%s=%s" % ("description", repr(desc)))

        def exportZProperties(obj):
            # 4.x has dev.exportZProperties()
            if hasattr(obj, "exportZProperties"):
                return obj.exportZProperties()
            # 3.x *might* have zenPropertyIds
            props = []
            if not hasattr(obj, "zenPropertyIds"):
                return props
            for zId in obj.zenPropertyIds():
                prop = {
                    "id": zId,
                    "islocal": obj.hasProperty(zId),
                    "type": obj.getPropertyType(zId),
                    "path": obj.zenPropertyPath(zId),
                    "options": obj.zenPropertyOptions(zId),
                    "value": None,
                    "valueAsString": obj.zenPropertyString(zId),
                }
                if not obj.zenPropIsPassword(zId):
                    prop["value"] = obj.getZ(zId)
                else:
                    prop["value"] = obj.zenPropertyString(zId)
                props.append(prop)

            return props

        # Z-properties
        for prop in (
            (x["id"], repr(x["value"]))
            for x in exportZProperties(obj)
            if self.isPropExportable(x)
        ):
            key = prop[0]
            if obj.zenPropIsPassword(key):
                val = repr(getattr(obj, key, ""))
                prop = (key, val)
            props.append("%s=%s" % prop)

        # C-properties
        for cProp in obj.custPropertyMap():
            if cProp["id"] == "cDateTest":
                continue
            value = getattr(obj, cProp["id"], "")
            if value and value != "":
                props.append("%s=%s" % (cProp["id"], repr(value)))

        for setMethod in [
            setter for setter in dir(obj) if setter.startswith("set")
        ]:
            if setMethod in self.ignoreSetters:
                continue
            getMethod = setMethod.replace("set", "get", 1)
            getter = getattr(obj, getMethod, None)
            if getter and callable(getter):
                # Deal with brain damaged get/setProdState
                if setMethod == "setProdState":
                    states = obj.getProdStateConversions()
                    for state in states:
                        if getter() in state:
                            value = state[1]
                else:
                    try:
                        value = getter()
                    except Exception:
                        msg = "Unable to use '%s' getter() method on %s" % (
                            getMethod,
                            obj.getPrimaryUrlPath(),
                        )
                        self.log.exception(msg)
                if value and value != "":
                    props.append("%s=%s" % (setMethod, repr(value)))
            else:
                # for setters that have no getter, try a bare attribute
                value = getattr(obj, setMethod[3:].lower(), None)
                if value and value != "":
                    props.append("%s=%s" % (setMethod, repr(value)))

        # There's always got to be a weirdie....
        if "getPerformanceServerName" in dir(obj):
            props.append(
                "setPerformanceMonitor=" + repr(obj.getPerformanceServerName())
            )
        return sorted(props)

    def isPropExportable(self, propdict):
        """
        Dump the specified property to the output file?
        propdict contents:
             id - name of the zprop
             category - as displayed in the 'Configuration Property' area
             islocal - overridden here?
             value - raw value
             options - complete list of items that can be chosen
             valueAsString - value in string format
             path - path of where the zprop was defined
             type - 'password', 'string', 'int', 'float', 'date', 'lines'

        """
        return propdict["islocal"]

    def _emitDev(self, dev):
        """
        Returns a device and its zProperties in strings appropriate for ZenBatchLoader

        @parameter dev: Device object to emit
        @type dev: Device
        @return: device name and list of Device-local zProperties and cProperties
        @rtype: tuple of strings
        """

        result = self._emitProps(dev)

        location = dev.location()
        if location:
            result.append(
                "setLocation=" + repr("/".join(location.getPrimaryPath()[4:]))
            )

        systems = self._normalizePaths(dev.systems())
        if systems:
            result.append("setSystems=" + repr(systems))

        groups = self._normalizePaths(dev.groups())
        if groups:
            result.append("setGroups=" + repr(groups))

        if self.options.noorganizers:
            # Need to be able to tell which device class we came from
            result.append(
                "moveDevices=('%s', '%s')"
                % ("/".join(dev.getPrimaryPath()[:-2]), dev.id)
            )

        if dev.comments:
            result.append("comments=%r" % (dev.comments,))

        return (repr(dev.getId()), sorted(result))

    def _normalizePaths(self, objList):
        """
        Given a list of objects, make their URL path representation
        look closer to what is seen in 'Infrastructure' view.
        """
        return sorted(
            "/" + "/".join(obj.getPrimaryPath()[4:]) for obj in objList
        )

    def _emitOrg(self, org):
        """
        Returns a device organizer with its type and local properties

        @parameter org: DeviceOrganizer to emit
        @type org: DeviceOrganizer
        @return: device organizer name, type and properties
        @rtype: tuple of strings
        """
        path = org.getPrimaryPath()
        name = "'/%s' " % "/".join(path[3:])
        props = self._emitProps(org)

        if "/Locations/" in path:
            props.append('setAddress="%s"' % org.address)

        return (name, props)

    def _backtraceOrg(self, outFile, obj):
        """
        Recurse upward from a device emitting parent DeviceClasses if not already emitted

        @parameter outFile: file object to which output is written
        @type outFile: file or other object with .write() method that is simillar
        @parameter dev: Device/DeviceClass for whom we emit parent Organizer paths
        @type dev: Device or DeviceClass
        @return: number of DeviceClasses emitted
        @rtype: int
        """

        result = 0
        if isinstance(obj, Device):
            # back out to first containing DeviceOrganizer
            obj = obj.getPrimaryParent().getPrimaryParent()

        if obj not in self.emittedDeviceClasses:
            parent = obj.getPrimaryParent()
            # don't recurse to dmd
            if parent.getPrimaryPath()[2:] != self.dmd.getPrimaryPath()[2:]:
                result = self._backtraceOrg(outFile, parent)

            definition = self.getLoaderDefinition(obj)
            if definition is None:
                name, props = self._emitOrg(obj)
            else:
                name, props = definition

            outFile.write("\n%s %s\n" % (name, ", ".join(props)))
            self.emittedDeviceClasses.add(obj)
            result += 1
        return result

    def listLSGOTree(self, outFile, branch):
        """
        Recurse through the Locations, Systems and Groups trees
        printing out Organizers with properties

        @parameter outFile: output object to which we write output
        @type outFile: file or other object with .write() method that is simillar
        @parameter branch: object reference to current tree branch
        @type branch: DeviceOrganizer
        @return: number of Locations, Systems or Groups dumped
        @rtype: int
        """
        if getattr(self, "rootPath", None) is None:
            # for unit tests and unexpected uses
            if not self._prepRoot():
                return -1

        result = 0

        if not isinstance(branch, DeviceOrganizer):
            raise TypeError(
                "listLSGOTree must start in a DeviceOrganizer not (%s)"
                % branch
            )

        # Hidden option for pruning LSG Organizers as pruned
        # ones may get referenced by unpruned devices
        # This is to be used by unit tests to simplify output
        if (
            getattr(self.options, "pruneLSGO", None)
            and not isinstance(self.root, DeviceClass)
            and not (
                branch.getPrimaryUrlPath().startswith(self.rootPath)
                or self.root.getPrimaryUrlPath().startswith(
                    branch.getPrimaryUrlPath()
                )
            )
        ):
            return result

        outFile.write("\n")
        (name, props) = self._emitOrg(branch)
        result += 1
        outFile.write("\n%s %s\n" % (name, ", ".join(props)))

        for org in branch.children():
            result += self.listLSGOTree(outFile, org)
        return result

    def makeRegexMatcher(self):
        if self.options.regex:
            regex = re.compile(self.options.regex)
            return lambda dev: dev is not None and regex.match(
                dev.getPrimaryId()
            )

    def chooseDevice(self, root, matcher=None):
        for dev in root.devices():
            if dev not in self.cachedRootSubDevices:
                continue
            if matcher:
                if matcher(dev):
                    yield dev
            else:
                yield dev

    def listDeviceTree(self, outFile, branch=None):
        """
        Recurse through the Devices tree printing out Organizers and
        Devices with properties
        return number of Devices emitted

        @parameter outFile: output object to which we write output
        @type outFile: file or other object with .write() method that is simillar
        @parameter branch: object reference to current tree branch
        @type branch: DeviceClass (or perhaps DeviceOrganizer at worst)
        @return: number of leaf Devices and DeviceClasses dumped
        @rtype: dict
        """
        if getattr(self, "rootPath", None) is None:
            # for unit tests and unexpected uses
            if not self._prepRoot():
                return {"fail": True}

        if branch is None:
            branch = self.root

        if not isinstance(branch, DeviceClass):
            raise TypeError(
                "listDeviceTree must start in a DeviceClass not "
                + repr(branch)
            )

        self.device_regex = self.makeRegexMatcher()

        return self._listDeviceTree(outFile, branch)

    def _listDeviceTree(self, outFile, branch=None):
        result = defaultdict(int)
        result["DeviceClasses"] = 0
        result["Devices"] = 0

        # Dump DeviceClass if not pruned
        if (
            not self.options.prune
            or branch.getPrimaryUrlPath() in self.rootPath
        ):
            if not self.options.noorganizers:
                outFile.write("\n")
                definition = self.getLoaderDefinition(branch)
                if definition is None:
                    name, props = self._emitOrg(branch)
                else:
                    name, props = definition
                    # add zProperties and others here to UCS device class
                    # workaround of workaround
                    _, emit_props = self._emitOrg(branch)
                    if emit_props:
                        props.extend(emit_props)
                result["DeviceClasses"] += 1
                outFile.write("\n%s %s\n" % (name, ", ".join(props)))
                self.emittedDeviceClasses.add(branch)

        # Dump all eligible Devices in this DeviceClass
        # (pruning occurs in .chooseDevice() )
        for dev in self.chooseDevice(branch, self.device_regex):
            try:
                name = dev.titleOrId()
                props = self.getLoaderProps(dev)
                if props is None:
                    (name, props) = self._emitDev(dev)
            except Exception:
                # Due to the fact that there might be a ZODB device issue,
                # do as little as possible
                msg = "Unable to export %s" % dev
                self.log.critical(msg)
                self.log.exception(msg)
                continue

            if not self.options.noorganizers:
                # ensure that if we've pruned Organizers above this
                # Device that we emit them first
                result["DeviceClasses"] += self._backtraceOrg(outFile, dev)

            outFile.write("\n%s %s\n" % (name, ", ".join(props)))
            result["Devices"] += 1

        # Recurse on down the tree
        # Unless we're in VMware land...
        if branch.getPrimaryUrlPath() == "/zport/dmd/Devices/VMware":
            found = self.listVMwareEndpoints(outFile, branch)
            result["Devices"] += found["Devices"]
            return result

        # ... or in Cisco UCS land....
        if (
            branch.getPrimaryUrlPath() == "/zport/dmd/Devices/CiscoUCS"
            and isinstance(branch, Device)
        ):
            found = self.listCiscoUCS(outFile, branch)
            result["Devices"] += found["Devices"]
            return result

        for org in branch.children():
            found = self._listDeviceTree(outFile, org)
            result["Devices"] += found["Devices"]
            result["DeviceClasses"] += found["DeviceClasses"]
        return result

    def buildOptions(self):
        """
        Add our command-line options to the basics
        """
        ZCmdBase.buildOptions(self)

        self.parser.add_option(
            "--root",
            dest="root",
            default="",
            help="Set the root Device Path to dump (eg: /Devices/Servers "
            "or /Devices/Network/Cisco/Nexus; default: /Devices)",
        )

        self.parser.add_option(
            "-o",
            "--outFile",
            dest="outFile",
            default=sys.__stdout__,
            help="Specify file to which zenbatchdump will write output",
        )

        self.parser.add_option(
            "--regex",
            dest="regex",
            default="",
            help="Specify include filter for device objects",
        )

        self.parser.add_option(
            "--prune",
            dest="prune",
            default=False,
            action="store_true",
            help="Should DeviceClasses only be dumped if part of root path",
        )

        self.parser.add_option(
            "--allzprops",
            dest="allzprops",
            default=False,
            action="store_true",
            help="Should z properties (including acquired values) be dumped?",
        )

        self.parser.add_option(
            "--noorganizers",
            dest="noorganizers",
            default=False,
            action="store_true",
            help="Should organizers (device classes, groups, etc) be dumped?",
        )

        self.parser.add_option(
            "--collectors_only",
            dest="collectors_only",
            default=False,
            action="store_true",
            help="Dump only the distributed hub/collector information?",
        )

    def run(self):
        """
        Run the batch device dump
        """
        outFile = self.getOutputHandle()

        # ensure we have a valid root
        if self.options.root:
            if self.options.root[0] == "/":
                self.options.root = self.options.root[1:]
            if not self._prepRoot():
                outFile.close()
                sys.exit(2)

        self.printHeader(outFile)
        if hasattr(self.dmd.Monitors, "Hub"):
            self.listHubsCollectors(outFile)
        if self.options.collectors_only:
            outFile.close()
            sys.exit(0)

        foundLSGO = {}
        foundLSGO["Locations"] = self.listLSGOTree(outFile, self.dmd.Locations)
        foundLSGO["Systems"] = self.listLSGOTree(outFile, self.dmd.Systems)
        foundLSGO["Groups"] = self.listLSGOTree(outFile, self.dmd.Groups)
        foundDevices = self.listDeviceTree(outFile)
        self.printTrailer(outFile, foundLSGO, foundDevices)
        outFile.close()

    def getOutputHandle(self):
        if isinstance(self.options.outFile, str):
            if self.options.outFile == "-":
                return sys.stdout
            try:
                outFile = open(self.options.outFile, "w")
            except IOError as e:
                self.log.error(
                    "Cannot open file %s for writing: %s",
                    self.options.outFile,
                    e,
                )
                sys.exit(1)
        else:
            outFile = self.options.outFile
            self.options.outFile = outFile.name

        return outFile

    def printHeader(self, outFile):
        curDate = datetime.now()
        hostname = platform.node()
        outFile.write(
            "# zenbatchdump run on host %s on date %s\n"
            % (hostname, str(curDate))
        )
        outFile.write("# with --root=%s\n" % self.options.root)
        outFile.write("# To load this Device dump file, use:\n")
        outFile.write("#   zenbatchload <file>\n")

    def printTrailer(self, outFile, foundLSGO, foundDevices):
        outFile.write("\n# Dumped:\n")
        for type in foundLSGO:
            outFile.write("#        %13s: %d\n" % (type, foundLSGO[type]))
        for type in foundDevices:
            outFile.write("#        %13s: %d\n" % (type, foundDevices[type]))

    def getLoaderDefinition(self, obj):
        """
        Workaround to avoid adding a dumper interface and RPS'ing all the way back to 2.5.2
        """
        path = obj.getPrimaryPath()
        name = "'/%s' " % "/".join(path[3:])
        path = obj.getPrimaryUrlPath()
        if path == "/zport/dmd/Devices/VMware":
            line = "loader='vmware', loader_arg_keys=['host', 'username', 'password', 'useSsl', 'id', 'collector']"
            return name, [line]

        elif path == "/zport/dmd/Devices/vSphere":
            line = "loader='VMware vSphere', loader_arg_keys=['title', 'hostname', 'username', 'password', 'ssl', 'collector']"
            return name, [line]

        elif path.startswith("/zport/dmd/Devices/CiscoUCS"):
            loaderArgKeys = [
                "host",
                "username",
                "password",
                "useSsl",
                "port",
                "collector",
            ]
            if "UCS-Central" in path:
                loaderName = "ciscoucscentral"
            else:
                loaderName = "ciscoucs"
                loaderArgKeys.append("ucstype")
            line = "loader='%s', loader_arg_keys=%r" % (
                loaderName,
                loaderArgKeys,
            )
            return name, [line]

        elif path.startswith("/zport/dmd/Monitors/Hub/"):
            line = "loader='dc_hub', loader_arg_keys=['hubId', 'poolId']"
            return name, [line]

        elif path.startswith("/zport/dmd/Monitors/Performance/"):
            line = "loader='dc_collector', loader_arg_keys=['monitorId', 'poolId', 'hubPath']"
            return name, [line]

    def getLoaderProps(self, obj):
        """
        Workaround to avoid adding a dumper interface and RPS'ing all the way back to 2.5.2

        Returns an array of strings of the form 'name=value'
        """
        path = obj.getPrimaryUrlPath()
        if path.startswith("/zport/dmd/Devices/VMware"):
            props = dict(
                host=obj.zVMwareViEndpointHost,
                username=obj.zVMwareViEndpointUser,
                password=obj.zVMwareViEndpointPassword,
                id=obj.id,
                collector=obj.zVMwareViEndpointMonitor,
            )
            props = ["%s='%s'" % (key, value) for key, value in props.items()]
            props.append("useSsl=%s" % obj.zVMwareViEndpointUseSsl)
            return props

        elif path.startswith("/zport/dmd/Devices/vSphere"):
            props = dict(
                hostname=obj.zVSphereEndpointHost,
                username=obj.zVSphereEndpointUser,
                password=obj.zVSphereEndpointPassword,
                ssl=obj.zVSphereEndpointUseSsl,
                title=obj.titleOrId(),
                collector=obj.perfServer().id,
            )
            props = ["%s='%s'" % (key, value) for key, value in props.items()]
            return props

        elif path.startswith("/zport/dmd/Devices/CiscoUCS"):
            if "UCS-Central" in path:
                username = obj.zCiscoUCSCentralUsername
                password = obj.zCiscoUCSCentralPassword
                usessl = obj.zCiscoUCSCentralUseSSL
                port = obj.zCiscoUCSCentralPort
            else:
                username = obj.zCiscoUCSManagerUser
                password = obj.zCiscoUCSManagerPassword
                usessl = obj.zCiscoUCSManagerUseSSL
                port = obj.zCiscoUCSManagerPort
            props = dict(
                host=obj.titleOrId(),
                username=username,
                password=password,
                collector=obj.perfServer().id,
            )
            props = ["%s='%s'" % (key, value) for key, value in props.items()]
            props.append("useSsl=%s" % usessl)
            props.append("port=%s" % port)
            matched = self._ucsTypeMatcher.search(path)
            ucstype = self._ucsTypes.get(matched.group(1)) if matched else ""
            if ucstype:
                props.append("ucstype='%s'" % ucstype)
            return props

        elif path.startswith("/zport/dmd/Monitors/Hub/"):
            # Hub
            props = dict(hubId=obj.id, poolId=obj.poolId)
            props = ["%s='%s'" % (key, value) for key, value in props.items()]

            return props

        elif path.startswith("/zport/dmd/Monitors/Performance/"):
            # Collector
            hubPath = obj.hub().getPrimaryUrlPath()
            props = dict(monitorId=obj.id, poolId=obj.poolId, hubPath=hubPath)
            props = ["%s='%s'" % (key, value) for key, value in props.items()]

            return props

    def listVMwareEndpoints(self, outFile, branch):
        result = dict(Devices=0)
        # Note: VMware endpoints are organizers under /Devices/VMware
        for endpoint in branch.children():
            name = endpoint.titleOrId()
            props = self.getLoaderProps(endpoint)
            outFile.write("\n%s %s\n" % (name, ", ".join(props)))
            result["Devices"] += 1

        return result

    def listCiscoUCS(self, outFile, branch):
        result = dict(Devices=0)
        for endpoint in branch.children():
            name = endpoint.titleOrId()
            props = self.getLoaderProps(endpoint)
            outFile.write("\n%s %s\n" % (name, ", ".join(props)))
            result["Devices"] += 1

        return result

    def listHubsCollectors(self, outFile):
        dcHeader = """
#
# ==== Begin distributed hub/collector information ===================
#
# Note:
#   1. The root password for the initial install of a hub/collector
#      is NOT stored, so this output MUST be modified IF passwords
#      are being used (as opposed to SSH keys).
#
#   2. 'installcreds' is either 'rootpasswd' or not (ie random text works fine)
#      This is subject to change.
#
#   3. 'installtype' is either 'local' or not (ie random text works fine)
#
#   4. The 'localhost' hub/collector is *NOT* dumped.
#
#   5. Collector properties are not loadable by zenbatchdump.
#      A commented out version of the properties suitable for running
#      in zendmd is output.
#      awk -F 'ZENDMD ' '/ZENDMD/ { print $2; }' batchloadfile > collector_config.zendmd
#      zendmd --script collector_config.zendmd
#
"""

        dcTrailer = """
# ==== End distributed hub/collector information ===================

"""

        dumpedConfig = False
        for hub in self.dmd.Monitors.Hub.getHubs():
            if hub.id != "localhost":
                if not dumpedConfig:
                    outFile.write(dcHeader)
                    dumpedConfig = True

                # Always dump hub definitions
                name, props = self.getLoaderDefinition(hub)
                name = "/Monitors/Hub"
                outFile.write("\n%s %s\n" % (name, ", ".join(props)))
                props = self.getLoaderProps(hub)
                name = hub.id
                outFile.write("%s %s\n" % (name, ", ".join(props)))

            # Only dump collector definitions once per hub
            dumpedDefLine = False
            for collector in hub.collectors():
                if not dumpedConfig:
                    outFile.write(dcHeader)
                    dumpedConfig = True

                if collector.id == "localhost":
                    self.dumpCollectorProperties(outFile, collector)
                    continue

                if not dumpedDefLine:
                    name, props = self.getLoaderDefinition(collector)
                    name = "/Monitors/Performance"
                    outFile.write("\n%s %s\n" % (name, ", ".join(props)))
                    dumpedDefLine = True

                props = self.getLoaderProps(collector)
                name = collector.id
                outFile.write("%s %s\n" % (name, ", ".join(props)))
                self.dumpCollectorProperties(outFile, collector)

        if dumpedConfig:
            outFile.write(dcTrailer)

        result = dict(Devices=0)
        return result

    def dumpCollectorProperties(self, outFile, collector):
        # Write out configuration information not directly loadable
        # by zenbatchloader
        # The following command is to be run in zendmd
        preface = "col=%s" % ".".join(collector.getPrimaryPath()[2:])
        props = [preface]
        for key, value in sorted(collector.propertyItems()):
            if isinstance(value, str):
                if not value:
                    continue  # Don't add empty strings
                value = "'%s'" % value
            data = "col.%s = %s" % (key, value)
            props.append(data)
        outFile.write("# ZENDMD %s\n" % "; ".join(props))


def main():
    BatchDeviceDumper().run()
