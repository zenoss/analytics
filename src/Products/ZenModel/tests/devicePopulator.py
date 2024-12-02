#! /usr/bin/env python 
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''devicePopulator

Populates the zenoss database with test devices.

'''

import transaction
from Products.ZenUtils.ZCmdBase import ZCmdBase


class DevicePopulator(ZCmdBase):


    def __init__(self):
        ZCmdBase.__init__(self)


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--commit',
                               dest="commit",
                               action='store_true',
                               default=False,
                               help="Commit changes to the database")
        self.parser.add_option('--name',
                               dest="name",
                               default='Test',
                               help="Root name for test devices, etc.")
        self.parser.add_option('--repeat',
                               dest="repeat",
                               type="int",
                               default=1,
                               help="Number of devices to create")
        self.parser.add_option('--everywhere',
                               dest="everywhere",
                               default=False,
                               action='store_true',
                               help="Create device(s) for every existing"
                                    " event class")
        self.parser.add_option('--onlyleafclasses',
                               dest="onlyleafclasses",
                               default=False,
                               action='store_true',
                               help="If --everywhere then only create devices"
                                    " on leaf nodes of the device class tree.")


    def getDeviceClass(self, name='Test Device Class', parent=None):
        ''' Return the test device class, creating it if necessary
        '''
        if not parent:
            parent = self.dmd.Devices
        return self.getOrAddOrganizer(name, parent)         

    
    def getSystem(self, name='Test System', parent=None):
        ''' Return the test system, creating it if necessary
        '''
        if not parent:
            parent = self.dmd.Systems
        return self.getOrAddOrganizer(name, parent)         


    def getGroup(self, name='Test Group', parent=None):
        ''' Return the test group, creating it if necessary
        '''
        if not parent:
            parent = self.dmd.Groups
        return self.getOrAddOrganizer(name, parent)         

     
    def getLocation(self, name='Test Location', parent=None):
        ''' Return the test location, creating it if necessary
        '''
        if not parent:
            parent = self.dmd.Locations
        return self.getOrAddOrganizer(name, parent)         

     
    def getOrAddOrganizer(self, name, parent):
        ''' Return or create a suborganizer of the given class, parent, name
        '''
        if name not in parent.childIds():
            parent.manage_addOrganizer(name)
        for subOrg in parent.children():
            if subOrg.getId() == name:
                return subOrg
        return None            

    
    def getOrAddManufacturer(self, device):
        ''' Return name of the manufacturer
        '''
        name = '%s Manufacturer' % self.options.name
        device.addManufacturer(newHWManufacturerName=name)
        return name
                        
    
    def getOrAddProduct(self, device):
        name = '%s Product' % self.options.name
        device.setHWProduct(newHWProductName=name)
        return name


    def buildTestDevice(self, name, dClass=None):
        if not dClass:
            dClass = self.getDeviceClass('%s class' % name)
        device = dClass.createInstance('%s device' % name)
        device.manage_editDevice(
                locationPath = self.getLocation('%s location' % name
                                                ).getOrganizerName(),
                groupPaths = [self.getGroup('%s group 1' % name
                                                ).getOrganizerName(),
                                self.getGroup('%s group 2' % name
                                                ).getOrganizerName()],
                systemPaths = [self.getSystem('%s system 1' % name
                                                ).getOrganizerName(),
                                self.getSystem('%s system 2' % name
                                                ).getOrganizerName()],
                hwManufacturer=self.getOrAddManufacturer(device),
                hwProductName=self.getOrAddProduct(device)
                )
        return device

    def buildDevicesEverywhere(self):
        ''' Create a test device in each event class
        '''
        def deviceNameGenerator(root='Device'):
            count = 1
            while True:
                yield '%s %s' % (root, count)
                count += 1

        nameGen = deviceNameGenerator(root=self.options.name)
        for org in self.dmd.Devices.getSubOrganizers():
            if not self.options.onlyleafclasses or not org.children():
                for i in range(self.options.repeat):
                    self.buildTestDevice(nameGen.next(), dClass=org)
        if self.options.commit:
            transaction.commit()
        else:
            transaction.abort()

    def main(self):
        for i in range(self.options.repeat):
            device = self.buildTestDevice('%s %s' % (self.options.name, i))
        if self.options.commit:
            transaction.commit()
        else:
            transaction.abort()

if __name__ == '__main__':
    pop = DevicePopulator()
    if pop.options.everywhere:
        pop.buildDevicesEverywhere()
    else:
        pop.main()
