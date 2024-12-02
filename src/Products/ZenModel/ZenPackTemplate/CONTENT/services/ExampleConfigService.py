"""
ExampleConfigService
ZenHub service for providing configuration to the zenexample collector daemon.

    This provides the daemon with a dictionary of datapoints for every device.
"""

import logging
log = logging.getLogger('zen.example')

import Globals
from Products.ZenCollector.services.config import CollectorConfigService


# Your daemon configuration service should almost certainly subclass
# CollectorConfigService to make it as easy as possible for you to implement.
class ExampleConfigService(CollectorConfigService):
    """
    ZenHub service for the zenexample collector daemon.
    """

    # When the collector daemon requests a list of devices to poll from ZenHub
    # your service can filter the devices that are returned by implementing
    # this _filterDevice method. If _filterDevice returns True for a device,
    # it will be returned to the collector. If _filterDevice returns False, the
    # collector daemon won't collect from it.
    def _filterDevice(self, device):
        # First use standard filtering.
        filter = CollectorConfigService._filterDevice(self, device)

        # If the standard filtering logic said the device shouldn't be filtered
        # we can setup some other contraint.
        if filter:
            # We only monitor devices that start with "z".
            return device.id.startswith('z')

        return filter

    # The _createDeviceProxy method allows you to build up the DeviceProxy
    # object that will be sent to the collector daemon. Whatever is returned
    # from this method will be sent as the device's representation to the
    # collector daemon. Use serializable types. DeviceProxy works, as do any
    # simple Python types.
    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)

        proxy.datapoints = []
        proxy.thresholds = []

        perfServer = device.getPerformanceServer()

        self._getDataPoints(proxy, device, device.id, None, perfServer)
        proxy.thresholds += device.getThresholdInstances('Example Protocol')

        for component in device.getMonitoredComponents():
            self._getDataPoints(
                proxy, component, component.device().id, component.id,
                perfServer)

            proxy.thresholds += component.getThresholdInstances(
                'Example Protocol')

        return proxy

    # This is not a method you must implement. It is used by the custom
    # _createDeviceProxy method above.
    def _getDataPoints(
            self, proxy, deviceOrComponent, deviceId, componentId, perfServer
            ):
        for template in deviceOrComponent.getRRDTemplates():
            dataSources = [ds for ds
                           in template.getRRDDataSources('Example Protocol')
                           if ds.enabled]

            for ds in dataSources:
                for dp in ds.datapoints():
                    path = '/'.join((deviceOrComponent.rrdPath(), dp.name()))
                    dpInfo = dict(
                        devId=deviceId,
                        compId=componentId,
                        dsId=ds.id,
                        dpId=dp.id,
                        path=path,
                        rrdType=dp.rrdtype,
                        rrdCmd=dp.getRRDCreateCommand(perfServer),
                        minv=dp.rrdmin,
                        maxv=dp.rrdmax,
                        exampleProperty=ds.exampleProperty,
                        )

                    if componentId:
                        dpInfo['componentDn'] = getattr(
                            deviceOrComponent, 'dn', None)

                    proxy.datapoints.append(dpInfo)


# For diagnostic purposes, allow the user to show the results of the
# proxy creation.
# Run this service as a script to see which devices will be sent to the daemon.
# Add the --device=name flag to see the detailed contents of the proxy that
# will be sent to the daemon
#
if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(ExampleConfigService)
    def printer(config):
        # Fill this out
        print config.datapoints
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()

