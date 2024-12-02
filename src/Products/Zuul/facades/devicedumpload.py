##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger('zen.devicedumpload.facade')
from StringIO import StringIO

from zope.interface import implements

from Products.Zuul.facades import ZuulFacade
from Products.Zuul import getFacade

from Products.ZenModel.BatchDeviceDumper import BatchDeviceDumper
from Products.ZenModel.BatchDeviceLoader import BatchDeviceLoader

from Products.Zuul.interfaces import IDeviceDumpLoadFacade


class DeviceDumpLoadFacade(ZuulFacade):
    implements(IDeviceDumpLoadFacade)

    def exportDevices(self, deviceClass='/', options={}):
        dumper = BatchDeviceDumper(noopts=True)
        output = StringIO()

        # Set command-line options
        dumper.options.root = deviceClass[1:]
        # Hidden 'option' in BatchDeviceDump
        dumper.options.pruneLSGO = True
        self._setOptions(dumper, options)

        # Export out custom list of properties
        def isPropExportable(propdict):
            id = propdict['id']
            if id == 'zDeviceTemplate':
                return True
            return propdict['islocal']
        dumper.isPropExportable = isPropExportable

        # Don't import out all getter/setter pairs either
        dumper.ignoreSetters += (
            'setLastChange', 'setHWProductKey', 'setHWSerialNumber',
            'setOSProductKey', 'setPriority',
        )

        dumpedCount = dumper.listDeviceTree(output)
        output.seek(0)
        data = output.readlines()
        output.close()

        # Dump the results in sorted order to make file
        # comparisons easier.
        data = '\n'.join(sorted(data))
        return data.lstrip('\n'), dumpedCount

    def importDevices(self, data, options={}):
        loader = BatchDeviceLoader(noopts=True)
        if isinstance(data, str):
            data = data.split('\n')

        # Set command-line options
        loader.options.nomodel = True
        self._setOptions(loader, options)

        devices, unparseable = loader.parseDevices(data)
        stats = loader.processDevices(devices)
        stats['unparseable'] = unparseable
        return stats

    def _setOptions(self, obj, options):
        """
        Apply options to the dumper or loader.
        """
        for name, value in options.items():
            option = getattr(obj.options, name, None)
            if option is not None:
                setattr(obj.options, name, value)

    def listDevices(self, deviceClass='/'):
        try:
            path = self._dmd.Devices.getPrimaryUrlPath()
            root = self._dmd.Devices.unrestrictedTraverse(path + deviceClass)
        except KeyError:
            log.error("%s is not a valid Device Organizer path under %s\n",
                      deviceClass, self._dmd.Devices.getPrimaryUrlPath())
            return []
        devices = tuple(dev.id for dev in root.getSubDevicesGen())
        return sorted(devices)

