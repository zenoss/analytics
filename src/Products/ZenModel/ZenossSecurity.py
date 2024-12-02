##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


# Any updates to permissions in this file must be reflected in
# ZenModel/permissions.zcml.

# Zenoss Roles
ZEN_USER_ROLE = 'ZenUser'
ZEN_MANAGER_ROLE = 'ZenManager'
OWNER_ROLE = 'Owner'
MANAGER_ROLE = 'Manager'

# notifications get their own roles which are managed locally on the objects
# themselves. We cannot reuse ZEN_USER_ROLE or ZEN_MANAGER_ROLE because we need
# finer grained control at the object level, not the action level.
NOTIFICATION_VIEW_ROLE = "Notification View"
NOTIFICATION_UPDATE_ROLE = "Notification Update"
NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE = "Notification Subscription Manager"

# Triggers also get their own roles which are managed locally on 'stub' objects.
# the real data for triggers is persisted externally in the event processing
# system.
TRIGGER_VIEW_ROLE = "Trigger View"
TRIGGER_UPDATE_ROLE = "Trigger Update"
TRIGGER_MANAGER_ROLE = "Trigger Manager"


# Zenoss Permissions
ZEN_COMMON = 'ZenCommon'
ZEN_MANAGE_DMD = 'Manage DMD'
ZEN_UPDATE = "ZenUpdate"
ZEN_DELETE = "Delete objects"
ZEN_ADD = 'Add DMD Objects'


# Network specific permissions
ZEN_CHANGE_NET = 'Change Network'


# Notification specific permissions
VIEW_NOTIFICATION = "View Notification"
UPDATE_NOTIFICATION = "Update Notification"
MANAGE_NOTIFICATION_SUBSCRIPTIONS = "Manage Notification Subscriptions"

# Trigger specific permissions
VIEW_TRIGGER = "View Trigger"
UPDATE_TRIGGER = "Update Trigger"
MANAGE_TRIGGER = "Manage Trigger"


ZEN_VIEW = 'View'
ZEN_VIEW_HISTORY = 'View History'

# Events
ZEN_MANAGE_EVENTMANAGER = 'Manage EventManager'
ZEN_MANAGE_EVENTS = 'Manage Events'
ZEN_SEND_EVENTS = 'Send Events'

# User Settings
ZEN_CHANGE_SETTINGS = 'Change Settings'
ZEN_CHANGE_ALERTING_RULES = 'Change Alerting Rules'
ZEN_CHANGE_EVENT_VIEWS = 'Change Event Views'
ZEN_CHANGE_ADMIN_OBJECTS = 'Change Admin Objects'

ZEN_EDIT_USER = 'Edit Users'
ZEN_EDIT_USERGROUP = 'Edit User Groups'

# Device
ZEN_CHANGE_DEVICE = 'Change Device'
# Change device production state
ZEN_CHANGE_DEVICE_PRODSTATE='Change Device Production State'
# Change Class, Rename, Reset IP
ZEN_ADMIN_DEVICE='Admin Device'
# Delete device
ZEN_DELETE_DEVICE='Delete Device'
# Model, Lock, Reset Community, Push Changes, Clear Heartbeats
ZEN_MANAGE_DEVICE='Manage Device'
# Existing permission for setLastPollSnmpUpTime, getLastPollSnmpUpTime
ZEN_MANAGE_DEVICE_STATUS='Manage Device Status'

# Run Commands
#ZEN_COLLECTOR_PLUGINS_EDIT='Modeler Plugins Edit'
#ZEN_COLLECTOR_PLUGINS_VIEW='Modeler Plugins View'
ZEN_ZPROPERTIES_EDIT='zProperties Edit'
ZEN_ZPROPERTIES_VIEW='zProperties View'
ZEN_EDIT_LOCAL_TEMPLATES='Edit Local Templates'

ZEN_RUN_COMMANDS = 'Run Commands'

# Administrate
ZEN_DEFINE_COMMANDS_EDIT='Define Commands Edit'
ZEN_DEFINE_COMMANDS_VIEW='Define Commands View'
ZEN_MAINTENANCE_WINDOW_EDIT='Maintenance Windows Edit'
ZEN_MAINTENANCE_WINDOW_VIEW='Maintenance Windows View'
ZEN_ADMINISTRATORS_EDIT='Administrators Edit'
ZEN_ADMINISTRATORS_VIEW='Administrators View'

# Included for ZenPack upgrades only. No longer used.
ZEN_VIEW_MODIFICATIONS='Unused'
