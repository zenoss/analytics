##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import implementer

from .interfaces import IEventManagerProxy


@implementer(IEventManagerProxy)
class EventManagerProxy(object):
    """
    An adapter holding several methods useful for interacting with a Zenoss
    event manager.
    """

    def __init__(self, view):
        self.context = view.context
        self.request = view.request

    @property
    def is_history(self):
        # If we're actually loading event console, False
        if "viewEvents" in self.request.getURL():
            return False
        # If we're loading history page or a request from the history page,
        # True, else False
        return (
            "viewHistoryEvents" in self.request.getURL()
            or "viewHistoryEvents" in self.request["HTTP_REFERER"]
        )

    def event_manager(self, forceHistory=False):
        evmgr = getattr(self, "_evmgr", None)
        if not evmgr:
            if forceHistory or self.is_history:
                evmgr = self.context.dmd.ZenEventHistory
            else:
                evmgr = self.context.dmd.ZenEventManager
            self._evmgr = evmgr
        return evmgr

    def _get_device_url(self, devname):
        dev = self.context.dmd.Devices.findDevice(devname)
        if dev:
            return dev.absolute_url_path(), dev.titleOrId()

    def _get_component_url(self, dev, comp):
        comps = self.context.dmd.searchComponents(dev, comp)
        if comps:
            return comps[0].absolute_url_path(), comps[0].titleOrId()

    def _get_eventClass_url(self, evclass):
        return "/zport/dmd/Events" + evclass

    def extract_data_from_zevent(self, zevent, fields):
        data = {}
        for field in fields:
            value = getattr(zevent, field)
            _shortvalue = str(value) or ""
            if field == "prodState":
                value = self.context.dmd.convertProdState(value)
            elif field == "eventState":
                value = self.event_manager().eventStateConversions[value][0]
            elif "Time" in field:
                value = value.rsplit(".")[0].replace("/", "-")
            elif field == "eventClass":
                data["eventClass_url"] = self._get_eventClass_url(value)
            elif field == "device":
                url, titleOrId = self._get_device_url(value)
                if url:
                    data["device_url"] = url
                if titleOrId:
                    data["device_title"] = titleOrId
                else:
                    data["device_title"] = value
            elif field == "component":
                dev = getattr(zevent, "device", None)
                if dev:
                    url, titleOrId = self._get_component_url(dev, value)
                    if url:
                        data["component_url"] = url
                    if titleOrId:
                        data["component_title"] = titleOrId
                    else:
                        data["component_title"] = value
            else:
                value = _shortvalue
            data[field] = value
        data["evid"] = zevent.evid
        data["id"] = zevent.evid
        return data
