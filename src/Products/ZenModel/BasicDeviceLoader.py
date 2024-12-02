##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""BasicDeviceLoader.py

BasicDeviceLoader.py populates the dmd with devices from a file.  The input file
only needs to have a list of machines.  It uses the Classifier system
to figure out where in the DeviceClass a new device should be created.
If no location is found it will use a specified default path or put
the device in the top level of the DevicesClass tree.
"""

from logging import info

from Products.ZenModel.Exceptions import *


class BasicDeviceLoader:
    '''Load a machine'''

    def loadDevice(self, deviceName, devicePath="", systemPath="",
                manufacturer="", model="", groupPath="",
                locationPath="", rack="",
                perfMonitorName="localhost",
                snmpCommunity="", snmpPort=None,
                loginName="", loginPassword=""):
        """load a device into the database"""
        info("adding device %s" % deviceName)
        device = self.getDevice(deviceName, devicePath, snmpCommunity, snmpPort,
                            loginName, loginPassword)

        if manufacturer and model:
            info("setting manufacturer to %s model to %s", manufacturer, model)
            device.setModel(manufacturer, model)

        if not locationPath: locationPath = self.getLocationPath()
        if locationPath:
            if rack:
                locationPath += "/%s" % rack
                info("setting rack location to %s" % locationPath)
                device.setRackLocation(locationPath)
            else:
                info("setting location to %s" % locationPath)
                device.setLocation(locationPath)

        if not groupPath: groupPath = self.getGroupPath()
        if groupPath:
            info("setting group %s" % groupPath)
            device.setGroups(groupPath)

        if not systemPath: systemPath = self.getSystemPath()
        if systemPath:
            info("setting system %s" % systemPath)
            device.setSystems(systemPath)

        if not perfMonitorName:
            perfMonitorName = self.getPerformanceMonitorName()
        info("setting performance monitor to %s" % perfMonitorName)
        device.setPerformanceMonitor(perfMonitorName)
       
        return device

    
    def getDevice(self, deviceName, devicePath,
                snmpCommunity, snmpPort, loginName, loginPassword):
        """get a device if devicePath is None try classifier"""
        self.classificationEntry = None
        dev = self.getDmdRoot("Devices").findDevice(deviceName)
        if dev:
            raise DeviceExistsError("Device %s already exists" %
                                    deviceName, dev)
        if not devicePath:
            self.classificationEntry = \
                self.getDmdRoot("Devices").ZenClassifier.classifyDevice(
                                        deviceName,
                                        snmpCommunity, snmpPort,
                                        loginName, loginPassword)
            if not self.classificationEntry:
                raise NotImplemented(
                    "Classifier failed to classify device %s" % deviceName)
            devicePath = self.classificationEntry.getDeviceClassPath

        deviceClass = self.getDmdRoot("Devices").getOrganizer(devicePath)
        if not deviceClass:
            raise PathNotFoundError(
                "Path to device %s is not valid" % deviceName)
        return deviceClass.createInstance(deviceName)


    def getLocationPath(self):
        """get the location path for an object"""
        pass


    def getGroupPath(self):
        """override if you need to derive the group name from something else"""
        pass


    def getSystemPath(self):
        """override if you need to derive the system name from something else"""
        pass
       

    def getPerformanceMonitorName(self):
        """return the performance monitor name, default is localhost"""
        return "localhost"


if __name__ == "__main__":
    loader = BasicDeviceLoader()
    loader.loadDatabase()
    print "Database Load is finished!"
