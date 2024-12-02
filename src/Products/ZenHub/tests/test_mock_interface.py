from unittest import TestCase
from mock_interface import create_interface_mock

from mock import Mock, create_autospec
from zope.component.interfaces import Interface
from zope.interface import Attribute
from zope.interface.verify import verifyObject


class MockInterfaceTest(TestCase):
    class ITestInterface(Interface):
        atrib = Attribute("Interface requires an attribute")

        def some_method(self):
            """Interface requires some method"""

    def setUp(self):
        """Create a Mock object that implements an Interface"""
        self.ITestInterfaceMock = create_interface_mock(self.ITestInterface)
        self.m_test_iface = self.ITestInterfaceMock()

    def test_interface_is_implemented_by_mock(self):
        """the mocked object implements the Interface
        the class implements the interface
        """
        verifyObject(self.ITestInterface, self.m_test_iface())
        self.assertTrue(
            self.ITestInterface.implementedBy(self.ITestInterfaceMock)
        )
        # the object provides the interface
        self.assertTrue(self.ITestInterface.providedBy(self.m_test_iface()))

    def test_interface_is_implemented_by_mock_with_spec_set(self):
        """You can use spec_set, which will raise an error if you call
        a method not required by the interface
        however, attributes defined like `a = Attribute('description')`
        will not be included
        """
        m_test_iface = self.ITestInterfaceMock(spec_set=True)
        instance = m_test_iface()

        verifyObject(self.ITestInterface, instance)
        # the class implements the interface
        self.assertTrue(
            self.ITestInterface.implementedBy(self.ITestInterfaceMock)
        )
        # the object provides the interface
        self.assertTrue(self.ITestInterface.providedBy(instance))

        # Can Access attributes defined by the interface
        instance.some_method()
        self.assertTrue(hasattr(instance, "atrib"))
        # cannot access attributes that are not defined
        with self.assertRaises(AttributeError):
            instance.undefined_method()
        with self.assertRaises(AttributeError):
            instance.undefined_atrib

    def test_has_required_properties(self):
        # It has attributes required by the Interface
        self.assertTrue(hasattr(self.m_test_iface, "atrib"))
        # It does not have attributes which are not required by the Interface
        self.assertFalse(hasattr(self.m_test_iface, "unspecified_attribute"))

    def test_assign_attribute_values(self):
        """You may assign values to required attributes
        and add new attributes
        """
        self.m_test_iface.atrib = "i am atrib"
        self.assertEqual(self.m_test_iface.atrib, "i am atrib")
        self.m_test_iface.not_atrib = "i am not atrib"
        self.assertEqual(self.m_test_iface.not_atrib, "i am not atrib")

    def test_set_method_return_values(self):
        """You can set return values for required methods,
        but not methods which were not defined in the Interface
        """
        self.m_test_iface.some_method.return_value = True
        self.assertIs(self.m_test_iface.some_method(), True)

        with self.assertRaises(AttributeError):
            self.m_test_iface.undefined_method.return_value = True

    def test_add_new_methods(self):
        """You may add new methods explicitly"""
        self.m_test_iface.new_method = lambda x: x
        self.assertEqual(self.m_test_iface.new_method("hi"), "hi")
        # or using a mock
        self.m_test_iface.new_method = Mock(return_value="a string")
        self.assertEqual(self.m_test_iface.new_method(), "a string")

        # with a proper spec
        def specific_function(a, b):
            return a + b

        self.m_test_iface.new_method = create_autospec(
            specific_function, return_value=5
        )
        self.assertEqual(self.m_test_iface.new_method(1, 2), 5)

        with self.assertRaises(TypeError):
            # takes exactly 2 arguments (1 given))
            self.m_test_iface.new_method(1)
