/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    Ext.define('Zenoss.quickstart.Wizard.model.JobRecord', {
        extend: 'Ext.data.Model',
        fields: [
            {name: 'uuid',  type: 'string'},
            {name: 'status',  type: 'string'},
            {name: 'networks',  type: 'array'},
            {name: 'collector',  type: 'string'},
            {name: 'zProperties',  type: 'object'},
            {name: 'joblog',  type: 'string'},
            {name: 'started',  type: 'string'},
            {name: 'scheduled',  type: 'string'},
            {name: 'finished',  type: 'string'},
            {name: 'logfile',  type: 'string'},
            {name: 'pendingDelete',  type: 'string', default: 'false'}
        ]
    });

    Ext.define('Zenoss.quickstart.Wizard.model.Discovery', {
        extend: 'Zenoss.quickstart.Wizard.model.JobRecord'
    });

    Ext.define('Zenoss.quickstart.Wizard.model.AddDeviceJobRecord', {
        extend: 'Ext.data.Model',
        fields: [
            {name: 'uuid',  type: 'string'},
            {name: 'deviceUid',  type: 'string'},
            {name: 'errors',  type: 'string'},
            {name: 'status',  type: 'string'},
            {name: 'deviceName',  type: 'string'},
            {name: 'deviceClass',  type: 'string'},
            {name: 'displayDeviceClass',  type: 'string'},
            {name: 'deviceType',  type: 'string'},
            {name: 'collector',  type: 'string'},
            {name: 'zProperties',  type: 'object'},
            {name: 'joblog',  type: 'string'},
            {name: 'started',  type: 'int'},
            {name: 'scheduled',  type: 'int'},
            {name: 'duration',  type: 'int'},
            {name: 'finished',  type: 'string'},
            {name: 'logfile',  type: 'string'},
            {name: 'pendingDelete',  type: 'boolean', default: 'false'}
        ]
    });

    /**
     * @class Zenoss.quickstart.Wizard.DiscoveryStore
     * @extend Zenoss.DirectStore
     * Direct store for loading discovery records
     */
    Ext.define("Zenoss.quickstart.Wizard.DiscoveryStore", {
        extend: "Ext.data.Store",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.quickstart.Wizard.model.Discovery',
                initialSortColumn: "ip_range",
                data: {
                    items: []
                },
                proxy: {
                    type: 'memory',
                    reader: {
                        type: 'json',
                        root: 'items'
                    }
                }
            });
            this.callParent(arguments);
        }
    });

    /**
     * @class Zenoss.quickstart.Wizard.AddDeviceStore
     * @extend Zenoss.DirectStore
     * Direct store for loading Add device job records
     */
    Ext.define("Zenoss.quickstart.Wizard.AddDeviceStore", {
        extend: "Ext.data.Store",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.quickstart.Wizard.model.AddDeviceJobRecord',
                data: {
                    items: []
                },
                proxy: {
                    type: 'memory',
                    reader: {
                        type: 'json',
                        root: 'items'
                    }
                }
            });
            this.callParent(arguments);
        }
    });

    Ext.define('Zenoss.model.TypeStore', {
        extend: 'Ext.data.Model',
        fields: ['value',
                 'description',
                 'protocol', {
                     name: 'shortdescription',
                     convert: function(value, record){
                         if (!Ext.isEmpty(record.raw.protocol)) {
                             return Ext.String.format("{0} ({1})", record.raw.description, record.raw.protocol);
                         }
                         return record.raw.description;
                     }
                 }]
    });

    Ext.define('Zenoss.quickstart.Wizard.store.DeviceType', {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.model.TypeStore',
                directFn: Zenoss.remote.DeviceRouter.getDevTypes,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

}());
