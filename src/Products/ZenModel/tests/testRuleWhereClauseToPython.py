##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenEvents.WhereClause import Text, Select, Compare, Enumerated, DeviceGroup, EventClass
from Products.ZenEvents.WhereClause import toPython, PythonConversionException
from ZenModelBaseTest import ZenModelBaseTest
from zenoss.protocols.protobufs.zep_pb2 import STATUS_NEW, SEVERITY_ERROR, SYSLOG_PRIORITY_DEBUG


class TestRuleWhereClauseToPython(ZenModelBaseTest):

    def setUp(self):

        # this var has the structure: [(old_where, new_python), ...]
        # These rules are adapted from a customers rules and have been scrubbed
        # to use mock data, such as deviceClass. The structure and format have
        # not changed.
        self.test_rules = [
            # this where clause was built with every available filter in the old UI.
            ("(prodState < 1000) and (devicePriority < 5) and (facility = 11) and (eventClassKey != '/Status/Perf') and (eventKey like '%/Status%') and (agent = 'zenhub') and (manager like '%manager_ends_with') and (deviceClass like '/%') and (message not like '%msg doesnt contain%') and (eventState < 1) and (ntevid = '12345') and (severity < 5) and (eventClass like '/Status/Heartbeat%') and (summary like '%foobaz%') and (priority = 0) and (deviceGroups like '%|/%') and (location like '%loc_contains%') and (ownerId = 'admin' or ownerId = 'tester') and (ipAddress like '%192.168%') and (systems like '%|/%')",
             '(dev.production_state < 1000) and (dev.priority < 5) and (evt.syslog_facility == 11) and (evt.event_class_key != "/Status/Perf") and ("/Status" in evt.event_key) and (evt.agent == "zenhub") and (evt.monitor.endswith("manager_ends_with")) and (dev.device_class.startswith("/")) and ("msg doesnt contain" not in evt.message) and (evt.status < 1) and (evt.nt_event_code == 12345) and (evt.severity < 5) and (evt.event_class.startswith("/Status/Heartbeat")) and ("foobaz" in evt.summary) and (evt.syslog_priority == 7) and ("/" in dev.groups) and ("loc_contains" in dev.location) and ((evt.current_user_name == "admin") or (evt.current_user_name == "tester")) and ("192.168" in dev.ip_address) and ("/" in dev.systems)'),

            # Same as above but with all OR clauses to ensure we evaluate all possibilities
            ("(prodState < 1000) or (devicePriority < 5) or (facility = 11) or (eventClassKey != '/Status/Perf') or (eventKey like '%/Status%') or (agent = 'zenhub') or (manager like '%manager_ends_with') or (deviceClass like '/%') or (message not like '%msg doesnt contain%') or (eventState < 1) or (severity < 5) or (eventClass like '/Status/Heartbeat%') or (summary like '%foobaz%') or (priority = 0) or (deviceGroups like '%|/%') or (location like '%loc_contains%') or (ownerId = 'admin' or ownerId = 'tester') or (ipAddress like '%192.168%') or (systems like '%|/%')",
             '(dev.production_state < 1000) or (dev.priority < 5) or (evt.syslog_facility == 11) or (evt.event_class_key != "/Status/Perf") or ("/Status" in evt.event_key) or (evt.agent == "zenhub") or (evt.monitor.endswith("manager_ends_with")) or (dev.device_class.startswith("/")) or ("msg doesnt contain" not in evt.message) or (evt.status < 1) or (evt.severity < 5) or (evt.event_class.startswith("/Status/Heartbeat")) or ("foobaz" in evt.summary) or (evt.syslog_priority == 7) or ("/" in dev.groups) or ("loc_contains" in dev.location) or (evt.current_user_name == "admin") or (evt.current_user_name == "tester") or ("192.168" in dev.ip_address) or ("/" in dev.systems)'),

            ("(prodState = 1000) and (deviceClass like '/Network%' or deviceClass like '/Server%') and (eventState = 0) and (severity >= 5) and (summary not like '%System Fault: FAN FAULT is detected.%') and (deviceGroups like '%|/test%' or deviceGroups like '%|/another/test%')",
             "(dev.production_state == 1000) and ((dev.device_class.startswith('/Network')) or (dev.device_class.startswith('/Server'))) and (evt.status == 0) and (evt.severity >= 5) and ('System Fault: FAN FAULT is detected.' not in evt.summary) and (('/test' in dev.groups) or ('/another/test' in dev.groups))"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (device != 'telcotesting1.sat6') and (eventState = 0) and (severity >= 5)",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and (elem.name != 'telcotesting1.sat6') and (evt.status == 0) and (evt.severity >= 5)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (device not like '%stl3%') and (eventState = 0) and (severity >= 5) and (summary not like '%System Fault: FAN FAULT is detected.%') and (deviceGroups not like '%|/test%')",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and ('stl3' not in elem.name) and (evt.status == 0) and (evt.severity >= 5) and ('System Fault: FAN FAULT is detected.' not in evt.summary) and ('/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 4) and (deviceGroups not like '%|/test%')",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and (evt.status == 0) and (evt.severity >= 4) and ('/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (deviceGroups not like '%|/another/test%')",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and ('/another/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (deviceGroups not like '%|/test%')",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and ('/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (summary not like '%System Fault: FAN FAULT is detected.%') and (deviceGroups not like '%|/test%')",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and ('System Fault: FAN FAULT is detected.' not in evt.summary) and ('/test' not in dev.groups)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (summary not like '%System Fault: FAN FAULT is detected.%')",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and ('System Fault: FAN FAULT is detected.' not in evt.summary)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5) and (summary not like '%threshold of Over%' or summary not like '%fan fault%')",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and (evt.status == 0) and (evt.severity >= 5) and (('threshold of Over' not in evt.summary) or ('fan fault' not in evt.summary))"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 5)",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and (evt.status == 0) and (evt.severity >= 5)"),

            ("(prodState = 1000) and (deviceClass like '/Network/Router%') and (eventState = 0) and (severity >= 5)",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network/Router')) and (evt.status == 0) and (evt.severity >= 5)"),

            ("(prodState = 1000) and (deviceClass like '/Server%') and (device != 'localhost') and (eventState = 0) and (count > 1) and (severity >= 4)",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Server')) and (elem.name != 'localhost') and (evt.status == 0) and (evt.count > 1) and (evt.severity >= 4)"),

            ("(prodState = 1000) and (deviceClass like '/Server%') and (eventState = 0) and (count > 1) and (severity >= 4)",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Server')) and (evt.status == 0) and (evt.count > 1) and (evt.severity >= 4)"),

            ("(prodState = 1000) and (deviceClass like '/Server%') and (eventState = 0) and (severity >= 4)",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Server')) and (evt.status == 0) and (evt.severity >= 4)"),

            ("(prodState = 1000) and (eventClass like '/Status/Perf%') and (eventState = 0) and (summary like '%threshold of Over%') and (deviceGroups like '%|/test%')",
             "(dev.production_state == 1000) and (evt.event_class.startswith('/Status/Perf')) and (evt.status == 0) and ('threshold of Over' in evt.summary) and ('/test' in dev.groups)"),

            ("(prodState = 1000) and (eventState = 0) and (eventClass like '/Status/Perf%') and (summary like '%threshold of Over%') and (deviceGroups like '%|/%') and (systems like '%|/foo%' or systems like '%|/foo/bar%')",
             "(dev.production_state == 1000) and (evt.status == 0) and (evt.event_class.startswith('/Status/Perf')) and ('threshold of Over' in evt.summary) and ('/' in dev.groups) and (('/foo' in dev.systems) or ('/foo/bar' in dev.systems))"),

            ("severity >= 5 and eventState = 0 and prodState >= 1000",
             "(evt.severity >= 5) and (evt.status == 0) and (dev.production_state >= 1000)"),

            ("(prodState = 1000) and (deviceClass like '/Network%') and (eventState = 0) and (severity >= 3) and (eventClass like '/Perf/CPU%' or eventClass like '/Perf/Feature Status%' or eventClass like '/Perf/Interface/Throughput%' or eventClass like '/Perf/TrafficLoad%' or eventClass like '/Status/IpInterface%' or eventClass like '/Status/Ping%' or eventClass like '/Status/PingStatus%' or eventClass like '/Status/Uptime%') and (deviceGroups like '%|/NSG-ent-net%')",
             "(dev.production_state == 1000) and (dev.device_class.startswith('/Network')) and (evt.status == 0) and (evt.severity >= 3) and ((evt.event_class.startswith('/Perf/CPU')) or (evt.event_class.startswith('/Perf/Feature Status')) or (evt.event_class.startswith('/Perf/Interface/Throughput')) or (evt.event_class.startswith('/Perf/TrafficLoad')) or (evt.event_class.startswith('/Status/IpInterface')) or (evt.event_class.startswith('/Status/Ping')) or (evt.event_class.startswith('/Status/PingStatus')) or (evt.event_class.startswith('/Status/Uptime'))) and ('/NSG-ent-net' in dev.groups)"),

            ("severity >= 5",
             "(evt.severity >= 5)"),

            ("(ntevid = '5')",
             "(evt.nt_event_code == 5)"),

            # Verify that priority correctly converts to the new mappings in 4.x
            # See issue #29909. (priority = 0) is 'debug'.
            ("(priority = 0)",
             "(evt.syslog_priority == 7)")
        ]

        self.exception_rules = [
            "(ntevid like 'abc%')",
            "(ntevid != 'a')",
        ]


        # Set up really controlled meta for these mock alert rules.
        deviceGroups_options = [(0, '/'), (1, '/test'), (2, '/another'), (3, '/another/test')]
        deviceGroups = DeviceGroup('Device Group', deviceGroups_options)

        systems_options =  [(0, '/'), (1, '/foo'), (2, '/foo/bar'), (3, '/baz')]
        systems = DeviceGroup('Systems', systems_options)

        esconv = [(0, 'New'), (1, 'Acknowledged'), (2, 'Suppressed')]
        sconv = [(5, 'Critical'), (4, 'Error'), (3, 'Warning'), (2, 'Info'), (1, 'Debug'), (0, 'Clear')]
        pconv = [(1000, 'Production'), (500, 'Pre-Production'), (400, 'Test'), (300, 'Maintenance'), (-1, 'Decommissioned')]
        dpconv = [(5, 'Highest'), (4, 'High'), (3, 'Normal'), (2, 'Low'), (1, 'Lowest'), (0, 'Trivial')]
        owners =  [('admin', 'admin'), ('tester', 'tester')]
        eventClasses = [
                ('/', '/'),
                ('/App', '/App'),
                ('/Status', '/Status'),
                ('/Status/Heartbeat', '/Status/Heartbeat'),
                ('/Status/Perf', '/Status/Perf'),
                ('/Status/Ping', '/Status/Ping')]
        deviceClasses = [
                ('/', '/'),
                ('/Discovered', '/Discovered'),
                ('/Server', '/Server'),
                ('/Server/Linux', '/Server/Linux'),
                ('/Network', '/Network'),
                ('/Network/Router','/Network/Router')]

        self.generated_meta = dict(
            eventClass=EventClass('Event Class', eventClasses),
            deviceClass=EventClass('Device Class', deviceClasses),
            summary=Text("Summary"),
            location=Text("Location"),
            prodState=Enumerated("Production State",pconv),
            severity=Enumerated("Severity",sconv),
            eventState=Enumerated("Event State",esconv),
            device=Text("Device"),
            devicePriority=Enumerated("Device Priority",dpconv),
            eventClassKey=Text("Event Class Key"),
            count=Compare("Count"),
            manager=Text("Manager"),
            agent=Select("Agent",[(x, x) for x in
                "zenhub", "zenping", "zensyslog", "zentrap",
                "zenmodeler", "zenperfsnmp", "zencommand", "zenprocess", "zenwin",
                "zeneventlog"]),
            facility=Select("Facility",[
                "auth","authpriv","cron","daemon","kern","lpr","mail",
                "mark","news","security","syslog","user","uucp",
                "local0","local1","local2","local3","local4",
                "local05","local6","local7"]),
            priority=Select("Priority",[
                "debug","info","notice","warning","error","critical",
                "alert","emergency"]),
            component=Text("Component"),
            eventKey=Text("Event Key"),
            message=Text("Message"),
            ntevid=Text("ntevid"),
            ipAddress=Text("IP Address"),
            ownerId=Select("Owner Id", owners),
            deviceGroups = deviceGroups,
            systems = systems,
        )

    def testRuleWhereClauseToPython(self):
        class MockEvent(object):
            summary = 'Event foobaz summary'
            current_user_name = 'admin'
            event_class = '/App/Info'
            event_class_key = 'EventClassKey'
            event_key = '/Status/Heartbeat'
            status = STATUS_NEW
            severity = SEVERITY_ERROR
            syslog_facility = 11
            syslog_priority = 0
            agent = 'zenhub'
            monitor = 'my_manager_ends_with'
            message = 'message does contain'
            nt_event_code = '1000'
        class MockDevice(object):
            device_class = '/Discovered'
            priority = 2
            production_state = 500
            groups = '|/Group1|/Group2'
            systems = '|/System1|/System2'
            location = 'loc_contains'
            ip_address = '192.168.1.2'
        class MockElem(object):
            pass
        class MockSubElem(object):
            pass

        evt = MockEvent()
        dev = MockDevice()
        elem = MockElem()
        sub_elem = MockSubElem()

        for where_clause, python_statement in self.test_rules:
            converted_python = toPython(self.generated_meta, where_clause)
            # TODO: Change strings above to include double quotes instead of single quotes to match rule builder
            self.assertEquals(converted_python, python_statement.replace("'", '"'))
            fn = eval('lambda evt, dev, elem, sub_elem: ' + converted_python)
            # TODO: Validate the boolean logic of before/after migration! We can't just validate the string - we need
            # to verify that it evaluates the same before/after.
            fn(evt, dev, elem, sub_elem)

        for where_clause in self.exception_rules:
            self.assertRaises(PythonConversionException, toPython, self.generated_meta, where_clause)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRuleWhereClauseToPython))
    return suite
