from zope.component import adapts

from ZenPacks.zenoss.DynamicView import TAG_IMPACTED_BY, TAG_IMPACTS, TAG_ALL
from ZenPacks.zenoss.DynamicView.model.adapters import DeviceComponentRelatable
from ZenPacks.zenoss.DynamicView.model.adapters import BaseRelationsProvider

from ..ExampleDevice import ExampleDevice
from ..ExampleComponent import ExampleComponent


### IRelatable Adapters

class ExampleComponentRelatable(DeviceComponentRelatable):
    adapts(ExampleComponent)

    group = 'Example Components'


### IRelationsProvider Adapters

class ExampleDeviceRelationsProvider(BaseRelationsProvider):
    adapts(ExampleDevice)

    def relations(self, type=TAG_ALL):
        """
        ExampleDevices impact all of their ExampleComponents.
        """
        if type in (TAG_ALL, TAG_IMPACTS):
            for exampleComponent in self._adapted.exampleComponents():
                yield self.constructRelationTo(exampleComponent, TAG_IMPACTS)


class ExampleComponentRelationsProvider(BaseRelationsProvider):
    adapts(ExampleComponent)

    def relations(self, type=TAG_ALL):
        """
        ExampleComponents are impacted by their ExampleDevice.
        """
        if type in (TAG_ALL, TAG_IMPACTED_BY):
            yield self.constructRelationTo(
                self._adapted.exampleDevice(), TAG_IMPACTED_BY)
