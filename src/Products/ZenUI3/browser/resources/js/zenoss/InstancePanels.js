/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

Ext.ns('Zenoss');




/**
 * @class Zenoss.InstanceModel
 * @extends Ext.data.Model
 * Field definitions for the instances, matches up with the columns above
 **/
Ext.define('Zenoss.InstanceModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        {name: 'device'},
        {name: 'name'},
        {name: 'description'},
        {name: 'minProcessCount'},
        {name: 'maxProcessCount'},
        {name: 'monitored'},
        {name: 'pingStatus'}
    ]
});

/**
 * @class Zenoss.InstanceStore
 * @extend: Zenoss.DirectStore
 * Base store for the instances of things
 */
Ext.define("Zenoss.InstanceStore", {
    extend:"Zenoss.DirectStore",
    alias: ['widget.InstanceStore'],

    constructor: function(config) {
        Ext.applyIf(config, {
            model: 'Zenoss.InstanceModel',
            root: 'data',
            initialSortColumn: 'name'
        });
        this.callParent(arguments);
    }

});


Ext.define("Zenoss.SimpleInstanceGridPanel", {
    extend:"Zenoss.BaseGridPanel",
    alias: ['widget.SimpleInstanceGridPanel'],

    constructor: function(config) {
        var instanceColumns = [{
            id: 'instanceName',
            dataIndex: config.nameDataIndex || 'name',
            header: _t('Name'),
            flex: 0.25,
            width: 400
        },{
            id: 'device',
            dataIndex: 'device',
            flex: 0.75,
            header: _t('Device'),
            width: 200,
            sortable: false,
            renderer: function(device){
                return Zenoss.render.link(device.uid, undefined,
                                          device.name);
            }
        }, {
            dataIndex: 'minProcessCount',
            header: _t('Min Threshold'),
            width: 85,
            sortable: false,
            hidden: !config.showProcessCount
        }, {
            dataIndex: 'maxProcessCount',
            header: _t('Max Threshold'),
            width: 85,
            sortable: false,
            hidden: !config.showProcessCount
        }, {
            id: 'monitored',
            dataIndex: 'monitored',
            header: _t('Monitored'),
            width: 70,
            sortable: false
        }, {
            id: 'status',
            dataIndex: 'pingStatus',
            header: _t('Status'),
            renderer: Zenoss.render.pingStatus,
            width: 60,
            sortable: false
        }];

        Ext.applyIf(config, {
            columns: config.columns || instanceColumns,
            store: config.store || Ext.create('Zenoss.InstanceStore',{
                directFn: config.directFn,
                pageSize: config.pageSize
            }),
            selModel: config.sm || Ext.create('Zenoss.ExtraHooksSelectionModel', {
                mode: 'SINGLE'
            })
        });
        this.callParent(arguments);
    }
});

// supply the instances implementation in the config
Ext.define("Zenoss.SimpleCardPanel", {
    extend:"Ext.Panel",
    alias: ['widget.simplecardpanel'],

    constructor: function(config) {
        this.contextUid = null;
        Ext.applyIf(config, {
            layout: 'card',
            activeItem: 0,
            placeholder: {},
            height: Math.min(((Ext.getCmp('viewport').getHeight() - 75)/5)+30, 200),
            tbar: {
                xtype: 'consolebar',
                centerPanel: 'detail_panel',
                title: _t('Display: '),
                parentPanel: this,
                leftItems: [{
                    xtype: 'select',
                    ref: '../displaySelect',
                    queryMode: 'local',
                    value: config.instancesTitle,
                    store: [config.instancesTitle, _t('Configuration Properties')],
                    listeners: {
                        select: function(displaySelect, records) {
                            var index = records[0].index;
                            this.layout.setActiveItem(index);
                        },
                        scope: this
                    }
                }]
            },
            items: [
                config.instances,
            {
                xtype: 'configpropertypanel',
                id: 'config_property_panel',
                ref: 'zPropertyEdit',
                displayFilters: false,
                viewName: 'zPropertyEdit',
                listeners: config.zPropertyEditListeners
            }]
        });
        this.callParent(arguments);
    },
    setContext: function(uid) {
        // only reload our datastores if we are not collapsed
        this.contextUid = uid;
        if (!this.collapsed){
            this.loadInstances(uid);
        }
    },
    loadInstances: function(){
        if (!this.contextUid){
            return;
        }
        var contextUid = this.contextUid;
        // if we have not set our store since we last updated the
        // context uid update it now
        this.items.each(function(item) {
            item.setContext(contextUid);
        });
        this.contextUid = null;
    }

});

// has the instances used by the Netwoks, Processes and the two Services pages
Ext.define("Zenoss.InstanceCardPanel", {
    extend:"Zenoss.SimpleCardPanel",
    alias: ['widget.instancecardpanel'],

    constructor: function(config) {
        var gridId = config.gridId || Ext.id();

        Ext.applyIf(config, {
            instances: {
                xtype: 'SimpleInstanceGridPanel',
                id: gridId,
                bufferSize: config.bufferSize,
                nearLimit: config.nearLimit,
                directFn: config.router.getInstances,
                nameDataIndex: config.nameDataIndex || "name",
                columns: config.columns,
                sm: config.sm,
                store: config.store,
                showProcessCount: config.showProcessCount
            }
        });
        this.callParent(arguments);
        this.gridId = gridId;
    },
    getInstancesGrid: function() {
        return Ext.getCmp(this.gridId);
    }

});

})();
