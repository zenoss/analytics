/* jshint boss:true */
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

(function() {
    Ext.ns('Zenoss.property.form.field', 'Zenoss.property.grid.column', 'Zenoss.property.custom.dialog');
    Ext.ns('Zenoss.cproperties');

    Ext.define('Zenoss.property.form.field.Lines', {
        extend: 'Ext.form.field.TextArea',
        alias: ['widget.lines', 'widget.linesfield'],
        setValue: function(value) {
            var fieldValue = Ext.isArray(value) ? value.join('\n') : value;
            return this.callParent([fieldValue]);
        },
        getValue: function() {
            var raw = this.getRawValue();
            return Ext.Array.map(raw.split('\n'), function(s) { return Ext.String.trim(s);});
        },
        getSubmitValue: function() {
            return this.getValue();
        }
    });

    /**
     * Model and field definitions for z and c properties.
     */
    Ext.define('Zenoss.property.Model', {
        extend: 'Ext.data.Model',
        fields: [
            {name: 'uid'},   // path to where property lives, e.g. /zport/dmd/Devices
            {name: 'id'},    // property ID
            {name: 'label'}, // A title for the property
            {name: 'description'},
            {name: 'category'},  // only valid for 'z' properties
            {name: 'type'},
            {name: 'select_variable'},  // Only valid if 'type' is 'selection'
            {name: 'value'},
            {
                name: 'valueAsString',
                persist: false,
                convert: function(value, record) {
                    var value = record.get('value');
                    switch (record.get('type')) {
                        case 'date':
                            return Zenoss.render.date(value);
                        case 'lines':
                            return (value) ? value.join(', ') : '';
                        default:
                            return value;
                    }
                }
            },
            {name: 'islocal', persist: false}
        ]
    });

    /**
     * Allow zenpack authors to register custom cproperty
     * editors.
     **/
    Zenoss.cproperties.registerCPropertyType = function(id, config){
        Ext.data.StoreManager.lookup('propertyTypeFields').add([[id, config]]);
    };

    // Array of records for the propertyTypeFields store.
    var propertyTypeFields = [
        ['int',       { xtype: 'numberfield', allowDecimals: false }],
        ['float',     { xtype: 'numberfield' }],
        ['long',      { xtype: 'numberfield' }],
        ['date',      { xtype: 'zendatetimefield' }],
        ['string',    { xtype: 'textfield' }],
        ['lines',     { xtype: 'lines' }],
        ['boolean',   { xtype: 'checkbox' }],
        ['password',  { xtype: 'password' }],
        ['selection', {
            xtype: 'panel',
            layout: 'anchor',
            defaults: {
                anchor: "100%"
            },
            reset: function() {
                var data = this.down("#selectionValue"),
                    source = this.down("#selectionSource");
                data.store.removeAll();
                data.reset();
                data.setDisabled(true);
                source.reset();
            },
            items: [{
                xtype: 'combo',
                itemId: 'selectionSource',
                name: 'select_variable',
                fieldLabel: 'Property to select from',
                store: Ext.create("Zenoss.DirectStore", {
                    model: 'Zenoss.property.Model',
                    directFn: Zenoss.remote.PropertiesRouter.query,
                    autoLoad: true,
                    baseParams: {
                        uid: "/zport/dmd/Devices",
                        constraints: {type: "lines"}
                    }
                }),
                displayField: 'id',
                allowBlank: false,
                forceSelection: true,
                listeners: {
                    change: function(srcCombo, value) {
                        var record = srcCombo.findRecord('id', value),
                            lines = (record) ? record.get("value").map(function(i) { return [i]; }) : null,
                            valueCombo = srcCombo.up("form").down("#selectionValue"),
                            selection = valueCombo.getValue();
                        if (lines) {
                            valueCombo.store.loadData(lines);
                        }
                    },
                    select: function(srcCombo, records) {
                        var record = records[0],
                            lines = record.get("value").map(function(i) { return [i]; }),
                            valueCombo = srcCombo.up("form").down("#selectionValue"),
                            selection = valueCombo.getValue();
                        if (selection === null || lines.indexOf(selection) == -1) {
                            valueCombo.setValue(valueCombo.store.getAt(0));
                        }
                    }
                }
            }, {
                xtype: 'combo',
                itemId: 'selectionValue',
                name: 'value',
                fieldLabel: 'Value',
                margin: '10 0 0 0',
                disabled: true,
                queryMode: 'local',
                store: [],
                allowBlank: true,
                forceSelection: true,
                listeners: {
                    change: function(combo, value) {
                        combo.setDisabled(false);
                    }
                }
            }]
        }]
    ];

    Ext.define('Zenoss.property.TypeFieldModel', {
        extend: 'Ext.data.Model',
        fields: ['type', 'field'],
        idProperty: 'type'
    });

    Ext.create('Ext.data.ArrayStore', {
        model: 'Zenoss.property.TypeFieldModel',
        storeId: 'propertyTypeFields',
        listeners: {
            add: function(store, records, index) {
                store.totalCount += records.length;
            }
        },
        data: propertyTypeFields
    });

    Ext.define('Zenoss.property.Proxy', {
        extend: 'Ext.data.proxy.Direct',
        simpleSortMode: true,
        directFn: Zenoss.remote.PropertiesRouter.query,
        reader: {
            root: 'data',
            totalProperty: 'totalCount'
        }
    });

    Ext.define('Zenoss.property.Store', {
        extend: 'Zenoss.DirectStore',
        alias: 'store.zenzproperties',
        model: 'Zenoss.property.Model',
        constructor: function(config) {
            config = config || {}
            Ext.applyIf(config, {
                initialSortColumn: config.initialSortColumn || 'id',
                pageSize: config.pageSize || 300,
            });
            var proppath = config.uid || '/zport/dmd/Devices';
            this.callParent([config]);
            this.setProxy(Ext.create('Zenoss.property.Proxy', {
                extraParams: {
                    constraints: { idPrefix: 'z' },
                    uid: proppath
                }
            }));
        }
    });

    Ext.define('Zenoss.property.custom.Store', {
        extend: 'Zenoss.DirectStore',
        alias: 'store.zencproperties',
        model: 'Zenoss.property.Model',
        constructor: function(config) {
            config = config || {}
            Ext.applyIf(config, {
                initialSortColumn: config.initialSortColumn || 'id',
                pageSize: config.pageSize || 300,
            });
            var proppath = config.uid || '/zport/dmd/Devices';
            this.callParent([config]);
            this.setProxy(Ext.create('Zenoss.property.Proxy', {
                extraParams: {
                    constraints: { idPrefix: 'c' },
                    uid: proppath
                }
            }));
        }
    });

    Ext.define('Zenoss.property.custom.dialog.Add', {
        extend: 'Zenoss.dialog.Form',
        alias: ['widget.addcustompropertydialog'],
        constructor: function(config) {
            var handler = config.handler || function() {};
            this.callParent([{
                title: _t('Add Custom Config Property'),
                autoHeight: true,
                minHeight: 360,
                width: 480,
                submitHandler: function(form) {
                    var values = form.getValues();
                    values.uid = "/zport/dmd/Devices";
                    handler(values);
                },
                form: {
                    layout: 'anchor',
                    defaults: {
                        padding: '0 0 10 0',
                        margin: 0,
                        anchor: '100%'
                    },
                    items: [{
                        xtype: 'textfield',
                        name: 'id',
                        fieldLabel: _t('Name'),
                        value: '',
                        emptyText: 'cPropertyName',
                        allowBlank: false,
                        regex: /^c[A-Z]/,
                        regexText: _t(
                            "Custom property name should start with a "
                            + "lower case \"c\" followed by a capital letter"
                        ),
                        msgTarget: 'under'
                    },{
                        xtype: 'textfield',
                        name: 'label',
                        fieldLabel: _t('Label')
                    },{
                        xtype: 'textareafield',
                        name: 'description',
                        fieldLabel: _t('Description')
                    },{
                        xtype: 'panel',
                        layout: 'hbox',
                        padding: 8,
                        style: {border: '1px solid #555'},
                        listeners: {
                            afterrender: function(e) {
                                var combo = this.up('panel').down('#typeSelector'),
                                    record = combo.getStore().getById('string');
                                combo.select(record.data.type);
                                combo.fireEvent('select', combo, [record]);
                            }
                        },
                        items: [{
                            xtype: 'combo',
                            itemId: 'typeSelector',
                            flex: 1,
                            name: 'type',
                            displayField: 'type',
                            allowBlank: false,
                            forceSelection: true,
                            fieldLabel: _t('Type'),
                            listeners: {
                                select: function(combo, record) {
                                    var layout = this.up('panel').down('#selectedTypePanel').getLayout(),
                                        oldItem = layout.getActiveItem();
                                    oldItem.setDisabled(true);
                                    oldItem.reset();
                                    layout.setActiveItem(combo.getValue());

                                    var newItem = layout.getActiveItem();
                                    newItem.setDisabled(false);
                                    if (newItem.down) {
                                        // For selection types, this disables the submit button until the
                                        // user selects a property.
                                        newItem.down('[name=value]').validate();
                                    } else {
                                        newItem.validate();
                                    }
                                }
                            },
                            store: Ext.data.StoreManager.lookup("propertyTypeFields")
                        }, {
                            xtype: 'panel',
                            itemId: 'selectedTypePanel',
                            padding: '0 0 0 10',
                            flex: 4,
                            layout: 'card',
                            deferredRender: true,
                            defaults: {
                                disabled: true,
                                allowBlank: true
                            },
                            items: (function() {
                                var items = [];
                                Ext.data.StoreManager.lookup("propertyTypeFields").each(function(record) {
                                    var config = Ext.clone(record.data.field);
                                    config = Ext.applyIf(config, {
                                        itemId: record.data.type,
                                        value: null,
                                        fieldLabel: 'Value',
                                        name: 'value',
                                        msgTarget: 'under'
                                    });
                                    items.push(config);
                                });
                                return items;
                            })()
                        }]
                    }]
                }
            }]);
        }
    });

    Ext.define('Zenoss.property.custom.dialog.Edit', {
        extend: 'Zenoss.dialog.Form',
        alias: ['widget.editcustompropertydialog'],
        constructor: function(config) {
            var uid = config.uid || '/zport/dmd/Devices',
                fieldConfig = config.fieldConfig || {},
                handler = config.handler || function() {};
            this.callParent([{
                title: _t('Edit Custom Config Property'),
                minWidth: 480,
                submitHandler: function(form) {
                    var values = form.getValues();
                    handler(values);
                },
                form: {
                    layout: 'anchor',
                    defaults: {
                        xtype: 'displayfield',
                        padding: '0 0 10 0',
                        margin: 0,
                        anchor: '100%'
                    },
                    fieldDefaults: {
                        labelAlign: 'left',
                        labelStyle: 'color:#aaccaa'
                    },
                    items: [{
                        name: 'id',
                        fieldLabel: 'Name',
                        submitValue: true
                    }, {
                        name: 'label',
                        fieldLabel: 'Label',
                    }, {
                        name: 'description',
                        fieldLabel: 'Description',
                    }, {
                        name: 'uid',
                        fieldLabel: 'Path',
                        renderer: Zenoss.render.PropertyPath
                    }, {
                        name: 'type',
                        fieldLabel: 'Type',
                    },
                    Ext.applyIf(Ext.clone(fieldConfig), {
                        name: 'value',
                        fieldLabel: 'Value',
                    }), {
                        name: 'uid',
                        fieldLabel: 'This change will be saved to this path',
                        labelAlign: 'top',
                        renderer: Zenoss.render.PropertyPath,
                        value: config.uid,
                        submitValue: true,
                    }]
                }
            }]);
        }
    });

    Ext.define("Zenoss.property.custom.Grid", {
        alias: ['widget.custompropertygrid'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};

            Zenoss.Security.onPermissionsChange(function() {
                this.setReadOnly(Zenoss.Security.doesNotHavePermission('zProperties Edit'));
            }, this);

            var addBtnConfig = {
                    xtype: 'button',
                    iconCls: 'add',
                    tooltip: _t('Add a Custom Property'),
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    handler: function(button) {
                        var grid = button.up("custompropertygrid");
                        Ext.create('Zenoss.property.custom.dialog.Add', {
                            handler: function(values) {
                                Zenoss.remote.PropertiesRouter.add(values, function(response) {
                                   if (response.success) {
                                       grid.refresh();
                                   }
                                });
                            }
                        }).show();
                    }
                },
                editBtnConfig = {
                    xtype: 'button',
                    itemId: "edit_property_value",
                    iconCls: 'customize',
                    tooltip: _t('Edit selected Custom Property'),
                    disabled: true,
                    handler: function(button) {
                        var grid = button.up("custompropertygrid"),
                            selected = grid.getSelectionModel().getSelection(),
                            record = (!Ext.isEmpty(selected)) ? selected[0] : null;
                        if (record === null) {
                            return;
                        }
                        var s = Ext.data.StoreManager.lookup('propertyTypeFields'),
                            fieldConfig = s.getById(record.data.type).data.field,
                            dialog = Ext.create('Zenoss.property.custom.dialog.Edit', {
                                uid: grid.uid,
                                fieldConfig: fieldConfig,
                                handler: function(values) {
                                    Zenoss.remote.PropertiesRouter.update(values, function(response) {
                                        if (response.success) {
                                            grid.refresh();
                                        }
                                    });
                                }
                            });
                        dialog.down('form').loadRecord(record);
                        dialog.show();
                    }
                },
                refreshBtnConfig = {
                    xtype: 'button',
                    itemId: 'refresh_property_grid',
                    iconCls: 'refresh',
                    tooltip: _t('Refresh'),
                    handler: function(button) {
                        button.up("custompropertygrid").refresh();
                    }
                },
                deleteBtnConfig = {
                    xtype: 'button',
                    itemId: 'delete_property',
                    iconCls: 'delete',
                    tooltip: _t('Delete selected custom properties'),
                    disabled: true,
                    handler: function(button) {
                        var grid = button.up("custompropertygrid"),
                            selected = grid.getSelectionModel().getSelection();
                        if (Ext.isEmpty(selected)) {
                            return;
                        }
                        var title = 'Propert' + ((selected.length == 1) ? 'y' : 'ies'),
                            names = selected.map(function(item) { return item.data['id']; });
                        Ext.create('Zenoss.dialog.SimpleMessageDialog', {
                            title: _t('Delete Local ' + title),
                            message: function() {
                                return new Ext.XTemplate(
                                    '<p style="margin-bottom: 10px">' +
                                        'Are you sure you want to delete the following Custom {title}?' +
                                    '</p>' +
                                    '<ul style="margin-left: 10px; margin-bottom: 10px">' +
                                        '<tpl for="names"><li>{.}</li></tpl>' +
                                    '</ul>'
                                ).applyTemplate({
                                    title: title,
                                    names: names
                                })
                            }(),
                            buttons: [{
                                xtype: 'DialogButton',
                                text: _t('OK'),
                                handler: function() {
                                    Zenoss.remote.PropertiesRouter.remove({
                                        uid: grid.uid,
                                        properties: names
                                    },
                                    function(response) {
                                        if (response.success) {
                                            grid.refresh();
                                        }
                                    });
                                }
                            }, {
                                xtype: 'DialogButton',
                                text: _t('Cancel')
                            }]
                        }).show();
                    }
                };

            Ext.applyIf(config, {
                stateId: config.id || 'custom_property_grid',
                stateful: true,
                tbar: [addBtnConfig, editBtnConfig, refreshBtnConfig, deleteBtnConfig],
                store: Ext.create('store.zencproperties', {
                    pageSize: 300,
                    uid: this.uid
                }),
                selModel: {
                    xtype: 'rowmodel',
                    mode: 'MULTI'
                },
                columns: {
                    defaults: {
                        sortable: true
                    },
                    items: [{
                        header: _t("Name"),
                        dataIndex: 'id',
                        width: 150
                    }, {
                        header: _t("Label"),
                        dataIndex: 'label',
                        width: 150
                    }, {
                        header: _t('Description'),
                        dataIndex: 'description',
                        width: 200
                    }, {
                        header: _t('Value'),
                        dataIndex: 'valueAsString',
                        flex: 1
                    }, {
                        header: _t('Path'),
                        dataIndex: 'uid',
                        width: 90,
                        renderer: Zenoss.render.PropertyPath
                    }, {
                        header: _t('Type'),
                        dataIndex: 'type',
                        width: 60
                    }, {
                        header: _t('Is Local'),
                        dataIndex: 'islocal',
                        width: 50,
                        filter: false,
                        renderer: function(value) {
                            return (value) ? 'Yes' : '';
                        }
                    }]
                }
            });
            this.callParent(arguments);
        },
        listeners: {
            selectionchange: function(selectionModel, selected) {
                var tbar = this.getDockedItems("toolbar[dock='top']")[0],
                    editBtn = tbar.down("[itemId=edit_property_value]"),
                    delBtn = tbar.down("[itemId=delete_property]");
                editBtn.setDisabled((selected.length != 1));
                if (selected.length > 0) {
                    delBtn.setDisabled(!Ext.Array.every(selected, function(row) { return row.data.islocal; }));
                } else {
                    delBtn.setDisabled(true);
                }
            },
            itemdblclick: function(gridview, row, e) {
                var btn = this.down('[itemId=edit_property_value]');
                if (!btn.isDisabled()) {
                    btn.handler(btn);
                }
            }
        },
        setReadOnly: function(value) {
            var btns = this.query("button");
            Ext.each(btns, function(btn) {
                if (btn.itemId != 'refresh_property_grid') {
                    btn.setVisible(!value);
                }
            });
            this.getSelectionModel().setLocked(value);
        }
    });

    Ext.define("Zenoss.property.custom.Panel", {
        alias:['widget.custompropertypanel'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};
            this.gridId = "custompropgridId";
            Ext.applyIf(config, {
                layout: 'fit',
                autoScroll: 'y',
                items: [{
                    id: this.gridId,
                    xtype: "custompropertygrid",
                    ref: 'customGrid',
                    displayFilters: config.displayFilters
                }]
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            Ext.getCmp(this.gridId).setContext(uid);
        }
    });

})();
