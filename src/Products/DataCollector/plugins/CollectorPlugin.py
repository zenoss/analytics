##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Collector classes for the different methods of collecting data from devices.
"""

import struct

from pprint import pformat

import Products.ZenUtils.IpUtil as iputil
import Products.DataCollector.CommandPluginUtils as utils

from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from Products.ZenHub.services.PerformanceConfig import ATTRIBUTES
from Products.ZenUtils.Utils import prepId as globalPrepId


class CollectorPlugin(object):
    """
    Base class for Collector plugins
    """

    order = 100
    transport = ""
    maptype = ""
    relname = ""
    compname = ""
    modname = ""
    classname = ""
    weight = 1
    deviceProperties = (
        "id",
        "manageIp",
        "_snmpLastCollection",
        "_snmpStatus",
        "zCollectorClientTimeout",
    )

    def isip(self, ip):
        return iputil.isip(ip)

    def prepId(self, id, subchar="_"):
        """Return the global prep ID"""
        # TODO: document what this means and why we care
        return globalPrepId(id, subchar)

    def maskToBits(self, mask):
        """Return the netmask as number of bits 255.255.255.0 -> 24."""
        return iputil.maskToBits(mask)

    def hexToBits(self, mask):
        """Return the netmask as number of bits 0xffffff00 -> 24."""
        return iputil.hexToBits(mask)

    def objectMap(self, data={}):
        """Create an object map from the data"""
        om = ObjectMap(data)
        om.compname = self.compname
        om.modname = self.modname
        om.classname = self.classname
        return om

    def relMap(self):
        """Create a relationship map."""
        relmap = RelationshipMap()
        relmap.relname = self.relname
        relmap.compname = self.compname
        return relmap

    def condition(self, device, log):
        """Test to see if this CollectorPlugin is valid for this device."""
        return True

    def preprocess(self, results, log):
        """
        Perform any plugin house keeping before calling user func process.
        """
        return results

    def process(self, device, results, log):
        """Process the data this plugin collects."""
        raise NotImplementedError

    def name(self):
        """Return the name of this plugin.
        Removes any paths before the plugins directory
        """
        return self.__class__.__module__.split("plugins.").pop()

    def checkColumns(self, row, columns, log):
        """Check that all columns came back,
        this should be everywhere #1539 -EAD
        """
        rescols = set(row.keys())
        cols = set(columns.values())
        if not rescols >= cols:
            log.error(
                "result missing columns: '%s'",
                ",".join(cols.difference(rescols)),
            )
            return False
        return True

    def copyDataToProxy(self, device, proxy):
        """
        For anything monitored indirectly,
        copy it's status to the proxy device.
        """
        for id in self.deviceProperties:
            if device.hasProperty(id, useAcquisition=True):
                value = device.getProperty(id)
            elif hasattr(device, id):
                value = getattr(device, id)
                if callable(value):
                    value = value()
            else:
                continue
            setattr(proxy, id, value)
        proxy._snmpStatus = device.getSnmpStatus()

    def asdate(self, val):
        """Convert a byte string to the date string 'YYYY/MM/DD HH:MM:SS'"""
        datear = (1968, 1, 8, 10, 15, 0)
        try:
            datear = struct.unpack("!h5B", val[0:7])
        except Exception:
            pass
        if datear[0] == 0:
            datear = (1968, 1, 8, 10, 15, 0)
        return "%d/%02d/%02d %02d:%02d:%02d" % datear[:6]


class PythonPlugin(CollectorPlugin):
    """
    A PythonPlugin defines a native Python collection routine and a parsing
    method to turn the returned data structure into a datamap. A valid
    PythonPlugin must implement the collect and process methods.
    """

    transport = "python"

    def collect(self, device, log):
        """Dummy collector to be implemented by the actual collector."""
        pass


class CommandPlugin(CollectorPlugin):
    """
    A CommandPlugin defines a command to be run on a remote device and
    a parsing methos to turn the commands output into a datamap.  A valid
    CommandPlugin must have class variable "command" defined and must implement
    the methods process and condition.
    """

    transport = "command"
    command = ""
    deviceProperties = CollectorPlugin.deviceProperties + (
        "zCommandPort",
        "zCommandProtocol",
        "zCommandUsername",
        "zCommandPassword",
        "zCommandLoginTries",
        "zCommandLoginTimeout",
        "zCommandCommandTimeout",
        "zKeyPath",
        "zCommandSearchPath",
        "zCommandExistanceTest",
        "zSshConcurrentSessions",
        "zTelnetLoginRegex",
        "zTelnetPasswordRegex",
        "zTelnetSuccessRegexList",
        "zTelnetTermLength",
        "zTelnetEnable",
        "zTelnetEnableRegex",
        "zEnablePassword",
    )

    def preprocess(self, results, log):
        """Strip off the command if it is echoed back in the stream."""

        if results.lstrip().startswith(self.command):
            results = results.output.lstrip()[len(self.command) :]
        return results


class LinuxCommandPlugin(CommandPlugin):
    """
    A command plugin for linux that is used by devices in Server/Cmd and
    Server/SSH/Linux.
    """

    def condition(self, device, log):
        """
        If the device resides under the Server/Cmd device class, then only run
        this plugin if uname has been previously modeled as "Linux". Otherwise
        always run this plugin.
        """
        path = device.deviceClass().getPrimaryUrlPath()

        if path.startswith("/zport/dmd/Devices/Server/Cmd"):
            result = device.os.uname == "Linux"
        else:
            result = True

        return result


class SoftwareCommandPlugin(CommandPlugin):
    """
    A CommandPlugin that collects information about installed software.
    """

    def __init__(self, parseResultsFunc):
        self.parseResultsFunc = parseResultsFunc

    def process(self, device, results, log):
        """
        Return a ReltionshipMap with the installed software.
        """
        log.info("Collecting installed software for host %s.", device.id)
        softwareDicts = self.parseResultsFunc(results)

        log.debug(
            "First three software dictionaries:\n%s",
            pformat(softwareDicts[:3]),
        )

        return utils.createSoftwareRelationshipMap(softwareDicts)


class SnmpPlugin(CollectorPlugin):
    """
    An SnmpPlugin defines a mapping from SNMP MIB values to a datamap.
    A valid SnmpPlugin must define 'collectoids' (a list of OIDs to be
    collected) and the process() method which converts the OID data to a
    datamap.  It can override the condition() method if nessesary.
    """

    transport = "snmp"
    conditionOids = []
    snmpGetMap = None
    snmpGetTableMaps = []
    deviceProperties = (
        CollectorPlugin.deviceProperties
        + ATTRIBUTES
        + (
            "snmpOid",
            "zMaxOIDPerRequest",
        )
    )

    def condition(self, device, log):
        """Default SNMP condition is true but it can be overridden.
        Default test is to check for condition OIDs.
        """
        return True

    def preprocess(self, results, log):
        """Gather raw data for process() to process"""
        getdata, tabledatas = results
        if self.snmpGetMap:
            getdata = self.snmpGetMap.mapdata(getdata)
        tdata = {}
        for tmap, tabledata in tabledatas.items():
            tdata[tmap.name] = tmap.mapdata(tabledata)
        return (getdata, tdata)

    def asmac(self, val):
        """Convert a byte string to a MAC address string."""
        mac = []
        for char in val:
            tmp = struct.unpack("B", char)[0]
            tmp = str(hex(tmp))[2:]
            if len(tmp) == 1:
                tmp = "0" + tmp
            mac.append(tmp)
        return ":".join(mac).upper()

    def asip(self, val):
        """Convert a byte string to an IP address string."""
        return ".".join(map(str, struct.unpack("!4B", val)))


class GetMap(object):
    """
    Map OIDs found from an SNMP get operation to their names.
    """

    def __init__(self, oidmap):
        """Initializer"""
        self.oidmap = oidmap

    def getoids(self):
        """Return the OID names"""
        return self.oidmap.keys()

    def mapdata(self, results):
        """Create a dictionary from our SNMP get results"""
        data = {}
        for oid, value in results.items():
            data[self.oidmap[oid]] = value
        return data


class GetTableMap(object):
    """
    Map SNMP table OIDs to their column names.
    """

    def __init__(self, name, tableoid, colmap):
        """Initializer"""
        self.name = name
        self.tableoid = tableoid
        self.colmap = colmap
        self._oids = {}
        for numb, name in self.colmap.items():
            self._oids[self.tableoid + numb] = name

    def getoids(self):
        """Return the raw OIDs used to get this table."""
        return self._oids.keys()

    def mapdata(self, results):
        """Map data from the format returned by SNMP table get (which is
        column-based) to a row-based format. eg data[rowidx][colname]
        """
        data = {}
        for col, rows in results.items():
            name = self._oids[col]
            clen = len(col) + 1
            for roid, value in rows.items():
                ridx = roid[clen:]
                data.setdefault(ridx, {})
                data[ridx][name] = value
        return data
