/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function() {

Ext.define('Zenoss.software.SoftwareGridPanel', {
    extend: 'Ext.grid.GridPanel',
    alias: ['widget.softwarepanel'],
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            store: Ext.create('Zenoss.software.SoftwareStore', {}),
            columns: [{
                dataIndex: 'manufacturer',
                width: 280,
                header: _t('Manufacturer'),
                renderer: function(v) {
                    return Ext.String.format('<a href="{0}">{1}</a>', v.uid, v.name);
                }
            }, {
                dataIndex: 'namelink',
                header: _t('Name'),
                width: 340,
                sortable: true,
                renderer: function(v, col, record) {
                    return Ext.String.format('<a href="{0}">{1}</a>', v, record.data.name);
                }

            }, {
                flex: 1,
                dataIndex: 'installdate',
                header: _t('Install Date')
            }]
        });
        this.callParent([config]);
    },
    refresh: function() {
        this.setContext(this.contextUid);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.getStore().load({
            params: {uid: uid, keys: ['uid', 'manufacturer', 'name', 'namelink', 'installdate']}
        });
    }
});

Ext.define('Zenoss.software.SoftwareModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
            {name: 'manufacturer'},
            {name: 'name'},
            {name: 'namelink'},
            {name: 'installdate'}
    ]
});

Ext.define("Zenoss.software.SoftwareStore", {
    extend: "Zenoss.NonPaginatedStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.software.SoftwareModel',
            initialSortColumn: "name",
            directFn: Zenoss.remote.DeviceRouter.getSoftware,
            root: 'data'
        });
        this.callParent(arguments);
    }
});


})();
