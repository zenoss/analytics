/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


/* package level */
(function() {

    var ZD = Ext.ns('Zenoss.devices');

    Ext.define("Zenoss.form.SmartCombo", {
        extend: "Ext.form.ComboBox",
        alias: ['widget.smartcombo'],
        constructor: function(config) {
            config = Ext.applyIf(config || {}, {
                queryMode: config.autoLoad !== false ? 'local':'remote',
                store: new Zenoss.NonPaginatedStore({
                    directFn: config.directFn,
                    root: config.root || 'data',
                    model: config.model || 'Zenoss.model.NameValue',
                    initialSortColumn: config.initialSortColumn || 'name',
                    initialSortDirection: config.initialSortDirection || 'ASC'
                }),
                valueField: 'value',
                displayField: 'name',
                forceSelection: true,
                editable: false,
                autoSelect: true,
                selectOnFocus: false,
                triggerAction: 'all'
            });
            this.callParent([config]);
            if (this.autoLoad!==false) {
                this.getStore().load();
            }
        },
        getValue: function() {
            return this.callParent(arguments) || this.getRawValue();
        },
        getStore: function() {
            return this.store;
        }
    });

    Ext.define("Zenoss.model.ValueIntModel", {
        extend: 'Ext.data.Model',
        idProperty: 'name',
        fields: [
            { name: 'name', type: 'string'},
            { name: 'value', type: 'int'}
        ]
    });

    Ext.define("Zenoss.devices.PriorityCombo", {
        extend:"Zenoss.form.SmartCombo",
        alias: ['widget.PriorityCombo'],
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                directFn: Zenoss.remote.DeviceRouter.getPriorities,
                cls: 'prioritycombo',
                model: 'Zenoss.model.ValueIntModel',
                initialSortColumn: 'value',
                initialSortDirection: 'DESC'

            });
            this.callParent([config]);
        },
        getValue: function() {
            // This method is being overridden because the check in SmartCombo
            // will not allow zero as a value; it will fallback and send the
            // raw value, which for Priority is the string "Trivial".
            var result = this.callParent(arguments);
            if (Ext.isString(result)) {
                Zenoss.env.initPriorities();
                Ext.each(Zenoss.env.PRIORITIES, function(item) {
                    if (item.name === result) {
                        result = item.value;
                        return false; // break
                    }
                });
            }
            return result;
        }
    });



    Ext.define("Zenoss.devices.DevicePriorityMultiselectMenu", {
        extend:"Zenoss.MultiselectMenu",
        alias: ['widget.multiselect-devicepriority'],
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                text:'...',
                cls: 'x-btn x-btn-default-toolbar-small',
                source: Zenoss.env.priorities,
                defaultValues: []
            });
            ZD.DevicePriorityMultiselectMenu.superclass.constructor.call(this, config);
        }
    });


    Ext.define("Zenoss.devices.ProductionStateCombo", {
        extend:"Zenoss.form.SmartCombo",
        alias: ['widget.ProductionStateCombo'],
        constructor: function(config) {
            config = Ext.apply(config || {}, {
                directFn: Zenoss.remote.DeviceRouter.getProductionStates,
                model: 'Zenoss.model.ValueIntModel',
                initialSortColumn: 'value',
                initialSortDirection: 'DESC'
            });
            this.callParent([config]);
        }
    });


    Ext.define("Zenoss.devices.DeviceStatusMultiselectMenu", {
        extend:"Zenoss.MultiselectMenu",
        alias: ['widget.multiselect-devicestatus'],
        constructor: function(config) {
            var defaults = [];
            config = Ext.apply(config || {}, {
                text: '...',
                cls: 'x-btn x-btn-default-toolbar-small',
                source: [
                    {name: 'Up', value: true},
                    {name: 'Down', value: false},
                    {name: 'Unknown', value: null},
                ],
                defaultValues: defaults
            });
            this.callParent([config]);
        }
    });


    Ext.define("Zenoss.devices.ProductionStateMultiselectMenu", {
        extend:"Zenoss.MultiselectMenu",
        alias: ['widget.multiselect-prodstate'],
        constructor: function(config) {
            var defaults = [];
            if (Ext.isDefined(Zenoss.env.PRODUCTION_STATES)) {
                defaults.Array = Ext.pluck(Zenoss.env.PRODUCTION_STATES, 'value');
            }
            config = Ext.apply(config || {}, {
                text:'...',
                cls: 'x-btn x-btn-default-toolbar-small',
                source: Zenoss.env.productionStates,
                defaultValues: defaults
            });
            this.callParent([config]);
        }
    });


    Ext.define("Zenoss.devices.ManufacturerDataStore", {
        extend:"Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            var router = config.router || Zenoss.remote.DeviceRouter;
            Ext.applyIf(config, {
                root: 'manufacturers',
                totalProperty: 'totalCount',
                initialSortColumn: 'name',
                model: 'Zenoss.model.Name',
                directFn: router.getManufacturerNames
            });
            this.callParent([config]);
        }
    });

    Ext.define("Zenoss.devices.OSProductDataStore", {
        extend:"Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            var router = config.router || Zenoss.remote.DeviceRouter;
            Ext.applyIf(config, {
                root: 'productNames',
                totalProperty: 'totalCount',
                model: 'Zenoss.model.Name',
                initialSortColumn: 'name',
                directFn: router.getOSProductNames
            });
            this.callParent([config]);
        }
    });

    Ext.define("Zenoss.devices.HWProductDataStore", {
        extend:"Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            var router = config.router || Zenoss.remote.DeviceRouter;
            Ext.applyIf(config, {
                root: 'productNames',
                totalProperty: 'totalCount',
                model: 'Zenoss.model.Name',
                initialSortColumn: 'name',
                directFn: router.getHardwareProductNames
            });
            this.callParent([config]);
        }
    });

    Ext.define("Zenoss.devices.ManufacturerCombo", {
        extend:"Zenoss.form.SmartCombo",
        alias: ['widget.manufacturercombo'],
        constructor: function(config) {
            var store = (config||{}).store || new ZD.ManufacturerDataStore();
            config = Ext.applyIf(config||{}, {
                store: store,
                width: 160,
                displayField: 'name',
                valueField: 'name'
            });
            this.callParent([config]);
        }
    });


    Ext.define("Zenoss.devices.ProductCombo", {
        extend:"Zenoss.form.SmartCombo",
        alias: ['widget.productcombo'],
        constructor: function(config) {
            var manufacturer = config.manufacturer || "",
                prodType = config.prodType || 'OS',
                store = (config||{}).store ||
                    prodType==='OS' ? new ZD.OSProductDataStore() : new ZD.HWProductDataStore();
            store.setBaseParam('manufacturer', manufacturer);
            config = Ext.applyIf(config||{}, {
                store: store,
                displayField: 'name',
                valueField: 'name',
                width: 160,
                queryMode: 'remote'
            });
            this.callParent([config]);
        }
    });

}());
