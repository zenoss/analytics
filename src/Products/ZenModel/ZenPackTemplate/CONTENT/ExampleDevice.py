from Products.ZenModel.Device import Device
from Products.ZenRelations.RelSchema import ToManyCont, ToOne


class ExampleDevice(Device):
    """
    Example device subclass. In this case the reason for creating a subclass of
    device is to add a new type of relation. We want many "ExampleComponent"
    components to be associated with each of these devices.

    If you set the zPythonClass of a device class to
    ZenPacks.NAMESPACE.PACKNAME.ExampleDevice, any devices created or moved
    into that device class will become this class and be able to contain
    ExampleComponents.
    """

    meta_type = portal_type = 'ExampleDevice'

    # This is where we extend the standard relationships of a device to add
    # our "exampleComponents" relationship that must be filled with components
    # of our custom "ExampleComponent" class.
    _relations = Device._relations + (
        ('exampleComponents', ToManyCont(ToOne,
            'ZenPacks.NAMESPACE.PACKNAME.ExampleComponent.ExampleComponent',
            'exampleDevice',
            ),
        ),
    )
