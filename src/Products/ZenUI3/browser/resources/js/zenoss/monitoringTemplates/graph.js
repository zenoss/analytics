/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

var router;
    //addGraphDefinition, deleteGraphDefinition, addThresholdToGraph;


Ext.ns('Zenoss', 'Zenoss.templates');

router = Zenoss.remote.TemplateRouter;


Ext.define('Zenoss.InstructionTypeModel', {
    extend: 'Ext.data.Model',
    idProperty: 'pythonClassName',
    fields: ['pythonClassName', 'label']
});

/**
 * @class Zenoss.graph.GraphPointModel
 * @extends Ext.data.Model
 * Field definitions for the Graph Point
 **/
Ext.define('Zenoss.graph.GraphPointModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: ['uid', 'name', 'type', 'description']
});

Ext.define("Zenoss.GraphPointStore", {
    alias:['widget.graphpointstore'],
    extend:"Zenoss.NonPaginatedStore",
    constructor: function(config){
        Ext.applyIf(config, {
            model: 'Zenoss.graph.GraphPointModel',
            directFn: router.getGraphPoints,
            root: 'data'
        });
        this.callParent(arguments);
    }
});

Ext.define("Zenoss.BaseSequenceGrid", {
    extend:"Ext.grid.GridPanel",
    constructor: function(config){
        Ext.applyIf(config, {
            enableDragDrop   : true,
            viewConfig: {
                forcefit: true,
                plugins: {
                    ptype: 'gridviewdragdrop'
                }
            }
        });
        this.addEvents({'resequence': true});
        Zenoss.BaseSequenceGrid.superclass.constructor.call(this, config);
    }
});

Ext.define("Zenoss.GraphPointGrid", {
    alias:['widget.graphpointgrid'],
    extend:"Zenoss.ContextGridPanel",
    constructor: function(config){
        var me = this;
        Ext.applyIf(config, {
            height: 215,
            viewConfig: {
                plugins: {
                    ptype: 'gridviewdragdrop'
                }
            },
            listeners: {
                /**
                 * The selection model was being ignored at this point so I used the
                 * row click.
                 **/
                itemclick: function() {
                    //var record = getSelectedGraphPoint();
                    var record = me.getSelectionModel().getSelected();
                    if (record) {
                        //Ext.getCmp('deleteGraphPointButton').enable();
                        //Ext.getCmp('editGraphPointButton').enable();
                        this.deleteGraphPointButton.enable();
                        this.editGraphPointButton.enable();
                    }else{
                        //Ext.getCmp('deleteGraphPointButton').disable();
                        //Ext.getCmp('editGraphPointButton').disable();
                        this.deleteGraphPointButton.disable();
                        this.editGraphPointButton.disable();
                    }
                },
                itemdblclick: function() {
                    if (me.getSelectionModel().getSelected()) {
                        displayGraphPointForm(me.getSelectionModel().getSelected(), me);
                    }
                }
            },
            store: Ext.create('Zenoss.GraphPointStore', {}),
            columns: [
                {dataIndex: 'name', header: _t('Name'), width: 150},
                {dataIndex: 'type', header: _t('Type'), width: 150},
                {
                    dataIndex: 'description',
                    header: _t('Description'),
                    //id: 'definition_description',
                    flex: 1
                }
            ],
            tbar: [{
                xtype: 'button',
                //id: 'addGraphPointButton',
                iconCls: 'add',
                //menu: 'graphPointMenu',
                menu: new Ext.menu.Menu({
                    items: [{
                        xtype: 'menuitem',
                        text: _t('Data Point'),
                        handler: function(){
                            //Ext.getCmp('addDataPointToGraphDialog').show();
                            var addDataPointToGraphDialog =
                                new Zenoss.HideFormDialog({
                                    //id: 'addDataPointToGraphDialog',
                                    title: _t('Add Data Point'),
                                    closeAction: 'hide',
                                    items:[{
                                        xtype: 'combo',
                                        ref: 'comboBox',
                                        getInnerTpl: function() {
                                            return '<tpl for="."><div ext:qtip="{name}" class="x-combo-list-item">{name}</div></tpl>';
                                        },
                                        fieldLabel: _t('Data Point'),
                                        valueField: 'uid',
                                        displayField: 'name',
                                        triggerAction: 'all',
                                        forceSelection: true,
                                        editable: false,
                                        allowBlank: false,
                                        listeners: {
                                            validitychange: function(form, isValid){
                                                //var window = Ext.getCmp('addDataPointToGraphDialog');
                                                var window = addDataPointToGraphDialog;
                                                if (window.isVisible()){
                                                    window.submit.setDisabled(!isValid);
                                                }
                                            }
                                        },
                                        store: Ext.create('Zenoss.NonPaginatedStore', {
                                            root: 'data',
                                            model: 'Zenoss.model.Basic',
                                            directFn: router.getDataPoints
                                        })
                                    },{
                                        xtype: 'checkbox',
                                        name: 'include_related_thresholds',
                                        ref: 'includeRelatedThresholds',
                                        fieldLabel: _t('Include Related Thresholds'),
                                        checked: true
                                    }],
                                    listeners: {
                                        show: function() {
                                            var combo, uid;
                                            //combo = Ext.getCmp('addDataPointToGraphDialog').comboBox;
                                            combo = addDataPointToGraphDialog.comboBox;
                                            combo.reset();
                                            //Ext.getCmp('addDataPointToGraphDialog').submit.disable();
                                            addDataPointToGraphDialog.submit.disable();
                                            //uid = getSelectedTemplate().data.uid;
                                            uid = me.templateUid;
                                            combo.store.setContext(uid);
                                        }
                                    },
                                    buttons: [
                                        {
                                            xtype: 'HideDialogButton',
                                            ui: 'dialog-dark',
                                            ref: '../submit',
                                            text: _t('Submit'),
                                            disabled: true,
                                            handler: function() {
                                                //var dataPointUid = Ext.getCmp('addDataPointToGraphDialog').comboBox.getValue(),

                                                var dataPointUid = addDataPointToGraphDialog.comboBox.getValue(),
                                                //graphUid = getSelectedGraphDefinition().get("uid"),
                                                graphUid = me.uid,
                                                //includeThresholds = Ext.getCmp('addDataPointToGraphDialog').includeRelatedThresholds.getValue(),
                                                includeThresholds = addDataPointToGraphDialog.includeRelatedThresholds.getValue(),
                                                params = {
                                                    dataPointUid: dataPointUid,
                                                    graphUid: graphUid,
                                                    includeThresholds: includeThresholds
                                                },
                                                callback = function() {
                                                    //Ext.getCmp('graphPointGrid').refresh();
                                                    me.refresh();
                                                };
                                                router.addDataPointToGraph(params, callback);
                                            }
                                        }, {
                                            xtype: 'HideDialogButton',
                                            ui: 'dialog-dark',
                                            text: _t('Cancel')
                                        }]

                                });
                            addDataPointToGraphDialog.show();
                        }
                    }, {
                        xtype: 'menuitem',
                        text: _t('Threshold'),
                        handler: function(){
                            var win = new Zenoss.HideFormDialog({
                                title: _t('Add Threshold'),
                                items: {
                                    xtype: 'combo',
                                    getInnerTpl: function() {
                                        return '<tpl for="."><div ext:qtip="{name}" class="x-combo-list-item">{name}</div></tpl>';
                                    },
                                    fieldLabel: _t('Threshold'),
                                    valueField: 'uid',
                                    displayField: 'name',
                                    triggerAction: 'all',
                                    forceSelection: true,
                                    editable: false,
                                    allowBlank: false,
                                    store: Ext.create('Zenoss.NonPaginatedStore', {
                                        root: 'data',
                                        model: 'Zenoss.model.Basic',
                                        directFn: router.getThresholds
                                    }),
                                    listeners: {
                                        validitychange: function(form, isValid){
                                            var button = win.down('button[formBind=true]');
                                            if (button.isVisible()){
                                                button.setDisabled(!isValid);
                                            }
                                        }
                                    }
                                },
                                listeners: {
                                    show: function() {
                                        var combo, uid;
                                        combo = win.down('combo');
                                        combo.reset();
                                        uid = me.templateUid;
                                        combo.store.setContext(uid);
                                    }
                                },
                                buttons: [
                                    {
                                        xtype: 'HideDialogButton',
                                        ui: 'dialog-dark',
                                        formBind: true,
                                        disabled:true,
                                        text: _t('Submit'),
                                        handler: function() {
                                            var params, callback;
                                            params = {
                                                graphUid: me.uid,
                                                thresholdUid: win.down('combo').getValue()
                                            };
                                            callback = function() {
                                                me.refresh();
                                            };
                                            router.addThresholdToGraph(params, callback);
                                        }
                                    }, {
                                        xtype: 'HideDialogButton',
                                        ui: 'dialog-dark',
                                        text: _t('Cancel')
                                    }]

                            });
                            win.show();
                        }
                    }, {
                        xtype: 'menuitem',
                        text: _t('Custom Graph Point'),
                        handler: function(){
                            var win = new Zenoss.HideFormDialog({
                                title: _t('Add Custom Graph Point'),
                                listeners: {
                                    show: function(dialog) {
                                        dialog.addForm.idField.reset();
                                        dialog.addForm.typeCombo.reset();
                                        dialog.addForm.typeCombo.store.load();
                                    }
                                },
                                items: [{
                                    xtype: 'form',
                                    ref: 'addForm',
                                    listeners: {
                                        validitychange: function(form, isValid) {
                                            win.down('button[formBind=true]').setDisabled(!isValid);
                                        }
                                    },
                                    items: [{
                                        xtype: 'idfield',
                                        ref: 'idField',
                                        fieldLabel: _t('Name'),
                                        allowBlank: false
                                    }, {
                                        xtype: 'combo',
                                        ref: 'typeCombo',
                                        fieldLabel: _t('Instruction Type'),
                                        valueField: 'pythonClassName',
                                        displayField: 'label',
                                        triggerAction: 'all',
                                        forceSelection: true,
                                        editable: false,
                                        allowBlank: false,
                                        store: Ext.create('Zenoss.NonPaginatedStore', {
                                            root: 'data',
                                            autoLoad: false,
                                            model: 'Zenoss.InstructionTypeModel',
                                            directFn: router.getGraphInstructionTypes
                                        })
                                    }]
                                }],
                                buttons: [{
                                    xtype: 'HideDialogButton',
                                    ui: 'dialog-dark',
                                    disabled: true,
                                    formBind: true,
                                    ref: '../submitButton',
                                    text: _t('Add'),
                                    handler: function() {
                                        var params, callback, form = win.addForm;
                                        params = {
                                            graphUid: me.uid,
                                            customId: form.idField.getValue(),
                                            customType: form.typeCombo.getValue()
                                        };
                                        callback = function() {
                                            me.refresh();
                                        };
                                        router.addCustomToGraph(params, callback);
                                    }
                                }, {
                                    xtype: 'HideDialogButton',
                                    ui: 'dialog-dark',
                                    ref: '../cancelButton',
                                    text: _t('Cancel')
                                }]
                            });
                            win.show();
                        }
                    }]
                })
                //TODO: register tooltip without id?
                /*
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('addGraphPointButton');
                    }
                }
                */
            }, {
                xtype: 'button',
                //id: 'deleteGraphPointButton',
                ref: '../deleteGraphPointButton',
                iconCls: 'delete',
                disabled: true,
                //TODO: register tooltip without id?
                /*
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('deleteGraphPointButton');
                    }
                },
                */
                handler: function() {
                    var html, dialog;
                    // format the confimation message
                    html = _t("Are you sure you want to remove the graph point, {0}? There is no undo.");
                    //html = Ext.String.format(html, getSelectedGraphPoint().data.name);
                    html = Ext.String.format(html, me.getSelectionModel().getSelected().data.name);

                    // show the dialog
                    //dialog = Ext.getCmp('deleteGraphPointDialog');
                    dialog =
                        new Zenoss.MessageDialog({
                            //id: 'deleteGraphPointDialog',
                            title: _t('Delete Graph Point'),
                            // the message is generated dynamically
                            okHandler: function() {
                                var params, callback;
                                params = {
                                    uid: me.getSelectionModel().getSelected().get("uid")
                                };
                                callback = function() {
                                    me.deleteGraphPointButton.disable();
                                    me.editGraphPointButton.disable();
                                    me.refresh();
                                };
                                router.deleteGraphPoint(params, callback);
                            }
                        });

                    dialog.setText(html);
                    dialog.show();
                }
            }, {
                xtype: 'button',
                //id: 'editGraphPointButton',
                ref: '../editGraphPointButton',
                iconCls: 'customize',
                disabled: true,
                //TODO: register tooltip without id?
                /*
                listeners: {
                    render: function() {
                        Zenoss.registerTooltipFor('editGraphPointButton');
                    }
                },
                */
                handler: function() {
                    if (me.getSelectionModel().getSelected()) {
                        displayGraphPointForm(me.getSelectionModel().getSelected(), me);
                    }
                }
            }],
            selModel: Ext.create('Zenoss.SingleRowSelectionModel', {})
        });
        this.callParent(arguments);
    }
});


/**********************************************************************
 *
 * Graph Point Edit Dialog/Grid
 *
 */

/**
 * Call back function from when a user selects a graph point.
 * This shows yet another dialog for editing a graph point
 **/
function displayGraphPointForm(record, grid) {

    function displayEditDialog(response) {
        var win = Ext.create('Zenoss.form.DataSourceEditDialog', {
            record: response.data,
            items: response.form,
            singleColumn: true,
            width: 400,
            title: _t('Edit Graph Point'),
            directFn: router.setInfo,
            id: 'editGraphPointDialog',
            saveHandler: function() {
                grid.refresh();
            }
        });

        win.show();
    }

    // remote call to get the object details
    router.getInfo({uid: record.get("uid")}, displayEditDialog);
}

Ext.create('Zenoss.dialog.BaseWindow', {
    layout: 'fit',
    id: 'viewGraphDefinitionDialog',
    title: _t('View and Edit Graph Definition'),
    closeAction: 'hide',
    buttonAlign: 'left',
    autoScroll: true,
    plain: true,
    modal: true,
    width: 400,
    height: 500,
    padding: 10,
    buttons: [{
        ref: '../submitButton',
        xtype: 'HideDialogButton',
        ui: 'dialog-dark',
        text: _t('Submit'),
        disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
        handler: function(submitButton){
            var dialogWindow, basicForm, params;
            dialogWindow = submitButton.refOwner;
            basicForm = dialogWindow.formPanel.getForm();
            params = Ext.applyIf(basicForm.getValues(), {
                uid: dialogWindow.uid,
                hasSummary: false,
                log: false,
                base: false
            });
            basicForm.api.submit(params, function() {
                var gGrid = Ext.getCmp('graphGrid');
                if (gGrid !== undefined) {
                    gGrid.refresh();
                }
            });
        }
    },{
        xtype: 'HideDialogButton',
        ref: '../cancelButton',
        ui: 'dialog-dark',
        text: 'Cancel'
    }],
    items: {
        xtype: 'form',
        ref: 'formPanel',
        autoScroll: true,
        paramsAsHash: true,
        api: {
            load: router.getGraphDefinition,
            submit: router.setGraphDefinition
        },
        listeners: {
            validitychange: function(formPanel, valid){
                var dialogWindow = Ext.getCmp('viewGraphDefinitionDialog');
                if (Zenoss.Security.hasPermission('Manage DMD')) {
                    dialogWindow.submitButton.setDisabled( ! valid );
                }
            },
            show: function(formPanel){
                formPanel.getForm().load();
            }
        },
        items: [{
            xtype: 'idfield',
            fieldLabel: _t('Name'),
            name: 'newId',
            allowBlank: false
        },{
            xtype: 'numberfield',
            fieldLabel: _t('Height'),
            name: 'height',
            minValue: 250
        },{
            xtype: 'textfield',
            fieldLabel: _t('Units'),
            name: 'units'
        },{
            xtype: 'checkbox',
            fieldLabel: _t('Logarithmic Scale'),
            name: 'log'
        },{
            xtype: 'checkbox',
            fieldLabel: _t('Base 1024'),
            name: 'base'
        },{
            xtype: 'numberfield',
            allowDecimals: true,
            decimalPrecision: 3,
            fieldLabel: _t('Min Y'),
            hideTrigger: true,
            name: 'miny'
        },{
            xtype: 'numberfield',
            allowDecimals: true,
            decimalPrecision: 3,
            fieldLabel: _t('Max Y'),
            hideTrigger: true,
            name: 'maxy'
        },{
            xtype: 'textarea',
            fieldLabel: _t('Description'),
            name: 'description'
        },{
            xtype: 'checkbox',
            fieldLabel: _t('Has Summary'),
            name: 'hasSummary'
        }]
    },
    loadAndShow: function(uid) {
        this.uid = uid;
        this.formPanel.getForm().load({
            params: {uid:uid},
            success: function() {
                this.show();
            },
            scope: this
        });
    }
});

Ext.define("Zenoss.templates.GraphGrid", {
    alias:['widget.graphgrid'],
    extend:"Zenoss.ContextGridPanel",
    constructor: function(config) {
        var me = this,
            tbarItems = config.tbarItems || [];
        Ext.applyIf(config, {
            title: _t('Graph Definitions'),
            store: Ext.create('Zenoss.GraphStore', {}),
            enableDragDrop   : true,
            viewConfig: {
                forcefit: true,
                plugins: {
                    ptype: 'gridviewdragdrop'
                },
                listeners: {
                    /**
                     * Updates the graph order when the user drags and drops them
                     **/
                    drop: function() {
                        var records, uids;
                        records = me.store.getRange();
                        uids = Ext.pluck(Ext.pluck(records, 'data'), 'uid');
                        router.setGraphDefinitionSequence({'uids': uids});
                    }
                }
            },
            listeners: {
                /**
                 * Double click to edit a graph definition
                 **/
                itemdblclick: function(grid, record)  {
                    var dialogWindow, uid;
                    dialogWindow = Ext.getCmp('viewGraphDefinitionDialog');
                    uid = record.data.uid;
                    dialogWindow.loadAndShow(uid);
                }

            },
            selModel: new Zenoss.SingleRowSelectionModel({
                listeners: {
                    select: function() {
                        if (Zenoss.Security.hasPermission('Manage DMD')){
                            this.deleteGraphDefinitionButton.enable();
                            this.graphDefinitionMenuButton.enable();
                        }
                    },
                    scope: me
                }
            }),
            columns: [{dataIndex: 'name', header: _t('Name'), flex:1, width: 400}],

            tbar: tbarItems.concat([{
                itemId: 'addGraphDefinitionButton',
                xtype: 'button',
                iconCls: 'add',
                ref: '../addButton',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                listeners: {
                    render: function(t) {
                        Zenoss.registerTooltipFor('addGraphDefinitionButton', t);
                    }
                },
                handler: function(t) {
                    var templateUid = Zenoss.getCmp('dataSourceTreeGrid', t).uid;
                    if (!templateUid) {
                        new Zenoss.dialog.ErrorDialog({message: _t('There is no template to which to add a graph definition.')});
                        return;
                    }
                    var dialog = Ext.create('Zenoss.dialog.BaseWindow', {
                        title: _t('Add Graph Definition'),
                        buttonAlign: 'left',
                        autoScroll: true,
                        plain: true,
                        width: 300,
                        autoHeight: true,
                        modal: true,
                        padding: 10,
                        items: [{
                            xtype: 'form',
                            listeners: {
                                validitychange: function(formPanel, valid) {
                                    dialog.submitButton.setDisabled( !valid );
                                }
                            },
                            items: [
                                {
                                    xtype: 'idfield',
                                    id: 'graphDefinitionIdTextfield',
                                    fieldLabel: _t('Name'),
                                    allowBlank: false
                                }
                            ]

                        }],
                        buttons: [
                            {
                                xtype: 'DialogButton',
                                ref: '../submitButton',
                                disabled: true,
                                text: _t('Submit'),
                                handler: function() {
                                    var params, callback;
                                    params = {
                                        templateUid: me.getSelectedTemplateUid(),
                                        graphDefinitionId: Ext.getCmp('graphDefinitionIdTextfield').getValue()
                                    };
                                    callback = function() {
                                        me.refresh();
                                    };

                                    router.addGraphDefinition(params, callback);
                                }
                            }, {
                                xtype: 'DialogButton',
                                text: _t('Cancel')
                            }]
                    });
                    dialog.show();
                }
            }, {
                itemId: 'deleteGraphDefinitionButton',
                ref: '../deleteGraphDefinitionButton',
                xtype: 'button',
                iconCls: 'delete',
                disabled: true,
                listeners: {
                    render: function(t) {
                        Zenoss.registerTooltipFor('deleteGraphDefinitionButton', t);
                    }
                },
                handler: function(button) {
                    var msg, name, html, dialog;
                    msg = _t("Are you sure you want to remove {0}? There is no undo.");
                    name = me.getSelectedGraphDefinition().data.name;
                    html = Ext.String.format(msg, name);
                    dialog = new Zenoss.MessageDialog({
                        title: _t('Delete Graph Definition'),
                        // the message is generated dynamically
                        okHandler: function(){
                            var params, callback;
                            params = {
                                uid: me.getSelectedGraphDefinition().get("uid")
                            };
                            callback = function() {
                                button.disable();
                                button.refOwner.graphDefinitionMenuButton.disable();
                                me.refresh();
                            };
                            router.deleteGraphDefinition(params, callback);
                        }
                    });
                    dialog.setText(html);
                    dialog.show();
                }
            }, {
                itemId: 'graphDefinitionMenuButton',
                ref: '../graphDefinitionMenuButton',
                xtype: 'button',
                listeners: {
                    render: function(t) {
                        Zenoss.registerTooltipFor('graphDefinitionMenuButton', t);
                    }
                },
                iconCls: 'customize',
                menu: new Ext.menu.Menu({
                    items: [{
                        xtype: 'menuitem',
                        text: _t('Manage Graph Points'),
                        handler: function(){
                            var uid, dialog;
                            uid = me.getSelectedGraphDefinition().get("uid");
                            dialog = new Zenoss.HideFitDialog({
                                title: _t('Manage Graph Points'),
                                items: [{
                                    xtype: 'graphpointgrid',
                                    templateUid: me.getSelectedTemplateUid(),
                                    ref: 'graphGrid'
                                }],
                                buttons: [{
                                    xtype: 'HideDialogButton',
                                    ui: 'dialog-dark',
                                    text: _t('Save'),
                                    handler: function(){
                                        if (Zenoss.Security.hasPermission('Manage DMD')) {
                                            var records, uids;
                                            //records = grid.getStore().getRange();
                                            records = dialog.graphGrid.getStore().getRange();
                                            uids = Ext.Array.pluck(Ext.Array.pluck(records, 'data'), 'uid');
                                            router.setGraphPointSequence({'uids': uids});
                                        }
                                    }
                                }, {
                                    xtype: 'HideDialogButton',
                                    ui: 'dialog-dark',
                                    text: _t('Cancel')
                                }]
                            });
                            dialog.show();
                            dialog.graphGrid.setContext(uid);
                        }
                    }, {
                        xtype: 'menuitem',
                        text: _t('View and Edit Details'),
                        handler: function(){
                            var dialogWindow, uid;
                            dialogWindow = Ext.getCmp('viewGraphDefinitionDialog');
                            uid = me.getSelectedGraphDefinition().get("uid");
                            dialogWindow.loadAndShow(uid);
                        }
                    }]
                }),
                disabled: true
            }])
        });
        this.callParent(arguments);
    },
    getSelectedTemplate: function() {
        return Zenoss.getCmp('templateTree', this).getSelectionModel().getSelectedNode();
    },

    getSelectedTemplateUid: function() {
        return this.getSelectedTemplate().data.uid;
    },
    getSelectedGraphDefinition: function() {
        return this.getSelectionModel().getSelected();
    }
});


})();
