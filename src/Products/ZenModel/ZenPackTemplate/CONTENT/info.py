# This file is the conventional place for "Info" adapters. Info adapters are
# a crucial part of the Zenoss API and therefore the web interface for any
# custom classes delivered by your ZenPack. Examples of custom classes that
# will almost certainly need info adapters include datasources, custom device
# classes and custom device component classes.

# Mappings of interfaces (interfaces.py) to concrete classes and the factory
# (these info adapter classes) used to create info objects for them are managed
# in the configure.zcml file.

from zope.component import adapts
from zope.interface import implements

from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo
from Products.Zuul.infos.template import RRDDataSourceInfo

from ZenPacks.NAMESPACE.PACKNAME.ExampleComponent import ExampleComponent
from ZenPacks.NAMESPACE.PACKNAME.interfaces \
    import IExampleDataSourceInfo, IExampleComponentInfo


class ExampleDataSourceInfo(RRDDataSourceInfo):
    """
    Defines API access for this datasource.
    """

    implements(IExampleDataSourceInfo)

    # ProxyProperty is a shortcut to mean that you want the getter/setter for
    # this property to go directly to properties of the same name on the
    # datasource class (ExampleDataSource).
    exampleProperty = ProxyProperty('exampleProperty')

    # RRDDataSourceInfo classes can create a property called "testable" that
    # controls whether the datasource dialog in the web interface allows the
    # user to test it. By default this property is set to True unless you
    # override it as is done below.

    @property
    def testable(self):
        """
        This datasource is not testable.
        """
        return False


class ExampleComponentInfo(ComponentInfo):
    implements(IExampleComponentInfo)
    adapts(ExampleComponent)

    attributeOne = ProxyProperty("attributeOne")
    attributeTwo = ProxyProperty("attributeTwo")
