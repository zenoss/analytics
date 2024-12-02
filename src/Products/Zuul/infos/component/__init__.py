##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import implements
from zope.component import adapts

from Products.Zuul.interfaces import IComponentInfo, IComponent
from Products.Zuul.infos import InfoBase, ProxyProperty, HasEventsInfoMixin, LockableMixin, BulkMetricLoadMixin
from Products.Zuul.form.builder import FormBuilder
from Products.Zuul.decorators import info
from Products.Zuul.utils import safe_hasattr as hasattr


class ComponentInfo(InfoBase, HasEventsInfoMixin, LockableMixin, BulkMetricLoadMixin):
    implements(IComponentInfo)
    adapts(IComponent)

    @property
    @info
    def device(self):
        return self._object.device()

    @property
    def deviceName(self):
        return self._object.device().titleOrId()

    @property
    def usesMonitorAttribute(self):
        return True

    monitor = ProxyProperty('monitor')

    @property
    def monitored(self):
        return self._object.monitored()

    @property
    def productionState(self):
        return self._object.getProductionState()

    @property
    def status(self):
        statusCode = self._object.getStatus()
        # the result from convertStatus will be a status string
        # or the number of down event
        value =  self._object.convertStatus(statusCode)
        if isinstance(value, str):
            return value

        if value > 0:
            return "Down"
        else:
            return "Up"

    pingStatus = status

    @property
    def icon(self):
        return self._object.getIconPath()


class ComponentFormBuilder(FormBuilder):
    def render(self, fieldsets=True):
        ob = self.context._object

        # find out if we can edit this form
        readOnly = True
        if hasattr(ob, 'isUserCreated'):
            readOnly = not ob.isUserCreated()

        # construct the form
        form = super(ComponentFormBuilder, self).render(fieldsets,
                                                        readOnly=readOnly)
        form['userCanModify'] = not readOnly or self.hasAlwaysEditableField
        return form


def ServiceMonitor():
    """
    Closure for the 'monitor' property of ip/win services
    """
    def getMonitor(self):
        return getattr(self._object, 'monitor')

    def setMonitor(self, monitor):
        self._object.setAqProperty('zMonitor', monitor, 'boolean')
        self._object.monitor = monitor
        self._object.index_object()
        return

    return property(getMonitor, setMonitor)
