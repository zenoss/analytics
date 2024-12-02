/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){
    var router = Zenoss.remote.PropertiesRouter,
        zpropertyConfigs = {};

    Ext.ns('Zenoss.zproperties');
    Zenoss.zproperties.inferZPropertyLabel= function(id) {
        var fieldLabel = id;
        // special case for vsphere end point.
        if (id.toLowerCase().indexOf('endpointhost')!== -1) {
            fieldLabel = _t("vSphere Endpoint Host");
        }else if (id.toLowerCase().indexOf('winkdc')!== -1) {
            fieldLabel = _t('AD Domain Controller');
        }else if (id.toLowerCase().indexOf('winscheme')!== -1) {
            fieldLabel = _t('Protocol (http/https)');
        }else if (id.toLowerCase().indexOf('user')!== -1) {
            fieldLabel = _t('Username');
        } else if (id.toLowerCase().indexOf('password')!== -1) {
            fieldLabel = _t('Password');
        } else if (id.toLowerCase().indexOf('snmpcomm')!== -1) {
            fieldLabel = _t('SNMP Community String');
        } else if (id.toLowerCase().indexOf('port')!== -1) {
            fieldLabel = _t('Port');
        } else if (id.toLowerCase().indexOf('ssl')!== -1) {
            fieldLabel = _t('Use SSL?');
        } else {
            fieldLabel = id;
        }
        return fieldLabel;
    };

    Ext.apply(zpropertyConfigs, {
        'int': {
            xtype: 'numberfield',
            allowDecimals: false,
            width: 100
        },
        'float': {
            xtype: 'numberfield',
            width: 100
        },
        'string': {
            xtype: 'textfield'
        },
        'lines': {
            xtype: 'textarea',
            resizable: true,
            width: 300
        },
        'severity': {
            xtype: 'severity'
        },
        'boolean': {
            xtype: 'checkbox'
        },
        'password': {
            xtype: 'password'
        },
        'options': {
            xtype: 'combo',
            editable: false,
            forceSelection: true,
            autoSelect: true,
            triggerAction: 'all',
            queryMode: 'local'
        },
        'zSnmpCommunity': {
            xtype: Zenoss.Security.doesNotHavePermission('zProperties Edit') ? 'password' : 'textfield'
        },
        'zEventAction': {
            xtype: 'eventaction'
        },
        'zEventSeverity': {
            xtype: 'defaultseverity'
        },
        'zFailSeverity': {
            xtype: 'severity'
        },
        'zFlappingSeverity': {
            xtype: 'severity'
        },
        'zFlappingThreshold': {
            xtype: 'numberfield',
            allowDecimals: false,
            width: 100
        },
        'zWinEventlogMinSeverity': {
            xtype: 'reverseseverity'
        },
        'zFlappingIntervalSeconds': {
            xtype: 'numberfield',
            allowDecimals: false,
            width: 100,
            minValue: 600
        }
    });

    /**
     * Allow zenpack authors to register custom zproperty
     * editors.
     **/
    Zenoss.zproperties.registerZPropertyType = function(id, config){
        zpropertyConfigs[id] = config;
    };

    Zenoss.zproperties.createZPropertyField = function(data) {
        var editConfig = {},
            type = data.type;
        // in case of drop down lists
        if (Ext.isArray(data.options) && data.options.length > 0 && type === 'string') {
            // make it a combo and the options is the store
            editConfig.store = data.options.map(function(value){
                var valueField = value,
                    displayField = value;

                // if the value is an empty string, indicate
                // with a special string
                if(value === ""){
                    displayField = "- None -";
                }
                return [valueField, displayField];
            });
            Ext.apply( editConfig, zpropertyConfigs['options']);
        } else {
            // Try the specific property id, next the type and finally default to string
            Ext.apply( editConfig, zpropertyConfigs[data.id] || zpropertyConfigs[type] || zpropertyConfigs['string']);
        }

        // set the default values common to all configs
        Ext.applyIf(editConfig, {
            fieldLabel: data.label || Zenoss.zproperties.inferZPropertyLabel(data.id),
            value: data.value,
            ref: 'editConfig',
            checked: data.value || data.valueAsString,
            name: data.id,
            width: 250
        });

        // lines come in as comma separated and should be saved as such
        if (type === 'lines' && Ext.isArray(editConfig.value)){
            editConfig.value = editConfig.value.join('\n');
        }
        return editConfig;
    };

    function showEditConfigPropertyDialog(data, grid) {
        var handler, config, editConfig, dialog, type;

        editConfig = Zenoss.zproperties.createZPropertyField(data);


        handler = function() {
            // save the junk and reload
            var values = dialog.getForm().getForm().getValues(),
                value = values[data.id];
            if (type === 'lines') {
                if (value) {
                    // send back as an array separated by a new line
                    value = Ext.Array.map(value.split('\n'), function(s) {return Ext.String.trim(s);});
                } else {
                    // send back an empty list if nothing is set
                    value = [];
                }
            }
            var params = {
                uid: grid.uid,
                zProperty: data.id,
                value: value
            };
            Zenoss.remote.PropertiesRouter.setZenProperty(params, function(response){
                if (response.success) {
                    grid.refresh();
                }
            });

        };

        // form config
        config = {
            submitHandler: handler,
            minHeight: 300,
            autoHeight: true,
            width: 500,
            title: _t('Edit Config Property'),
            listeners: {
                show: function() {
                    dialog.getForm().query("field[ref='editConfig']")[0].focus(true, 500);
                }
            },
            items: [{
                    xtype: 'displayfield',
                    name: 'name',
                    fieldLabel: _t('Name'),
                    value: data.id
                },{
                    xtype: 'displayfield',
                    name: 'path',
                    ref: 'path',
                    fieldLabel: _t('Path'),
                    value: data.path
                },{
                    xtype: 'displayfield',
                    name: 'description',
                    ref: 'description',
                    fieldLabel: _t('Description'),
                    value: data.description
                },{
                    xtype: 'displayfield',
                    name: 'type',
                    ref: 'type',
                    fieldLabel: _t('Type'),
                    value: data.type
                }, {
                    // spacer for metadata/value
                    height: 25,
                    xtype: 'container'
                },{
                    //Add hidden input fields to prevent password autocomplete
                    xtype: 'textfield',
                    hidden: true
                },{
                    xtype: 'password',
                    hidden: true
                }, editConfig
            ],
            // explicitly do not allow enter to submit the dialog
            keys: {

            }
        };
        dialog = new Zenoss.SmartFormDialog(config);

        if (Zenoss.Security.hasPermission('zProperties Edit')) {
            dialog.show();
        }
    }

    /**
     * @class Zenoss.ConfigProperty.Model
     * @extends Ext.data.Model
     * Field definitions for the Config Properties
     **/
    Ext.define('Zenoss.ConfigProperty.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: [
            {name: 'id'},
            {name: 'islocal'},
            {name: 'value'},
            {name: 'category'},
            {name: 'valueAsString'},
            {name: 'type'},
            {name: 'path'},
            {name: 'options'},
            {name: 'label'},
            {name: 'description'}
        ]
    });

    /**
     * @class Zenoss.ConfigProperty.Store
     * @extends Zenoss.DirectStore
     * Store for our configuration properties grid
     **/
    Ext.define("Zenoss.ConfigProperty.Store", {
        extend: "Zenoss.DirectStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.ConfigProperty.Model',
                initialSortColumn: 'id',
                pageSize: 300,
                directFn: Zenoss.remote.PropertiesRouter.getZenProperties
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.ConfigProperty.Grid", {
        alias: ['widget.configpropertygrid'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};

            Zenoss.Security.onPermissionsChange(function() {
                this.disableButtons(Zenoss.Security.doesNotHavePermission('zProperties Edit'));
            }, this);

            Ext.applyIf(config, {
                stateId: config.id || 'config_property_grid',
                sm: Ext.create('Zenoss.SingleRowSelectionModel', {}),
                tbar:[

                    {
                    xtype: 'button',
                    iconCls: 'customize',
                    tooltip: _t('Customize'),
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    ref: 'customizeButton',
                    handler: function(button) {
                        var grid = button.up("configpropertygrid"),
                            data,
                            selected = grid.getSelectionModel().getSelection();
                        if (Ext.isEmpty(selected)) {
                            return;
                        }
                        // single selection
                        data = selected[0].data;
                        showEditConfigPropertyDialog(data, grid);
                    }
                    }, {
                    xtype: 'button',
                    iconCls: 'refresh',
                    tooltip: _t('Refresh'),
                    ref: '../refreshButton',
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    handler: function(button) {
                        var grid = button.up("configpropertygrid");
                        grid.refresh();
                    }
                    },{
                        xtype: 'button',
                        ref: '../deleteButton',
                        tooltip: _t('Delete'),
                        text: _t('Delete Local Copy'),
                        handler: function(button) {
                            var grid = button.up("configpropertygrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();
                            if (Ext.isEmpty(selected)) {
                                return;
                            }

                            data = selected[0].data;
                            if (data.islocal && data.path === '/') {
                                Zenoss.message.info(_t('{0} can not be deleted from the root definition.'), data.id);
                                return;
                            }
                            if (!data.islocal){
                                Zenoss.message.info(_t('{0} is not defined locally'), data.id);
                                return;
                            }
                            new Zenoss.dialog.SimpleMessageDialog({
                                title: _t('Delete Local Property'),
                                message: Ext.String.format(_t("Are you sure you want to delete the local copy of {0}?"), data.id),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        if (grid.uid) {
                                            router.deleteZenProperty({
                                                uid: grid.uid,
                                                zProperty: data.id
                                            }, function(response){
                                                grid.refresh();
                                            });
                                        }
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
                        }
                    }
                ],
                store: Ext.create('Zenoss.ConfigProperty.Store', {
                }),
                columns: [{
                        header: _t("Is Local"),
                        dataIndex: 'islocal',
                        width: 60,
                        sortable: true,
                        filter: false,
                        renderer: function(value){
                            if (value) {
                                return 'Yes';
                            }
                            return '';
                        }
                    },{
                        dataIndex: 'category',
                        header: _t('Category'),
                        sortable: true,
                        renderer: function(value) {
                            return Ext.htmlEncode(value);
                        }
                    },{
                        dataIndex: 'id',
                        header: _t('Name'),
                        width: 200,
                        sortable: true,
                        renderer: function(value) {
                            return Ext.htmlEncode(value);
                        }
                    },{
                        dataIndex: 'valueAsString',
                        header: _t('Value'),
                        width: 150,
                        renderer: function(v, row, record) {
                            if (Zenoss.Security.doesNotHavePermission("zProperties Edit") &&
                                record.data.id === 'zSnmpCommunity') {
                                return "*******";
                            }
                            return Zenoss.render.zProperty(v, record);
                        },
                        sortable: false
                    },{
                        dataIndex: 'label',
                        header: _t('Label'),
                        width: 200,
                        sortable: true
                    },{
                        dataIndex: 'description',
                        header: _t('Description'),
                        flex: 1
                    },{
                        //id: 'path',
                        dataIndex: 'path',
                        header: _t('Path'),
                        width: 380,
                        sortable: true,
                        renderer: function(value) {
                            return Ext.htmlEncode(value);
                        }
                    }]
            });
            this.callParent(arguments);
            this.on('itemdblclick', this.onRowDblClick, this);
        },
        setContext: function(uid) {
            if (uid === '/zport/dmd/Devices'){
                this.deleteButton.setDisabled(true);
            } else {
                this.deleteButton.setDisabled(Zenoss.Security.doesNotHavePermission('zProperties Edit'));
            }

            this.uid = uid;
            // load the grid's store
            this.callParent(arguments);
        },
        onRowDblClick: function(grid, rowIndex, e) {
            var data,
                selected = this.getSelectionModel().getSelection();
            if (!selected) {
                return;
            }
            data = selected[0].data;
            showEditConfigPropertyDialog(data, this);
        },
        disableButtons: function(bool) {
            var btns = this.query("button");
            Ext.each(btns, function(btn){
                btn.setDisabled(bool);
            });
        }
    });

    Ext.define("Zenoss.form.ConfigPropertyPanel", {
        alias:['widget.configpropertypanel'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};
            this.gridId = Ext.id();
            Ext.applyIf(config, {
                layout: 'fit',
                autoScroll: 'y',
                height: 800,
                items: [{
                    id: this.gridId,
                    xtype: "configpropertygrid",
                    ref: 'configGrid',
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
