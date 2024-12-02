##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zope.component import getUtility

from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import (
    Change_Add,
    Change_Remove,
    Change_Set,
    Change_Add_Blocked,
    Change_Remove_Blocked,
    Change_Set_Blocked,
    Change_Rebuild,
)
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher
from Products.ZenUtils import guid

log = logging.getLogger("zen.ApplyDataMap.reporter")

AGENT = "ApplyDataMap"
EXPLANATION = "Event sent as zCollectorLogChanges is True"


class ADMReporter(object):
    def __init__(self, datacollector=None):
        self.__publisher = getUtility(IEventPublisher, "batch")
        self._report_map = None
        self._datacollector = datacollector

    @property
    def report_map(self):
        if not self._report_map:
            self._report_map = {
                "add": self.report_added,
                "add_locked": self.report_add_locked,
                "update": self.report_updated,
                "update_locked": self.report_update_locked,
                "remove": self.report_removed,
                "delete_locked": self.report_delete_locked,
                "rebuild": self.report_rebuild,
                "nochange": self.report_nochange,
            }
        return self._report_map

    def _send_event(self, event_dict):
        if not self._datacollector:
            return
        event = Event.buildEventFromDict(event_dict)
        event.evid = guid.generate(1)
        self.__publisher.publish(event)

    def report_directive(self, device, objmap):
        """call the appropriate reporting method based on the objectmap"""
        self.report_map[objmap._directive](device, objmap)

    def report_added(self, device, objmap):
        msg = "adding object {} to relationship {}".format(
            objmap.id, objmap._relname
        )
        log.debug(msg)
        event = {
            "eventClass": Change_Add,
            "device": device.id,
            "component": objmap.id,
            "summary": msg,
            "severity": Event.Info,
            "agent": AGENT,
            "explanation": EXPLANATION,
        }
        self._send_event(event)

    def report_add_locked(self, device, objmap):
        objtype = objmap.modname.split(".")[-1]
        msg = "Add locked: {} '{}' on {}".format(objtype, objmap.id, device.id)
        log.debug(msg)
        event = {
            "eventClass": Change_Add_Blocked,
            "device": device.id,
            "component": objmap.id,
            "summary": msg,
            "severity": Event.Warning,
            "agent": AGENT,
            "explanation": EXPLANATION,
        }
        self._send_event(event)

    def report_updated(self, device, objmap):
        component_id = getattr(objmap, "id", device.id)
        msg = "set attributes {} on object {}".format(objmap._diff, device.id)
        log.debug(msg)
        event = {
            "eventClass": Change_Set,
            "device": device.id,
            "component": component_id,
            "summary": msg,
            "severity": Event.Info,
            "agent": AGENT,
            "explanation": EXPLANATION,
        }
        self._send_event(event)

    def report_update_locked(self, device, objmap):
        msg = "update locked: {}".format(objmap.id)
        log.debug(msg)
        event = {
            "eventClass": Change_Set_Blocked,
            "device": device.id,
            "component": objmap.id,
            "summary": msg,
            "severity": Event.Warning,
            "agent": AGENT,
            "explanation": EXPLANATION,
        }
        self._send_event(event)

    def report_removed(self, device, objmap=None, relname=None, target=None):
        if objmap:
            relname = objmap._relname
            target = objmap.id

        msg = "removed object {} from rel {} on device {}".format(
            target, relname, device.id
        )
        log.debug(msg)
        event = {
            "eventClass": Change_Remove,
            "device": device.id,
            "component": target,
            "summary": msg,
            "severity": Event.Info,
            "agent": AGENT,
            "explanation": EXPLANATION,
        }
        self._send_event(event)

    def report_delete_locked(
        self, device, objmap=None, relname=None, target=None
    ):
        if objmap:
            relname = objmap._relname
            target = objmap.id

        msg = "deletion locked on {} from rel {} on device {}".format(
            target, relname, device.id
        )
        log.debug(msg)
        event = {
            "eventClass": Change_Remove_Blocked,
            "device": device.id,
            "component": target,
            "summary": msg,
            "severity": Event.Warning,
            "agent": AGENT,
            "explanation": EXPLANATION,
        }
        self._send_event(event)

    def report_rebuild(self, device, objmap):
        msg = "rebuilt object {} to relationship {}".format(
            objmap.id, objmap._relname
        )
        log.debug(msg)
        event = {
            "eventClass": Change_Rebuild,
            "device": device.id,
            "component": objmap.id,
            "summary": msg,
            "severity": Event.Info,
            "agent": AGENT,
            "explanation": EXPLANATION,
        }
        self._send_event(event)

    def report_nochange(self, device, objmap):
        pass
