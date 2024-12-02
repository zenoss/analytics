/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

    var setComboFromData = function(response, combo){
            var data = [];
            for(var i=0;i < response.data.length; i++){
                data.push([response.data[i]]);
            }
            combo.store.loadData(data);
            combo.setValue(combo.store.getAt(-1));
            combo.setValue("Select a Configuration Property");
    };

    var checkComboIndex = function(){
        var combo = Ext.getCmp('propsCombo');
        var v = combo.getValue();
        var record = combo.findRecord(combo.valueField || combo.displayField, v);
        var index = combo.store.indexOf(record);
        // disable the edit box if the index is -1
        if(index === -1){
            Ext.getCmp('overriddenobjbase_grid1').disableButtons(true);
        }else{
            Ext.getCmp('overriddenobjbase_grid1').disableButtons(false);
        }
        return index;
    };

    var loadBaseGrid = function(uid){
        var combo = Ext.getCmp('propsCombo');
        Zenoss.remote.DeviceRouter.getOverriddenObjectsParent({uid:uid, propname:combo.value}, function(response){
            if (response.success) {
                Ext.getCmp('overriddenobjbase_grid1').getStore().loadData(response.data);
            }
        });
    };
    var loadOverriddenGrid = function(uid){
        var combo = Ext.getCmp('propsCombo'), relName = 'devices';
        // switch this based on where the grid is located or embeded

        var refreshit = function(data){
            Ext.getCmp('overriddenobjover_grid2').getStore().loadData(data);
        };

        /* If it finds /dmd/Events in the UID, then this is being used on the
         * Events Classes page and needs to get its overridden objects from
         * a different router method. Otherwise, we use the default devices method
         */
        if(uid.indexOf('/dmd/Events') !== -1) {
            relName = 'instances';
        }
        // default method for devices:
        Zenoss.remote.DeviceRouter.getOverriddenObjectsList({uid:uid, propname:combo.value, relName: relName}, function(response){
            if (response.success) {
                refreshit(response.data);
            }
        });

    };
    var onComboChange = function(uid){
        if(checkComboIndex() === -1) {
            return;
        }
        loadOverriddenGrid(uid);
        loadBaseGrid(uid);
    };

    function showEditCustPropertyDialog(data, grid){
        var s = Ext.data.StoreManager.lookup('propertyTypeFields'),
            fieldConfig = (data.proptype) ? s.getById(data.proptype).data.field : null;
        if (fieldConfig == null) {
            return;
        }
        var dialog = Ext.create('Zenoss.dialog.Form', {
                title: _t('Edit Configuration Property'),
                minWidth: 480,
                submitHandler: function(form) {
                    var values = form.getValues();
                    Zenoss.remote.PropertiesRouter.setZenProperty(values, function(response){
                        if (response.success) {
                            grid.refresh();
                        }
                    });
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
                        labelWidth: 50,
                        labelStyle: 'color:#aaccaa'
                    },
                    items: [{
                        name: 'zProperty',
                        fieldLabel: 'Name',
                        submitValue: true
                    }, {
                        name: 'uid',
                        fieldLabel: 'Path',
                        renderer: Zenoss.render.PropertyPath,
                        submitValue: true
                    }, {
                        name: 'type',
                        fieldLabel: 'Type',
                    },
                    Ext.applyIf(Ext.clone(fieldConfig), {
                        name: 'value',
                        fieldLabel: 'Value',
                    })]
                }
            }),
            record = { data: {
                zProperty: grid.up('overriddenobjects').down('combo').getValue(),
                uid: (function() {
                    var needPrefix = (data.devicelink.search(/^\/zport\/dmd/) === -1);
                    return (needPrefix) ? '/zport/dmd' + data.devicelink : data.devicelink;
                })(),
                type: data.proptype,
                value: data.props
            }};
        dialog.down('form').loadRecord(record);
        dialog.show();
    }


    /****************************************************** BASE OBJECT GRID ***************************/

    Ext.define("Zenoss.OverriddenObj_base.Grid", {
        alias: ['widget.overriddenobjbase_grid'],
        extend:"Zenoss.ContextGridPanel",
        constructor: function(config) {
            config = config || {};

            Zenoss.Security.onPermissionsChange(function() {
                this.disableButtons(Zenoss.Security.doesNotHavePermission('zProperties Edit'));
            }, this);

            Ext.applyIf(config, {
                stateId: config.id || 'overridden_grid2',
                sm: Ext.create('Zenoss.SingleRowSelectionModel', {}),
                stateful: true,
                tbar:[
                    {
                    xtype: 'button',
                    iconCls: 'customize',
                    tooltip: _t('Edit selected Configuration Property value'),
                    disabled: Zenoss.Security.doesNotHavePermission('zProperties Edit'),
                    ref: 'customizeButton',
                        handler: function() {
                            var grid1 = Ext.getCmp('overriddenobjbase_grid1');
                            var grid2 = Ext.getCmp('overriddenobjover_grid2');
                            var data, grid, selected;
                            if( Ext.isEmpty(grid1.getSelectionModel().getSelection()) ){
                                // nothing selected in grid1
                                if( Ext.isEmpty(grid2.getSelectionModel().getSelection()) ){
                                    // nothing selected in grid2 either, abort
                                    return;
                                }else{
                                    // nothing selected in grid1, but we do have grid2 selection. Use it.
                                    selected = grid2.getSelectionModel().getSelection();
                                    grid = grid2;
                                }
                            }else{
                                // found a selection in grid1. Use it.
                                selected = grid1.getSelectionModel().getSelection();
                                grid = grid1;
                            }
                            data = selected[0].data;
                            showEditCustPropertyDialog(data, grid);
                        }
                    },
                    {
                    xtype: 'combo',
                    width:350,
                    fieldLabel: 'Configuration Properties',
                    labelWidth: 135,
                    editable: false,
                    id: 'propsCombo',
                    value: 'Select a Configuration Property',
                    queryMode:'local',
                    listConfig: {
                        maxWidth:300
                    },
                    store: ['none']
                    }
                ],
                store: Ext.create('Ext.data.ArrayStore', {
                      fields: [
                          {name: 'devicelink'},
                          {name: 'props'},
                          {name: 'proptype'}
                      ]
                   }),
                columns: [{
                        dataIndex: 'devicelink',
                        header: _t('Object'),
                        width: 340,
                        filter:false,
                        sortable: true,
                        renderer: function(e){
                            return Zenoss.render.DeviceClass(e, e.replace(/^\/zport\/dmd/, ''));
                        }
                    },{
                        dataIndex: 'props',
                        header: _t('Value'),
                        flex: 1,
                        sortable: true,
                        filter: false
                    },{
                        dataIndex: 'proptype',
                        hidden:true
                    }]
            });
            this.callParent(arguments);
            this.on('itemdblclick', this.onRowDblClick, this);
            this.on('select', this.onSelectRow, this);
        },
        setContext: function(uid) {
            this.uid = uid;
            var combo = Ext.getCmp('propsCombo');
            // load the grid's store
            this.callParent(arguments);
            Zenoss.remote.DeviceRouter.getOverriddenZprops({uid:uid}, function(response){
                if (response.success) {
                    setComboFromData(response, combo);
                    combo.on('change', function(){
                        onComboChange(uid);
                    });
                }
            });
            Zenoss.remote.DeviceRouter.getOverriddenObjectsParent({uid:uid, propname:''}, function(response){
                if (response.success) {
                    Ext.getCmp('overriddenobjbase_grid1').getStore().loadData(response.data);
                }
            });
            checkComboIndex();
        },
        refresh: function(){
            var uid = Ext.getCmp('overriddenobjbase_grid1').uid;
            loadBaseGrid(uid);
        },
        onSelectRow: function(){
            var otherGrid = Ext.getCmp('overriddenobjover_grid2');
            otherGrid.getSelectionModel().deselectAll();
        },
        onRowDblClick: function() {
            var selected = this.getSelectionModel().getSelection(),
                data = (selected) ? selected[0].data : null,
                disabled = this.up('overriddenobjects').down('button').isDisabled();
            if (!disabled && data != null) {
                showEditCustPropertyDialog(data, this);
            }
        },
        disableButtons: function(bool) {
            var btns = this.query("button");
            Ext.each(btns, function(btn){
                btn.setDisabled(bool);
            });
        }
    });


    /****************************************************** OVERRIDDEN OBJECT GRID **************************/


    Ext.define("Zenoss.OverriddenObj_over.Grid", {
        alias: ['widget.overriddenobjover_grid'],
        extend:"Zenoss.ContextGridPanel",
        constructor: function(config) {
            config = config || {};

            Ext.applyIf(config, {
                stateId: config.id || 'overridden_grid2',
                sm: Ext.create('Zenoss.SingleRowSelectionModel', {}),
                stateful: true,
                store: Ext.create('Ext.data.ArrayStore', {
                    sorters: [
                          {property : 'devicelink', direction: 'ASC'}
                      ],
                      fields: [
                          {name: 'objtype'},
                          {name: 'name'},
                          {name: 'devicelink'},
                          {name: 'props'},
                          {name: 'proptype'}
                      ]
                   }),
                columns: [{
                        header: _t("Overriding Object"),
                        dataIndex: 'devicelink',
                        width: 340,
                        sortable: true,
                        renderer: function(val, meta, record) {
                            if (record.get('objtype') == 'devices') {
                                return Zenoss.render.Device(val, record.get('name'));
                            } else {
                                return Zenoss.render.DeviceClass(val.substring(8));
                            }
                        }
                    },{
                        dataIndex: 'props',
                        header: _t('Value'),
                        flex: 1,
                        sortable: true
                    },{
                        dataIndex: 'proptype',
                        hidden:true
                    }]
            });
            this.callParent(arguments);
            this.on('itemdblclick', this.onRowDblClick, this);
            this.on('select', this.onSelectRow, this);
        },
        setContext: function(uid) {
            this.uid = uid;
            // load the grid's store
            this.callParent(arguments);
        },
        refresh: function(){
            var uid = Ext.getCmp('overriddenobjbase_grid1').uid;
            loadOverriddenGrid(uid);
        },
        onSelectRow: function(){
            var otherGrid = Ext.getCmp('overriddenobjbase_grid1');
            otherGrid.getSelectionModel().deselectAll();
        },
        onRowDblClick: function() {
            var selected = this.getSelectionModel().getSelection(),
                data = (selected) ? selected[0].data : null,
                disabled = this.up('overriddenobjects').down('button').isDisabled();
            if (!disabled && data != null) {
                showEditCustPropertyDialog(data, this);
            }
        }
    });

    Ext.define("Zenoss.form.overriddenobjects", {
        alias:['widget.overriddenobjects'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};
            this.grid1Id = "overriddenobjbase_grid1";
            this.grid2Id = "overriddenobjover_grid2";
            Ext.applyIf(config, {
                layout: 'border',
                defaults: {
                    split: true
                },
                items: [{
                    id: this.grid1Id,
                    xtype: "overriddenobjbase_grid",
                    region: 'north',
                    height: '20%',
                    ref: 'overriddenGrid1',
                    displayFilters: config.displayFilters
                },
                {
                    id: this.grid2Id,
                    xtype: "overriddenobjover_grid",
                    region: 'center',
                    ref: 'overriddenGrid2',
                    displayFilters: config.displayFilters
                }]
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            Ext.getCmp(this.grid1Id).setContext(uid);
            Ext.getCmp(this.grid2Id).setContext(uid);
        }
    });

})();
