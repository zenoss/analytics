##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from unittest import TestCase
from mock import Mock, patch, create_autospec, sentinel

from ..reporter import (
    AGENT,
    EXPLANATION,
    ADMReporter,
    Change_Add,
    Change_Add_Blocked,
    Change_Rebuild,
    Change_Remove,
    Change_Remove_Blocked,
    Change_Set,
    Change_Set_Blocked,
    Event,
    IEventPublisher,
    log,
)

PATH = {"src": "Products.DataCollector.ApplyDataMap.reporter"}


class TestModule(TestCase):
    def test_globals(t):
        t.assertEqual(AGENT, "ApplyDataMap")
        t.assertEqual(
            EXPLANATION, "Event sent as zCollectorLogChanges is True"
        )
        t.assertEqual(log.name, "zen.ApplyDataMap.reporter")


class TestADMReporter_send_event(TestCase):
    @patch("{src}.getUtility".format(**PATH), autospec=True)
    @patch("{src}.guid".format(**PATH), autospec=True)
    @patch("{src}.Event".format(**PATH), autospec=True)
    def test__send_event(t, Event, guid, getUtility):
        reporter = ADMReporter("datacollector")
        t.assertEqual(
            reporter._ADMReporter__publisher, getUtility.return_value
        )

        reporter._send_event({"event": "dict"})

        guid.generate.assert_called_with(1)
        Event.buildEventFromDict.assert_called_with({"event": "dict"})
        t.assertEqual(
            Event.buildEventFromDict.return_value.evid,
            guid.generate.return_value,
        )
        getUtility.assert_called_with(IEventPublisher, "batch")
        reporter._ADMReporter__publisher.publish.assert_called_with(
            Event.buildEventFromDict.return_value
        )

    @patch("{src}.getUtility".format(**PATH), autospec=True)
    @patch("{src}.guid".format(**PATH), autospec=True)
    @patch("{src}.Event".format(**PATH), autospec=True)
    def test__send_event_without_datacollector(t, Event, guid, getUtility):
        """datacollector is used as a flag to turn event sending on"""
        reporter = ADMReporter()
        reporter._send_event({"event": "dict"})
        reporter._ADMReporter__publisher.publish.assert_not_called()


class TestADMReporter(TestCase):
    def setUp(t):
        patches = ["getUtility"]
        for target in patches:
            patcher = patch("{src}.{}".format(target, **PATH), autospec=True)
            setattr(t, target, patcher.start())
            t.addCleanup(patcher.stop)

        t.reporter = ADMReporter()
        t.reporter._send_event = create_autospec(t.reporter._send_event)

        t.device = Mock(name="device", zCollectorLogChanges=True)
        t.objmap = Mock(name="object_map")

    def test_report_added(t):
        t.reporter.report_added(t.device, t.objmap)

        msg = "adding object {} to relationship {}".format(
            t.objmap.id, t.objmap._relname
        )
        t.reporter._send_event.assert_called_with(
            {
                "eventClass": Change_Add,
                "device": t.device.id,
                "component": t.objmap.id,
                "summary": msg,
                "severity": Event.Info,
                "agent": AGENT,
                "explanation": EXPLANATION,
            }
        )

    def test_report_added_directive(t):
        t.reporter.report_added = create_autospec(t.reporter.report_added)
        t.objmap._directive = "add"
        t.reporter.report_directive(t.device, t.objmap)
        t.reporter.report_added.assert_called_with(t.device, t.objmap)

    def test_report_add_locked(t):
        t.device.sendEventWhenBlocked.return_value = True
        t.objmap.modname = "Products.module.objtype"

        t.reporter.report_add_locked(t.device, t.objmap)

        msg = "Add locked: {} '{}' on {}".format(
            "objtype", t.objmap.id, t.device.id
        )
        t.reporter._send_event.assert_called_with(
            {
                "eventClass": Change_Add_Blocked,
                "device": t.device.id,
                "component": t.objmap.id,
                "summary": msg,
                "severity": Event.Warning,
                "agent": AGENT,
                "explanation": EXPLANATION,
            }
        )

    def test_report_add_locked_directive(t):
        report_add_locked = create_autospec(t.reporter.report_add_locked)
        t.reporter.report_add_locked = report_add_locked
        t.objmap._directive = "add_locked"
        t.reporter.report_directive(t.device, t.objmap)
        report_add_locked.assert_called_with(t.device, t.objmap)

    def test_report_updated(t):
        t.reporter.report_updated(t.device, t.objmap)

        msg = "set attributes {} on object {}".format(
            t.objmap._diff, t.device.id
        )
        args, kwargs = t.reporter._send_event.call_args
        expected_event = {
            "eventClass": Change_Set,
            "device": t.device.id,
            "component": t.objmap.id,
            "summary": msg,
            "severity": Event.Info,
            "agent": AGENT,
            "explanation": EXPLANATION,
        }
        t.assertDictEqual(args[0], expected_event)

    def test_report_updated_directive(t):
        report_updated = create_autospec(t.reporter.report_updated)
        t.reporter.report_updated = report_updated
        t.objmap._directive = "update"
        t.reporter.report_directive(t.device, t.objmap)
        report_updated.assert_called_with(t.device, t.objmap)

    def test_report_update_locked(t):
        t.reporter.report_update_locked(t.device, t.objmap)

        msg = "update locked: {}".format(t.objmap.id)
        t.reporter._send_event.assert_called_with(
            {
                "eventClass": Change_Set_Blocked,
                "device": t.device.id,
                "component": t.objmap.id,
                "summary": msg,
                "severity": Event.Warning,
                "agent": AGENT,
                "explanation": EXPLANATION,
            }
        )

    def test_report_update_locked_directive(t):
        report_update_locked = create_autospec(t.reporter.report_update_locked)
        t.reporter.report_update_locked = report_update_locked
        t.objmap._directive = "update_locked"
        t.reporter.report_directive(t.device, t.objmap)
        report_update_locked.assert_called_with(t.device, t.objmap)

    def test_report_removed(t):
        t.reporter.report_removed(t.device, t.objmap)

        msg = "removed object {} from rel {} on device {}".format(
            t.objmap.id, t.objmap._relname, t.device.id
        )
        t.reporter._send_event.assert_called_with(
            {
                "eventClass": Change_Remove,
                "device": t.device.id,
                "component": t.objmap.id,
                "summary": msg,
                "severity": Event.Info,
                "agent": AGENT,
                "explanation": EXPLANATION,
            }
        )

    def test_report_removed_no_map(t):
        t.reporter.report_removed(
            t.device, target=sentinel.target, relname=sentinel.relname
        )

        msg = "removed object {} from rel {} on device {}".format(
            sentinel.target, sentinel.relname, t.device.id
        )
        t.reporter._send_event.assert_called_with(
            {
                "eventClass": Change_Remove,
                "device": t.device.id,
                "component": sentinel.target,
                "summary": msg,
                "severity": Event.Info,
                "agent": AGENT,
                "explanation": EXPLANATION,
            }
        )

    def test_report_removed_directive(t):
        report_removed = create_autospec(t.reporter.report_removed)
        t.reporter.report_removed = report_removed
        t.objmap._directive = "remove"
        t.reporter.report_directive(t.device, t.objmap)
        report_removed.assert_called_with(t.device, t.objmap)

    def test_report_delete_locked(t):
        t.reporter.report_delete_locked(t.device, t.objmap)

        msg = "deletion locked on {} from rel {} on device {}".format(
            t.objmap.id, t.objmap._relname, t.device.id
        )
        t.reporter._send_event.assert_called_with(
            {
                "eventClass": Change_Remove_Blocked,
                "device": t.device.id,
                "component": t.objmap.id,
                "summary": msg,
                "severity": Event.Warning,
                "agent": AGENT,
                "explanation": EXPLANATION,
            }
        )

    def test_report_delete_locked_no_map(t):
        t.reporter.report_delete_locked(
            t.device, target=sentinel.target, relname=sentinel.relname
        )

        msg = "deletion locked on {} from rel {} on device {}".format(
            sentinel.target, sentinel.relname, t.device.id
        )
        t.reporter._send_event.assert_called_with(
            {
                "eventClass": Change_Remove_Blocked,
                "device": t.device.id,
                "component": sentinel.target,
                "summary": msg,
                "severity": Event.Warning,
                "agent": AGENT,
                "explanation": EXPLANATION,
            }
        )

    def test_report_delete_locked_directive(t):
        report_delete_locked = create_autospec(t.reporter.report_delete_locked)
        t.reporter.report_delete_locked = report_delete_locked
        t.objmap._directive = "delete_locked"
        t.reporter.report_directive(t.device, t.objmap)
        report_delete_locked.assert_called_with(t.device, t.objmap)

    def test_report_rebuild(t):
        t.reporter.report_rebuild(t.device, t.objmap)

        msg = "rebuilt object {} to relationship {}".format(
            t.objmap.id, t.objmap._relname
        )
        t.reporter._send_event.assert_called_with(
            {
                "eventClass": Change_Rebuild,
                "device": t.device.id,
                "component": t.objmap.id,
                "summary": msg,
                "severity": Event.Info,
                "agent": AGENT,
                "explanation": EXPLANATION,
            }
        )

    def test_report_rebuild_directive(t):
        report_rebuild = create_autospec(t.reporter.report_delete_locked)
        t.reporter.report_rebuild = report_rebuild
        t.objmap._directive = "rebuild"
        t.reporter.report_directive(t.device, t.objmap)
        report_rebuild.assert_called_with(t.device, t.objmap)

    def test_report_nochange(t):
        """NOOP unless reporting unchanged objects is needed"""
        t.reporter.report_nochange(t.device, t.objmap)
        t.assertEqual(t.reporter._send_event.call_count, 0)

    def test_nochange_directive(t):
        report_nochange = create_autospec(t.reporter.report_nochange)
        t.reporter.report_nochange = report_nochange
        t.objmap._directive = "nochange"
        t.reporter.report_directive(t.device, t.objmap)
        report_nochange.assert_called_with(t.device, t.objmap)
