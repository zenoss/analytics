##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenModel.TemperatureSensor import TemperatureSensor

from ZenModelBaseTest import ZenModelBaseTest


class TestTemperatureSensor(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestTemperatureSensor, self).afterSetUp()
        self.dev = self.dmd.Devices.createInstance('testdev')
        tmpo = TemperatureSensor('ts1')
        self.dev.hw.temperaturesensors._setObject('ts1',tmpo)
        self.ts = self.dev.hw.temperaturesensors()[0]

    def testNans(self):
        oldfunc = self.ts.cacheRRDValue
        def cacheRRDValue(self, string, defualt=None):
            return float('nan')
        self.ts.cacheRRDValue = cacheRRDValue
        self.assertEquals(self.ts.temperatureCelsius(), None)
        self.assertEquals(self.ts.temperatureFahrenheit(), None)
        self.ts.cacheRRDValue = oldfunc

    def testNones(self):
        self.assertEquals(self.ts.temperatureCelsius(), None)
        self.assertEquals(self.ts.temperatureFahrenheit(), None)

    def testHaveValue(self):
        oldfunc = self.ts.cacheRRDValue
        def cacheRRDValue(self, string, defualt=None):
            return 75.3
        self.ts.cacheRRDValue = cacheRRDValue
        self.assertEquals(self.ts.temperatureCelsius(), 75)
        self.assertEquals(self.ts.temperatureFahrenheit(), 167)
        self.ts.cacheRRDValue = oldfunc


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestTemperatureSensor))
    return suite

if __name__=="__main__":
    framework()
