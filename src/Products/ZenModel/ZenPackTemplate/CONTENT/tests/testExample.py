# BaseTestCase is a subclass of ZopeTestCase which is ultimately a subclass of
# Python's standard unittest.TestCase. Because of this the following
# documentation on unit testing in Zope and Python are both applicable here.
#
# Python Unit testing framework
# http://docs.python.org/library/unittest.html
#
# Zope Unit Testing
# http://wiki.zope.org/zope2/Testing

from Products.ZenTestCase.BaseTestCase import BaseTestCase


class TestExample(BaseTestCase):
    def afterSetUp(self):
        # You can use the afterSetUp method to create a proper environment for
        # your tests to execute in, or to run common code between the tests.

        #Always call the base class's afterSetUp method first, so things like self.dmd will be available.
        super(TestExample, self).afterSetUp()

        self.device = self.dmd.Devices.createInstance('testDevice')

    def testExampleOne(self):
        self.assertEqual("One", "One")
        self.assertTrue(True)

    def testExampleTwo(self):
        self.assertEqual(self.device.id, "testDevice")
        self.assertFalse(False)

    def beforeTearDown(self):
        # You can use the beforeTearDown method to un-do anything from the afterSetUp method
        # that needs to be restored to its original state. The ZODB transaction for the test
        # case will be rolled back, so this method is not be necessary in most cases.

        self.device = None

        # Always call the base class's beforeTearDown method last, so any changes are rolled back
        # correctly.
        super(TestExample, self).beforeTearDown()

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()

    # Add your BaseTestCase subclasses here to have them executed.
    # suite.addTest(makeSuite(TestExample))

    return suite
