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
        ConfigPropertyPanel,
        zpropertyConfigs = {};

    Ext.ns('Zenoss.zproperties');
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
        'zEventSeverity': {
            xtype: 'severity'
        },
        'zFailSeverity': {
            xtype: 'severity'
        },
        'zWinEventlogMinSeverity': {
            xtype: 'reverseseverity'
        }
    });

    /**
     * Allow zenpack authors to register custom zproperty
     * editors.
     **/
    Zenoss.zproperties.registerZPropertyType = function(id, config){
        zpropertyConfigs[id] = config;
    };


    function showEditConfigPropertyDialog(data, grid) {
        var handler, uid, config, editConfig, dialog, type;
        type = data.type;
        editConfig = {};

        // in case of drop down lists
        if (Ext.isArray(data.options) && data.options.length > 0 && type == 'string') {
            // make it a combo and the options is the store
            editConfig.store = data.options;
            Ext.apply( editConfig, zpropertyConfigs['options']);
        } else {
            // Try the specific property id, next the type and finally default to string
            Ext.apply( editConfig, zpropertyConfigs[data.id] || zpropertyConfigs[type] || zpropertyConfigs['string']);
        }

        // set the default values common to all configs
        Ext.applyIf(editConfig, {
            fieldLabel: _t('Value'),
            value: data.value,
            ref: 'editConfig',
            checked: data.value,
            name: data.id,
            width: 250
        });

        // lines come in as comma separated and should be saved as such
        if (type == 'lines' && Ext.isArray(editConfig.value)){
            editConfig.value = editConfig.value.join('\n');
        }

        handler = function() {
            // save the junk and reload
            var values = dialog.getForm().getForm().getValues(),
                value = values[data.id];
            if (type == 'lines') {
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
                    name: 'type',
                    ref: 'type',
                    fieldLabel: _t('Type'),
                    value: data.type
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
            {name: 'options'}
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
                    toolTip: _t('Customize'),
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
                        toolTip: _t('Refresh'),
                    ref: '../refreshButton',
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    handler: function(button) {
                        var grid = button.up("configpropertygrid");
                        grid.refresh();
                    }
                    },{
                        xtype: 'button',
                        ref: '../deleteButton',
                        toolTip: _t('Delete'),
                        text: _t('Delete Local Copy'),
                        handler: function(button) {
                            var grid = button.up("configpropertygrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();
                            if (Ext.isEmpty(selected)) {
                                return;
                            }

                            data = selected[0].data;
                            if (data.islocal && data.path == '/') {
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
                        flex: 1,
                        width: 180,
                        renderer: function(v, row, record) {
                            if (Zenoss.Security.doesNotHavePermission("zProperties Edit") &&
                                record.data.id == 'zSnmpCommunity') {
                                return "*******";
                            }
                            return Ext.htmlEncode(v);
                        },
                        sortable: false
                    },{
                        //id: 'path',
                        dataIndex: 'path',
                        header: _t('Path'),
                        width: 200,
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
            if (uid == '/zport/dmd/Devices'){
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



    var checkText = function(e){
        var uid = "/zport/dmd/Devices"; // to force it to apply to the root on every newly created prop

        var params = {
            uid: uid,
            zProperty: e
        };
        Zenoss.remote.PropertiesRouter.getZenProperty(params, function(response){
            if (response.success) {
                if (response.data.type == "lines"){
                    var lines = response.data.value, context = Zenoss.zproperties.configPropertyConfigs.state.context, formID;
                    context == "add" ? formID = "addCustomDialog" : formID = "editCustomDialog";
                    var c = Ext.getCmp(formID).getForm().getForm().getValues();

                    // we got a 'lines' item back. Lets save this so we can complete the users goal

                    var params = {
                        uid: uid,
                        id: c.name,
                        type: c.type,
                        label: c.description,
                        value: c.value
                    };
                    var addToCombo = function(){
                        // dump the array response.data.value into the combo box by breaking it up into an array of arrays
                        // for loadData to work
                        var combo = Ext.getCmp('linesCombo');
                        var data = [];
                        for (var i = 0; i < lines.length; i++){
                            data.push([lines[i]]);
                        }
                        combo.store.loadData(data);
                        // fire off a selection of the first item so it's obvious something happened
                        combo.setValue(combo.store.getAt('0'));
                    };
                    if (context == "add"){
                        Zenoss.remote.PropertiesRouter.addCustomProperty(params, function(response){
                            if (response.success) {
                                addToCombo();
                            }
                        });
                    }else{
                        addToCombo();
                    }

                }
            }
        });
    };




    Zenoss.zproperties.configPropertyConfigs = {};
    var propValText = _t("Value for Property Type:");
    Ext.apply(Zenoss.zproperties.configPropertyConfigs, {
        'state': {
            context: 'add'
        },
        'int': {
            xtype: 'numberfield',
            allowDecimals: false,
            fieldLabel: _t(propValText+' INT'),
            name: 'value'
        },
        'float': {
            xtype: 'numberfield',
            fieldLabel: _t(propValText+' FLOAT'),
            name: 'value'
        },
        'long': {
            xtype: 'numberfield',
            fieldLabel: _t(propValText+' LONG'),
            name: 'value'
        },
        'date': {
            xtype: 'datefield',
            name: 'value',
            fieldLabel: _t(propValText+' DATE')
        },
        'string': {
            xtype: 'textfield',
            name: 'value',
            fieldLabel: _t(propValText+' STRING'),
            width:220
        },
        'lines': {
            xtype: 'textarea',
            name: 'value',
            width: 220,
            height: 70,
            fieldLabel: _t(propValText+' LINES')
        },
        'boolean': {
            xtype: 'checkbox',
            name: 'value',
            fieldLabel: _t(propValText+' BOOLEAN')
        },
        'password': {
            xtype: 'password',
            name: 'value',
            width:220,
            fieldLabel: _t(propValText+' PASSWORD')
        },
        'selection': {
            xtype: 'panel',
            items: [
                {
                    xtype: 'panel',
                    width: 260,
                    layout: 'hbox',
                    items: [
                        {
                            xtype: 'textfield',
                            name: 'value',
                            id: 'linesSearchBox',
                            width:220,
                            margin: '0 0 5px 0',
                            fieldLabel: _t(propValText+' SELECTION')
                        },{
                            xtype: 'button',
                            iconCls: 'acknowledge',
                            listeners: {
                                afterrender: function(button){
                                    button.setTooltip(_t("Retrieve lines from property for selection"));
                                    if (Zenoss.zproperties.configPropertyConfigs.state.context == "add"){
                                        button.setTooltip(_t("Save new property and retrieve lines for selection"));
                                    }
                                }
                            },
                            margin: '17px 0 0 7px',
                            handler: function(button) {
                                var txt = Ext.getCmp('linesSearchBox').getValue(), uid;
                                if(Zenoss.zproperties.configPropertyConfigs.state.context == "add"){
                                    uid = Ext.getCmp('addCustomDialog').uid;
                                }else{
                                    uid = Ext.getCmp('editCustomDialog').uid;
                                }
                                if(txt != ""){
                                    checkText(txt, uid);
                                }else{
                                    Zenoss.message.info(_t('The "Lines" property type cannot be empty. Please enter a "Lines" custom property.'));
                                }
                            }
                        }
                        ]
                },{
                    xtype: 'combo',
                    name: 'selection',
                    queryMode:'local',
                    id: 'linesCombo',
                    store: [ 'none' ],
                    width:220
                }
            ]
        }
    });

    Zenoss.zproperties.showEditPropertyDialog = function(pkg) {
        var handler, config, editConfig, dialog;

        Zenoss.zproperties.configPropertyConfigs.state.context = "edit";
        // Try the specific property id, next the type and finall default to string
        editConfig = Zenoss.zproperties.configPropertyConfigs[pkg.name] || Zenoss.zproperties.configPropertyConfigs[pkg.type] || Zenoss.zproperties.configPropertyConfigs['string'];

        // in case of drop down lists
        if (Ext.isArray(pkg.options) && pkg.options.length > 0 && pkg.type == 'string') {
            // make it a combo and the options is the store
            editConfig = Zenoss.zproperties.configPropertyConfigs['options'];
            editConfig.store = pkg.options;
        }
        // set the default values common to all configs
        Ext.apply(editConfig, {
            fieldLabel: _t('Value'),
            value: pkg.value,
            ref: 'editConfig',
            checked: pkg.value,
            name: pkg.name
        });

        // lines come in as comma separated and should be saved as such
        if (pkg.type == 'lines' && Ext.isArray(editConfig.value)){
            editConfig.value = editConfig.value.join('\n');
        }

        handler = function() {
            // save the junk and reload
            var values = dialog.getForm().getForm().getValues(),
                value = values[pkg.name];
            if ((typeof values.applylocal) == "undefined"){
                values.applylocal = false;
            }
            if (pkg.type == 'lines') {
                if (value) {
                    // send back as an array separated by a new line
                    value = Ext.Array.map(value.split('\n'), function(s) {return Ext.String.trim(s);});
                } else {
                    // send back an empty list if nothing is set
                    value = [];
                }
            }
            // if this is a selection type, then the value is form.selection and not form.value
            if (pkg.type == 'selection'){
                value = values.selection;
            }
            var params = {
                uid: "/zport/dmd"+pkg.uid,
                zProperty: pkg.name,
                value: value
            };
            Zenoss.remote.PropertiesRouter.setZenProperty(params, function(response){
                if (response.success) {
                    pkg.grid.refresh();
                }
            });

        };
        var items = pkg.items;
        Ext.Array.splice( items, -1, 0, editConfig );
        var config = {
            submitHandler: handler,
            minHeight: pkg.minHeight,
            autoHeight: true,
            width: pkg.width,
            uid: pkg.uid,
            id: "editCustomDialog",
            title: _t('Edit Configuration Property'),
            items: items,
            keys: {}
        };

        dialog = new Zenoss.SmartFormDialog(config);

        if (Zenoss.Security.hasPermission('zProperties Edit')) {
            dialog.show();
        }
    };


})();
