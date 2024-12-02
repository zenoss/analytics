##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.ObjectMap import ObjectMap
from Products.DataCollector.RelationshipMap import RelationshipMap
from Products.ZenUtils.Utils import prepId as globalPrepId


class CommandParser(object):
    """
    CommandParser parses the output of a command to return a datamap
    """

    # Subclasses must fill this in with appropriate command
    command = ""

    def prepId(self, id, subchar="_"):
        return globalPrepId(id, subchar)

    def newObjectMap(self, className=None):
        return ObjectMap(className)

    def newRelationshipMap(self, relationshipName, componentName=""):
        return RelationshipMap(relationshipName, componentName)

    def condition(self, device, snmpsess):
        """does device meet the proper conditions for this collector to run"""
        return 0

    def parse(self, results, log):
        """collect snmp information from this device
        device is the a Device class (or subclass) object
        snmpsess is a valid instance of SnmpSession to connect
        to this device"""
        pass

    def description(self):
        """return a description of what this map does"""
        pass
