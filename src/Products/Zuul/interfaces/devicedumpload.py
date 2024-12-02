##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.Zuul.interfaces import IFacade


class IDeviceDumpLoadFacade(IFacade):

    def exportDevices(deviceClass, options):
        """
        Export out devices in zenbatchload format.

        @parameter deviceClass: location to start exporting devices (default /)
        @type deviceClass: string
        @parameter options: zenbatchdump options
        @type options: dictionary
        @return: zenbatchload format file
        @rtype: string
        """

    def importDevices(data, options):
        """
        Import devices from zenbatchload format string.

        @parameter data: zenbatchload format file
        @type data: string
        @parameter options: zenbatchload options
        @type options: dictionary
        @return: key/value pairs of import statistics
        @rtype: dictionary of category and statistic
        """

    def listDevices(self, deviceClass='/'):
        """
        Convenience method to list devices for comparison with other systems

        @parameter deviceClass: location to start exporting devices (default /)
        @type deviceClass: string
        @return: device names
        @rtype: list
        """

