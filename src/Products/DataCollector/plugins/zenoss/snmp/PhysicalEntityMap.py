##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import (
    GetTableMap,
    SnmpPlugin,
)
from Products.DataCollector.plugins.DataMaps import MultiArgs


class Card(object):

    _CARDS = set()

    @classmethod
    def startCollection(cls):
        cls._CARDS = set()

    @classmethod
    def getAllCards(cls):
        return tuple(cls._CARDS)

    @property
    def slot(self):
        if not self.parent:
            return str(self._slot)
        for card in Card._CARDS:
            if card.index == self.parent:
                return "%s.%d" % (card.slot, self._slot)
        raise ValueError("No parent exists!")

    def __init__(
        self,
        i,
        index=None,
        descr="",
        parent=0,
        slot=0,
        name="",
        serial="",
        manuf="",
        model="",
    ):
        # Required values
        self.index = index is None and i or index
        self.snmpindex = i

        name = name or descr or str(self.index)

        # Make sure all values are in ascii'ish range (i.e. <128)
        # These should all be ASCII, but some broken devices
        # have '\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
        self.name = "".join(c for c in name if ord(c) < 128)
        self.serial = "".join(c for c in serial if ord(c) < 128)
        self.manuf = "".join(c for c in manuf if ord(c) < 128)
        self.model = "".join(c for c in model if ord(c) < 128)

        # Treat "Unknown" (et al) as empty strings
        self.name = name.lower() != "unknown" and name or ""
        self.serial = serial.lower() != "unknown" and serial or ""
        self.manuf = manuf.lower() != "unknown" and manuf or ""
        self.model = model.lower() != "unknown" and model or ""

        # Optional values
        self.parent = slot >= 0 and parent or None
        self.serial = str(serial).strip()  # get rid of padding
        self.manuf = str(manuf).strip()
        self.model = str(model).strip()
        self._slot = slot >= 0 and slot or 0

        self.__class__._CARDS.add(self)

    def toOM(self, obj):
        om = obj.objectMap()
        om.id = obj.prepId(self.name)
        om.snmpindex = self.snmpindex
        om.slot = self.slot
        om.serialNumber = self.serial
        if self.manuf and self.model:
            om.setProductKey = MultiArgs(self.model, self.manuf)
        return om

    def __lt__(self, other):
        return map(int, self.slot.split(".")) < map(int, other.slot.split("."))

    def __gt__(self, other):
        return map(int, self.slot.split(".")) > map(int, other.slot.split("."))

    def __eq__(self, other):
        return self.slot == other.slot


class PhysicalEntityMap(SnmpPlugin):
    """Map Physical Entities to model.

    Use ENTITY-MIB to determine physical entities as expansion cards.
    """

    maptype = "PhysicalEntityMap"
    modname = "Products.ZenModel.ExpansionCard"
    relname = "cards"
    compname = "hw"
    deviceProperties = SnmpPlugin.deviceProperties + (
        "getHWManufacturerName",
        "getOSManufacturerName",
    )

    columns = {
        ".1": "index",
        ".2": "descr",
        ".4": "parent",
        ".6": "slot",
        ".7": "name",
        ".11": "serial",
        ".12": "manuf",
        ".13": "model",
    }

    snmpGetTableMaps = (
        GetTableMap("peTable", ".1.3.6.1.2.1.47.1.1.1.1", columns),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        petable = tabledata.get("peTable")
        if not petable:
            return

        # Process all of the cards
        Card.startCollection()
        for i, c in petable.iteritems():
            if not c.get("manuf", "").strip():
                c["manuf"] = getattr(
                    device, "getHWManufacturerName", ""
                ) or getattr(device, "getOSManufacturerName", "")
            Card(int(i), **c)

        # Create the maps
        rm = self.relMap()
        for card in sorted(Card.getAllCards()):
            om = card.toOM(self)

            # NOTE: we only save entities that have serial numbers.
            # Failure to do this can result in *very* large databases.
            if om.serialNumber:
                rm.append(om)
        return rm
