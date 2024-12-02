/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

Ext.ns('Zenoss');

function objectRenderer(obj) {
    if (obj) {
        return obj.name;
    }
    return "";
}
var deviceColumns = [
    {
        dataIndex: 'name',
        header: _t('Device'),
        id: 'name',
        flex: 1,
        hideable: false,
        renderer: function(name, row, record) {
            return Zenoss.render.Device(record.data.uid, name);
        }
    },{
        id: 'snmpSysName',
        dataIndex: 'snmpSysName',
        width: 150,
        hidden: true,
        header: _t('System Name')
    },{
        width: 100,
        dataIndex: 'ipAddress',
        header: _t('IP Address'),
        renderer: function(ip, row, record) {
            return record.data.ipAddressString;
        }
    },{
        dataIndex: 'uid',
        header: _t('Device Class'),
        width: 120,
        renderer: Zenoss.render.DeviceClass
    },{
        id: 'status',
        dataIndex: 'status',
        sortable: true,
        hidden: true,
        filter: {
            xtype: 'multiselect-devicestatus'
        },
        header: _t('Device Status'),
        renderer: function(status, row, record) {
            switch(record.data.status){
                case true: return Zenoss.render.pingStatus('Up');
                case false: return Zenoss.render.pingStatus('Down');
                default: return Zenoss.render.pingStatus(null);
            }
        },
        width: 80
    },{
        id: 'productionState',
        dataIndex: 'productionState',
        width: 100,
        filter: {
            xtype: 'multiselect-prodstate'
        },
        header: _t('Production State'),
        renderer: function(value) {
            return Zenoss.env.PRODUCTION_STATES_MAP[value];
        }

    },{
        id: 'serialNumber',
        dataIndex: 'serialNumber',
        width: 100,
        hidden: true,
        header: _t('Serial Number')
    },{
        id: 'tagNumber',
        dataIndex: 'tagNumber',
        width: 100,
        hidden: true,
        header: _t('Tag Number')
    },{
        id: 'hwManufacturer',
        dataIndex: 'hwManufacturer',
        width: 100,
        header: _t('Hardware Manufacturer'),
        hidden: true,
        renderer: objectRenderer
    },{
        id: 'hwModel',
        dataIndex: 'hwModel',
        hidden: true,
        width: 100,
        header: _t('Hardware Model'),
        renderer: objectRenderer
    },{
        id: 'osManufacturer',
        dataIndex: 'osManufacturer',
        width: 100,
        header: _t('OS Manufacturer'),
        hidden: true,
        renderer: objectRenderer
    },{
        id: 'osModel',
        dataIndex: 'osModel',
        width: 150,
        hidden: true,
        header: _t('OS Model'),
        renderer: objectRenderer
    },{
        dataIndex: 'collector',
        width: 100,
        hidden: true,
        header: _t('Collector')
    },{
        id: 'priority',
        dataIndex: 'priority',
        width: 100,
        hidden: true,
        filter: {
            xtype: 'multiselect-devicepriority'
        },
        header: _t('Priority'),
        renderer: function(value) {
            return Zenoss.env.PRIORITIES_MAP[value];
        }
    },{
        dataIndex: 'systems',
        width: 100,
        hidden: true,
        sortable: true,
        header: _t('Systems'),
        renderer: function(systems) {
            var links = [];
            if (systems) {
                Ext.each(systems, function(system){
                    links.push(Zenoss.render.DeviceSystem(system.uid, system.name));
                });
            }
            return links.join(" | ");
        }
    },{
        dataIndex: 'groups',
        width: 100,
        hidden: true,
        sortable: true,
        header: _t('Groups'),
        renderer: function(groups) {
            var links = [];
            if (groups) {
                Ext.each(groups, function(group){
                    links.push(Zenoss.render.DeviceGroup(group.uid, group.name));
                });
            }
            return links.join(" | ");

        }
    },{
        dataIndex: 'location',
        width: 100,
        hidden: true,
        sortable: false,
        header: _t('Location'),
        renderer: function(loc){
            if (loc){
                return Zenoss.render.DeviceLocation(loc.uid, loc.name);
            }
            return '';
        }
    },{
        id: 'worstevents',
        sortable: true,
        filter: false,
        width: 75,
        dataIndex: 'events',
        header: _t('Events'),
        renderer: function(ev, ignored, record) {
            var table = Zenoss.render.worstevents(ev),
            url = record.data.uid + '/devicedetail?filter=default#deviceDetailNav:device_events';
            if (table){
                table = table.replace('table', 'table onclick="location.href=\''+url+'\';"');
            }
            return table;
        }
    }
];

Ext.define("Zenoss.DeviceGridSelectionModel", {
    extend:"Zenoss.ExtraHooksSelectionModel",

    // Default to 'MULTI'-selection mode.
    mode: 'MULTI',

    /** _selectAll
     *
     * Set to true when the user has chosen the 'select all' records.
     *
     * @private
     * @type boolean
     */
    _selectAll: false,

    /** _excludedRecords
     *
     * Stores the set of records (IDs, hashes, ??) specifically
     * deselected from the set of all selected records.
     *
     * @private
     * @type dictionary
     */
    _excludedRecords: {},

    constructor: function(config) {
        this.callParent([config]);
        this.on('select', this._includeRecord, this);
        this.on('deselect', this._excludeRecord, this);
    },

    /** _includeRecord
     *
     * Include the record in the selection. Removes the record from the
     * set of excluded records.
     *
     * @private
     * @param sm {Zenoss.DeviceGridSelectionModel}
     * @param record {Zenoss.device.DeviceModel}
     * @param index {Integer}
     */
    _includeRecord: function(sm, record) {
        if (record && this._selectAll) {
            delete this._excludedRecords[record.getId()];
        }
    },

    /** _excludeRecord
     *
     * Exclude the record from the selection. Includes the record in the
     * set of excluded records.
     *
     * @private
     * @param sm {Zenoss.DeviceGridSelectionModel}
     * @param record {Zenoss.device.DeviceModel}
     * @param index {Integer}
     */
    _excludeRecord: function(sm, record) {
        if (record && this._selectAll) {
            this._excludedRecords[record.getId()] = true;
        }
    },

    /** _handleStoreDataChange
     *
     * Callback for handling changes to the grid's datastore.  When the
     * _selectAll flag is set, this function removes the current selection
     * and selects all the records currently in the datastore.
     *
     * @private
     */
    _handleStoreDataChange: function() {
        if (this._selectAll) {
            this.suspendEvents();
            var data = this.store.data.filterBy(
                    function(item) {
                        return (! this._excludedRecords[item.getId()]);
                    },
                    this
                );
            this.select(data.items, false, true);
            this.resumeEvents();
            this.fireEvent('selectionchange', this);
        }
    },

    /** bind
     *
     * The grid will use this method to bind the datastore to the
     * grid's selection model.
     *
     * @override
     * @param store {Ext.data.Store}
     * @param initial {boolean}
     */
    bind: function(store, initial){
        if (!initial && this.store) {
            if (store !== this.store && this.store.autoDestroy) {
                this.store.destroyStore();
            } else {
                this.store.un("datachanged", this._handleStoreDataChange, this);
            }
        }
        if (store) {
            store = Ext.data.StoreManager.lookup(store);
            store.on("datachanged", this._handleStoreDataChange, this);
        }
        this.store = store;
        if (store && !initial) {
            this.refresh();
        }
    },

    /** selectAll
     *
     * Sets the _selectAll flag before selecting 'all' the records.
     *
     * @override
     */
    selectAll: function() {
        this._selectAll = true;
        this.callParent([true]);
    },

    /** selectNone
     *
     * Unsets the _selectAll flag before deselecting all the records.
     */
    selectNone: function() {
        this._selectAll = false;
        // reset the set of excluded records to the empty set.
        this._excludedRecords = {};
        // Deselect all the records without firing an event for each
        // selected record.
        this.deselectAll([true]);
        this.fireEvent('selectionchange', this);
    },

    /** deselectAll
     *
     * Doesn't deselect anything if the _selectAll flag is set.
     * This works around other parts of the ExtJS framework that
     * invoke this method without passing suppressEvents = true.
     *
     * @override
     */
    deselectAll: function() {
        if (! this._selectAll) {
            this.callParent(arguments);
        }
    },

    /** clearSelections
     *
     * Clears out all the selections only if the _selectAll flag
     * is not set.
     *
     * @override
     */
    clearSelections: function() {
        if (this.isLocked() || this._selectAll) {
            return;
        }

        // Suspend events to avoid firing the whole chain for every row
        this.suspendEvents();

        // make sure all rows are deselected so that UI renders properly
        // base class only deselects rows it knows are selected; so we need
        // to deselect rows that may have been selected via selectstate
        this.deselect(this.store.data.items, true);

        // Bring events back and fire one selectionchange for the batch
        this.resumeEvents();

        this.fireEvent('selectionchange', this);

        this.callParent(arguments);
    }
});


Ext.define('Zenoss.device.DeviceModel',{
    extend: 'Ext.data.Model',
    fields: [
        {name: 'uid', type: 'string'},
        {name: 'name', type: 'string'},
        {name: 'snmpSysName', type: 'string'},
        {name: 'ipAddress', type: 'int'},
        {name: 'ipAddressString', type: 'string'},
        {name: 'status', type: 'auto'},
        {name: 'productionState', type: 'string'},
        {name: 'serialNumber', type: 'string'},
        {name: 'tagNumber', type: 'string'},
        {name: 'hwManufacturer', type: 'object'},
        {name: 'hwModel', type: 'object'},
        {name: 'osManufacturer', type: 'object'},
        {name: 'osModel', type: 'object'},
        {name: 'collector', type: 'string'},
        {name: 'priority', type: 'string'},
        {name: 'systems', type: 'object'},
        {name: 'groups', type: 'object'},
        {name: 'location', type: 'object'},
        {name: 'events', type: 'object'},
        {name: 'availability', type: 'float'},
        {name: 'pythonClass', type: 'string'}
    ],
    idProperty: 'uid'
});

/**
 * @class Zenoss.DeviceStore
 * @extend Zenoss.DirectStore
 * Direct store for loading devices
 */
Ext.define("Zenoss.DeviceStore", {
    alias: ['widget.DeviceStore'],
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            autoLoad: false,
            pageSize: Zenoss.settings.deviceGridBufferSize,
            model: 'Zenoss.device.DeviceModel',
            initialSortColumn: "name",
            directFn: Zenoss.remote.DeviceRouter.getDevices,
            root: 'devices'
        });
        this.callParent(arguments);
    }
});

/**
 * @class Zenoss.DeviceGridPanel
 * @extends Zenoss.FilterGridPanel
 * Main grid panel for displaying a device. Used on the It Infrastructure page.
 **/
Ext.define("Zenoss.DeviceGridPanel", {
    extend: "Zenoss.FilterGridPanel",
    alias: ['widget.DeviceGridPanel', 'widget.SimpleDeviceGridPanel'],
    lastHash: null,
    constructor: function(config) {
        var storeConfig = config.storeCfg || {};
        var store = Ext.create('Zenoss.DeviceStore', storeConfig);

        Ext.applyIf(config, {
            store: store,
            columns: deviceColumns
        });

        this.callParent(arguments);
        this.on('itemdblclick', this.onItemDblClick, this);
    },

    onItemDblClick: function(view, record) {
        window.location = record.get("uid");
    },
    applyOptions: function(options){
        // only request the visible columns
        var visibleColumns = Zenoss.util.filter(this.columns, function(c){
                return !c.hidden;
            }),
            keys = Ext.Array.pluck(visibleColumns, 'dataIndex');

        keys.push('ipAddressString');
        keys.push('pythonClass');
        Ext.apply(options.params, {
            keys: keys
        });
    }
});

function showComponentLockingDialog(msg, locking, funcs) {
        Ext.create('Zenoss.dialog.LockForm', {
            applyOptions: function(values) {
                Ext.applyIf(values, funcs.fetcher());
            },
            title: msg === "" ? _t("Lock Device") : _t("Lock Devices"),
            message: msg,
            updatesChecked: locking.updates,
            deletionChecked: locking.deletion,
            sendEventChecked: locking.events,
            submitFn: function(values) {
                funcs.REMOTE.lockDevices(values, funcs.saveHandler);
            }
        }).show();
}

/**********************************************************************
 *
 * Device Actions
 *
 */
    /**
     * Drop down of action items that you can use against
     * a device. The two required parameters are
     *@param 1. saveHandler = function to be called after the action (refresh the grid etc)
     *@param 2. deviceFetcher = function that returns the list of device records
     *@class Zenoss.DeviceActionMenu
     *@extends Ext.Button
     **/
    Ext.define("Zenoss.DeviceActionMenu", {
        alias: ['widget.deviceactionmenu'],
        extend: "Ext.Button",
        constructor: function(config) {
            config = config || {};
            if (!config.saveHandler) {
                throw "Device Action Menu did not receive a save handler";
            }
            if (!config.deviceFetcher) {
                throw "Device Action Menu did not receive a device fetcher";
            }
            var fetcher = config.deviceFetcher,
                saveHandler = config.saveHandler,
                REMOTE = Zenoss.remote.DeviceRouter;

            Ext.applyIf(config, {
                text: _t('Actions'),
                disabled: Zenoss.Security.doesNotHavePermission('Manage Device') &&
                          Zenoss.Security.doesNotHavePermission('Change Device Production State'),
                menu: {
                    items: [
                        new Zenoss.Action({
                            text: _t('Lock Devices') + '...',
                            iconCls: 'lock',
                            permission: 'Change Device',
                            handler: function() {
                            var sel = fetcher().uids,
                                funcs = {'fetcher': fetcher, 'saveHandler': saveHandler, 'REMOTE': REMOTE};

                                if(sel.length === 0){
                                    Zenoss.message.warning(_t("Please select 1 or more devices to lock"));
                                    return;
                                }
                                if(sel.length > 1){
                                    showComponentLockingDialog(_t("To view locked state, select one device at a time."), "", funcs);
                                }else{
                                    REMOTE.getInfo({
                                        uid: fetcher().uids[0],
                                        keys: ['locking']
                                    }, function(result){
                                        if (result.success) {
                                            showComponentLockingDialog("", result.data.locking, funcs);
                                        }
                                    });
                                }

                            }
                        }),
                        new Zenoss.Action({
                            text: _t('Reset IP'),
                            iconCls: 'set',
                            permission: 'Change Device',
                            handler: function(){
                                new Zenoss.dialog.SimpleMessageDialog({
                                    message: Ext.String.format(_t('Are you sure you want to reset the IP addresses of these devices to the results of a DNS lookup?')),
                                    title: _t('Reset IP'),
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        text: _t('OK'),
                                        handler: function() {
                                            REMOTE.resetIp(fetcher(), saveHandler);
                                        }
                                    }, {
                                        xtype: 'DialogButton',
                                        text: _t('Cancel')
                                    }]
                                }).show();
                            }
                        }),
                        /*
                         * Currently causes a bus error on multiple devices: http://dev.zenoss.org/trac/ticket/6142
                         * Commenting out until that is fixed
                         *
                        resetCommunity: new Zenoss.Action({
                            text: _t('Reset Community'),
                            iconCls: 'set',
                            permission: 'Change Device',
                            handler: function(){
                                Ext.Msg.show({
                                    title: _t('Reset Community'),
                                    msg: _t('Are you sure you want to reset the SNMP '+
                                            'community strings of these devices?'),
                                    buttons: Ext.Msg.YESNO,
                                    fn: function(r) {
                                        switch(r) {
                                          case 'no':
                                            break;
                                          case 'yes':
                                            REMOTE.resetCommunity(gridOptions(), resetGrid);
                                            break;
                                        default:
                                            break;
                                        }
                                    }
                                });
                            }
                        }),
                        */
                        new Zenoss.Action({
                            text: _t('Set Production State')+'...',
                            iconCls: 'set',
                            permission: 'Change Device Production State',
                            handler: function(){
                                var win = new Zenoss.FormDialog({
                                    title: _t('Set Production State'),
                                    modal: true,
                                    width: 310,
                                    height: 150,
                                    items: [{
                                        xtype: 'ProductionStateCombo',
                                        fieldLabel: _t('Select a production state'),
                                        id: 'prodstate',
                                        listeners: {
                                            'select': function(){
                                                Ext.getCmp('prodstateok').enable();
                                            }
                                        }
                                    }],
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        id: 'prodstateok',
                                        disabled: true,
                                        text: _t('OK'),
                                        handler: function(){
                                            var opts = Ext.apply(fetcher(), {
                                                prodState:Ext.getCmp('prodstate').getValue()
                                            });
                                            REMOTE.setProductionState(opts, saveHandler);
                                        }
                                    }, Zenoss.dialog.CANCEL
                                             ]
                                });
                                win.show();
                            }
                        }),
                        new Zenoss.Action({
                            text: _t('Set Priority')+'...',
                            iconCls: 'set',
                            permission: 'Change Device',
                            handler: function(){
                                var win = new Zenoss.FormDialog({
                                    title: _t('Set Priority'),
                                    modal: true,
                                    width: 310,
                                    height: 150,
                                    items: [{
                                        xtype: 'PriorityCombo',
                                        id: 'device_action_priority',
                                        fieldLabel: _t('Select a priority'),
                                        listeners: {
                                            'select': function(){
                                                Ext.getCmp('priorityok').enable();
                                            }
                                        }
                                    }],
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        id: 'priorityok',
                                        disabled: true,
                                        text: _t('OK'),
                                        handler: function(){
                                            var opts = Ext.apply(fetcher(), {
                                                priority: Ext.getCmp('device_action_priority').getValue()
                                            });
                                            REMOTE.setPriority(opts, saveHandler);
                                        }
                                    }, Zenoss.dialog.CANCEL
                                             ]
                                });
                                win.show();
                            }
                        }),
                        new Zenoss.Action({
                            text: _t('Set Collector') + '...',
                            iconCls: 'set',
                            permission: 'Change Device',
                            handler: function(){
                                var win = new Zenoss.FormDialog({
                                    title: _t('Set Collector'),
                                    modal: true,
                                    width: 310,
                                    height: 180,
                                    items: [{
                                        xtype: 'combo',
                                        fieldLabel: _t('Select a collector'),
                                        id: 'collector',
                                        queryMode: 'local',
                                        store: new Ext.data.ArrayStore({
                                            data: Zenoss.env.COLLECTORS,
                                            fields: ['name']
                                        }),
                                        valueField: 'name',
                                        displayField: 'name',
                                        forceSelection: true,
                                        editable: false,
                                        listeners: {
                                            'select': function(){
                                                Ext.getCmp('collectorok').enable();
                                            }
                                        }
                                    }],
                                    buttons: [{
                                        xtype: 'DialogButton',
                                        id: 'collectorok',
                                        disabled: true,
                                        text: _t('OK'),
                                        handler: function(){
                                            var opts = Ext.apply(fetcher(), {
                                                collector: Ext.getCmp('collector').getValue()
                                            });
                                            opts.asynchronous = Zenoss.settings.deviceMoveIsAsync(opts.uids);
                                            REMOTE.setCollector(opts, saveHandler);
                                        }
                                    }, Zenoss.dialog.CANCEL
                                             ]
                                });
                                win.show();
                            }
                        })]
                }
            });
            Zenoss.DeviceActionMenu.superclass.constructor.apply(this, arguments);
        }
    });



    // Extension point for adding new devices for zenpacks
    Zenoss.customDeviceAdder = {};
    Zenoss.registerAddDeviceMethod = function(uid, fn ) {
        Zenoss.customDeviceAdder[uid] = fn;
    };
    Zenoss.getCustomDeviceAdder = function(uid) {
        return Zenoss.customDeviceAdder[uid];
    };

})(); // end of function namespace scoping
