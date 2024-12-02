from zope.component import adapts
from zope.interface import implements

from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

from ZenPacks.zenoss.Impact.impactd import Trigger
from ZenPacks.zenoss.Impact.stated.interfaces import IStateProvider
from ZenPacks.zenoss.Impact.impactd.relations import ImpactEdge
from ZenPacks.zenoss.Impact.impactd.interfaces \
    import IRelationshipDataProvider, INodeTriggers

from .ExampleDevice import ExampleDevice
from .ExampleComponent import ExampleComponent


def getRedundancyTriggers(guid, format):
    """
    Helper method for generating a good general redunancy set of triggers.
    """

    availability = 'AVAILABILITY'
    percent = 'policyPercentageTrigger'
    threshold = 'policyThresholdTrigger'

    return (
        Trigger(guid, format % 'DOWN', percent, availability, dict(
            state='DOWN', dependentState='DOWN', threshold='100',
        )),
        Trigger(guid, format % 'DEGRADED', threshold, availability, dict(
            state='DEGRADED', dependentState='DEGRADED', threshold='1',
        )),
        Trigger(guid, format % 'ATRISK_1', threshold, availability, dict(
            state='ATRISK', dependentState='DOWN', threshold='1',
        )),
        Trigger(guid, format % 'ATRISK_2', threshold, availability, dict(
            state='ATRISK', dependentState='ATRISK', threshold='1',
        )),
    )


class ExampleDeviceRelationsProvider(object):
    implements(IRelationshipDataProvider)
    adapts(ExampleDevice)

    relationship_provider = "ExampleImpact"

    def __init__(self, adapted):
        self._object = adapted

    def belongsInImpactGraph(self):
        return True

    def getEdges(self):
        """
        An ExampleDevice impacts all of its ExampleComponents.
        """
        guid = IGlobalIdentifier(self._object).getGUID()

        for exampleComponent in self._object.exampleComponents():
            c_guid = IGlobalIdentifier(exampleComponent).getGUID()
            yield ImpactEdge(guid, c_guid, self.relationship_provider)


class ExampleComponentRelationsProvider(object):
    implements(IRelationshipDataProvider)
    adapts(ExampleComponent)

    relationship_provider = "ExampleImpact"

    def __init__(self, adapted):
        self._object = adapted

    def belongsInImpactGraph(self):
        return True

    def getEdges(self):
        """
        An ExampleComponent is impacted by its ExampleDevice.
        """
        guid = IGlobalIdentifier(self._object).getGUID()

        d_guid = IGlobalIdentifier(self._object.exampleDevice())
        yield ImpactEdge(d_guid, guid, self.relationship_provider)


class ExampleComponentStateProvider(object):
    implements(IStateProvider)

    def __init__(self, adapted):
        self._object = adapted

    @property
    def eventClasses(self):
        return ('/Status/',)

    @property
    def excludeClasses(self):
        return None

    @property
    def eventHandlerType(self):
        return "WORST"

    @property
    def stateType(self):
        return 'AVAILABILITY'

    def calcState(self, events):
        status = None
        if self._object.attributeOne < 1:
            return 'DOWN'
        else:
            return 'UP'

        cause = None
        if status == 'DOWN' and events:
            cause = events[0]

        return status, cause


class ExampleComponentTriggers(object):
    implements(INodeTriggers)

    def __init__(self, adapted):
        self._object = adapted

    def get_triggers(self):
        return getRedundancyTriggers(
            IGlobalIdentifier(self._object).getGUID(),
            'DEFAULT_EXAMPLECOMPONENT_TRIGGER_ID_%s',
        )
