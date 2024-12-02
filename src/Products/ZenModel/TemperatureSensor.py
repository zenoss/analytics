##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""TemperatureSensor

TemperatureSensor is an abstraction of a temperature sensor or probe.

"""

from math import isnan

from AccessControl.class_init import InitializeClass

from Products.ZenRelations.RelSchema import ToOne, ToManyCont

from HWComponent import HWComponent



class TemperatureSensor(HWComponent):

    portal_type = meta_type = 'TemperatureSensor'

    state = "unknown"

    _properties = HWComponent._properties + (
        {'id':'state', 'type':'string', 'mode':'w'},
    )

    _relations = HWComponent._relations + (
        ("hw", ToOne(
            ToManyCont, "Products.ZenModel.DeviceHW", "temperaturesensors")),
        )

    
    factory_type_information = ( 
        { 
            'id'             : 'TemperatureSensor',
            'meta_type'      : 'TemperatureSensor',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'TemperatureSensor_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addTemperatureSensor',
            'immediate_view' : 'viewTemperatureSensor',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewTemperatureSensor'
                , 'permissions'   : ('View',)
                },
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },
            )
          },
        )


    def temperatureCelsius(self, default=None):
        """
        Return the current temperature in degrees celsius
        """
        tempC = self.cacheRRDValue('temperature_celsius', default)
        if tempC is None or isnan(tempC):
            tempF = self.cacheRRDValue('temperature_fahrenheit', default)
            if tempF is not None and not isnan(tempF):
                tempC = (tempF - 32) / 9.0 * 5
        if tempC is not None and not isnan(tempC):
            return long(tempC)
        return None
    temperature = temperatureCelsius

    def temperatureFahrenheit(self, default=None):
        """
        Return the current temperature in degrees fahrenheit
        """
        tempC = self.temperatureCelsius(default)
        if tempC is not None and not isnan(tempC):
            tempF = tempC * 9 / 5 + 32.0
            return long(tempF)
        return None

    def temperatureCelsiusString(self):
        """
        Return the current temperature in degrees celsius as a string
        """
        tempC = self.temperature()
        return tempC is None and "unknown" or "%dC" % (tempC,)
    temperatureString = temperatureCelsiusString


    def temperatureFahrenheitString(self):
        """
        Return the current temperature in degrees fahrenheit as a string
        """
        tempF = self.temperatureFahrenheit()
        return tempF is None and "unknown" or "%dF" % (tempF,)


InitializeClass(TemperatureSensor)
