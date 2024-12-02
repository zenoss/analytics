import types
from mock import Mock
from zope.interface import classImplements


def create_interface_mock(interface_class):
    """given a Zope Interface class
    return a Mock sub class
    that implements the given Zope interface class.

    Mock objects created from this InterfaceMock will
    have Attributes and Methods required in the Interface
    will not have Attributes or Methods that are not specified
    """

    # the init method, automatically spec the interface methods
    def init(self, *args, **kwargs):
        Mock.__init__(self, *args, spec=interface_class.names(), **kwargs)

    # subclass named '<interface class name>Mock'
    name = interface_class.__name__ + "Mock"

    # create the class object and provide the init method
    klass = types.TypeType(name, (Mock,), {"__init__": init})

    # the new class should implement the interface
    classImplements(klass, interface_class)

    return klass
