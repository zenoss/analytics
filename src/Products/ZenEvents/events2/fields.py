##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class EventField:
    UUID = 'uuid'
    CREATED_TIME = 'created_time'
    FINGERPRINT = 'fingerprint'
    EVENT_CLASS = 'event_class'
    EVENT_CLASS_KEY = 'event_class_key'
    EVENT_CLASS_MAPPING_UUID = 'event_class_mapping_uuid'
    ACTOR = 'actor'
    SUMMARY = 'summary'
    MESSAGE = 'message'
    SEVERITY = 'severity'
    EVENT_KEY = 'event_key'
    EVENT_GROUP = 'event_group'
    AGENT = 'agent'
    SYSLOG_PRIORITY = 'syslog_priority'
    SYSLOG_FACILITY = 'syslog_facility'
    NT_EVENT_CODE = 'nt_event_code'
    MONITOR = 'monitor'
    DETAILS = 'details'
    STATUS = 'status'
    TAGS = 'tags'
    FLAPPING_INTERVAL = 'flapping_interval_seconds'
    FLAPPING_THRESHOLD = 'flapping_threshold'
    FLAPPING_SEVERITY = 'flapping_severity'

    class Actor:
        ELEMENT_TYPE_ID = 'element_type_id'
        ELEMENT_IDENTIFIER = 'element_identifier'
        ELEMENT_TITLE = 'element_title'
        ELEMENT_UUID = 'element_uuid'
        ELEMENT_SUB_TYPE_ID = 'element_sub_type_id'
        ELEMENT_SUB_IDENTIFIER = 'element_sub_identifier'
        ELEMENT_SUB_TITLE = 'element_sub_title'
        ELEMENT_SUB_UUID = 'element_sub_uuid'

    class Detail:
        NAME = 'name'
        VALUE = 'value'

    class Tag:
        TYPE = 'type'
        UUID = 'uuid'

class EventSummaryField:
    UUID = 'uuid'
    OCCURRENCE = 'occurrence'
    STATUS = 'status'
    FIRST_SEEN_TIME = 'first_seen_time'
    STATUS_CHANGE_TIME = 'status_change_time'
    LAST_SEEN_TIME = 'last_seen_time'
    COUNT = 'count'
    CURRENT_USER_UUID = 'current_user_uuid'
    CURRENT_USER_NAME = 'current_user_name'
    CLEARED_BY_EVENT_UUID = 'cleared_by_event_uuid'
    NOTES = 'notes'
    AUDIT_LOG = 'audit_log'

class ZepRawEventField:
    EVENT = 'event'
    CLEAR_EVENT_CLASS = 'clear_event_class'
