##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.Zuul.utils import ZuulMessageFactory as _t
from copy import deepcopy

def manage_addUserInterfaceSettings(context, id="UserInterfaceSettings"):
    settings = UserInterfaceSettings(id)
    context._setObject(id, settings)
    return getattr(context, id)

class UserInterfaceSettings(ZenModelRM):
    """
    Container for various settings on the User Interface. This is
    serialized and sent down to the server on every page request. Any
    user configurable settings that apply to the user interface should
    be added here
    """

    _relations = ()

    _properties = (
        {'id': 'enableHtmlInEventFields', 'type': 'boolean', 'mode': 'w'},
        {'id': 'enableInfiniteGridForEvents', 'type': 'boolean', 'mode': 'w'},
        {'id': 'enableInfiniteGridForComponents', 'type': 'boolean', 'mode': 'w'},
        {'id': 'enableLiveSearch', 'type': 'boolean', 'mode': 'w'},
        {'id': 'incrementalTreeLoad', 'type': 'boolean', 'mode': 'w'},
        {'id': 'showEventSeverityIcons', 'type': 'boolean', 'mode': 'w'},
        {'id': 'loadDeviceTreeFromCatalog', 'type': 'boolean', 'mode': 'w'},
        {'id': 'enableTreeFilters', 'type': 'boolean', 'mode': 'w'},
        {'id': 'showPageStatistics', 'type' : 'boolean', 'mode':'w'},
        {'id': 'defaultTimeRange', 'type': 'int', 'mode': 'w'},
        {'id': 'graphColumns', 'type': 'int', 'mode': 'w'},
        {'id': 'deviceGridBufferSize', 'type': 'int', 'mode': 'w'},
        {'id': 'componentGridBufferSize', 'type': 'int', 'mode': 'w'},
        {'id': 'eventConsoleBufferSize', 'type': 'int', 'mode': 'w'},
        {'id': 'deviceMoveJobThreshold', 'type': 'int', 'mode': 'w'},
        {'id': 'zenjobsRefreshInterval', 'type' : 'int', 'mode':'w'},
        {'id': 'zenjobsGridBufferSize', 'type' : 'int', 'mode':'w'},
        )

    # information about the properties that is used for the UI
    _propertyMetaData = {
        'enableHtmlInEventFields': {'xtype': 'checkbox', 'name': _t('Enable Hyperlinks in Event Fields'), 'defaultValue': False},
        'enableInfiniteGridForEvents': {'xtype': 'checkbox', 'name': _t('Enable Infinite Grids for Events'), 'defaultValue': True},
        'enableInfiniteGridForComponents': {'xtype': 'checkbox', 'name': _t('Enable Infinite Grids for Components'), 'defaultValue': True},
        'enableLiveSearch': {'xtype': 'checkbox', 'name': _t('Enable Live Filters'), 'defaultValue': True},
        'incrementalTreeLoad': {'xtype': 'checkbox', 'name': _t('Enable Incremental Tree Loading on the Infrastructure Page'), 'defaultValue': True},
        'showEventSeverityIcons': {'xtype': 'checkbox', 'name': _t('Show Tree Event Severity Icons (disabling may speed up the page load)'), 'defaultValue': True},
        'loadDeviceTreeFromCatalog': {'xtype': 'checkbox', 'name': _t('Load Infrastructure Page\'s Device Tree from Catalog'), 'defaultValue': False},
        'enableTreeFilters': {'xtype': 'checkbox', 'name': _t('Enable Tree Filters'), 'defaultValue': True},
        'defaultTimeRange': {'xtype': 'combo', 'name': _t('Default Time Range'), 'queryMode': 'local', 'store': [['0', 'Last Hour'], ['1','Last 24 Hours'], ['2','Last Week'], ['3','Last 30 Days'], ['4','Last Year']], 'defaultValue': '0', 'allowBlank': False, 'editable': False},
        'graphColumns': {'xtype': 'combo', 'name': _t('Number of Graph Columns'), 'queryMode': 'local', 'store': [['0', 'Auto'], ['1','1'], ['2','2'], ['3','3']], 'defaultValue': '0', 'allowBlank': False, 'editable': False},
        'deviceGridBufferSize': {'xtype': 'numberfield', 'name': _t('Device Grid Buffer Size'), 'defaultValue': 100, 'minValue': 50, 'maxValue': 1000, 'allowBlank': False},
        'componentGridBufferSize': {'xtype': 'numberfield', 'name': _t('Component Grid Buffer Size'), 'defaultValue': 25, 'minValue': 10, 'maxValue': 1000, 'allowBlank': False},
        'eventConsoleBufferSize': {'xtype': 'numberfield', 'name': _t('Event Console Buffer Size'), 'defaultValue': 200, 'minValue': 50, 'maxValue': 1000, 'allowBlank': False},
        'deviceMoveJobThreshold': {'xtype': 'numberfield', 'name': _t('Device Move Job Threshold'), 'defaultValue': 5, 'minValue': 0, 'allowBlank': False},
        'zenjobsRefreshInterval': {'xtype': 'numberfield', 'name': _t('Job Notification Refresh Interval (seconds)'), 'defaultValue' : 10, 'minValue' : 0, 'maxValue': 300, 'allowBlank': False},
        'showPageStatistics': {'xtype': 'checkbox', 'name': _t('Show Page Statistics (debug information)'), 'defaultValue' : False},
        'zenjobsGridBufferSize': {'xtype': 'numberfield', 'name': _t('Job Grid Buffer Size'), 'defaultValue': 100, 'minValue': 50, 'maxValue': 300, 'allowBlank': False},
    }

    def getInterfaceSettings(self):
        """
        @rtype:   Dictionary
        @return Key/Value pair of all settings for the UserInterface
        """
        settings = {}
        for prop in self.getSettingsData():
            propId = prop['id']
            settings[propId] = prop['value']
        return settings

    def getSettingsData(self):
        """
        @rtype: Dictionary
        @return: The value of the settings along with some meta information
        for display
        """
        settings = deepcopy(self._properties)
        for prop in settings:
            prop.update(self._propertyMetaData[prop['id']])
            prop['value'] = getattr(self, prop['id'], prop['defaultValue'])
        return settings
