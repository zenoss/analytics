/*****************************************************************************
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


/* package level */
(function() {
    Ext.namespace('Zenoss.templates');
    /**********************************************************************
     *
     * Variable Declarations
     *
     */
    var router,
        treeId,
        dataSourcesId;

    Zenoss.templates.thresholdsId = 'thresholdGrid';
    dataSourcesId = 'dataSourceTreeGrid';
    router = Zenoss.remote.TemplateRouter;

    // The id of the tree on the left hand side of the screen
    treeId = 'templateTree';

    /**********************************************************************
     *
     * Add Threshold
     *
     */

    function addThreshold(data, grid){
        var uid,
            node,
            dataPoints,
            params,
            callback,
            dataSourceGrid = Zenoss.getCmp(dataSourcesId, grid);
        uid = grid.getTemplateUid();
        if (dataSourceGrid) {
            node = dataSourceGrid.getSelectionModel().getSelectedNode();
        }
        if ( node && node.isLeaf() ) {
            dataPoints = [node.data.uid];
        } else {
            dataPoints = [];
        }
        params = {
            uid: uid,
            thresholdType: data.thresholdTypeField,
            thresholdId: data.thresholdIdField,
            dataPoints: dataPoints
        };
        callback = function() {
            grid.refresh();
        };
        Zenoss.remote.TemplateRouter.addThreshold(params, callback);
    }

    function showAddThresholdDialog(grid) {
        if (!grid.getTemplateUid()) {
            return;
        }
        var context = grid.getTemplateUid() + '/thresholds';
        var addThresholdDialog = Ext.create('Zenoss.dialog.BaseWindow', {
            id: 'addThresholdDialog',
            title: _t('Add Threshold'),
            message: _t('Allow the user to add a threshold.'),
            width: 295,
            height: 250,
            modal: true,
            padding: 10,
            listeners:{
                show: function() {
                    this.formPanel.getForm().reset();
                }
            },

            buttons: [{
                ref: '../submitButton',
                text: _t('Add'),
                disabled: true,
                xtype: 'DialogButton',
                handler: function(submitButton) {
                    var dialogWindow, basicForm;
                    dialogWindow = submitButton.refOwner;
                    basicForm = dialogWindow.formPanel.getForm();
                    addThreshold(basicForm.getValues(), grid);
                }
            }, {
                ref: '../cancelButton',
                text: _t('Cancel'),
                xtype: 'DialogButton'
            }],
            items: {
                xtype: 'form',
                ref: 'formPanel',
                height: 75,
                leftAlign: 'top',
                monitorValid: true,
                paramsAsHash: true,
                listeners: {
                    validitychange: function(formPanel, valid) {
                        addThresholdDialog.submitButton.setDisabled( !valid );
                    }
                },
                items: [{
                    name: 'thresholdIdField',
                    xtype: 'idfield',
                    fieldLabel: _t('Name'),
                    allowBlank: false,
                    context: context
                },{
                    name: 'thresholdTypeField',
                    xtype: 'combo',
                    fieldLabel: _t('Type'),
                    displayField: 'type',
                    forceSelection: true,
                    triggerAction: 'all',
                    emptyText: _t('Select a type...'),
                    selectOnFocus: true,
                    allowBlank: false,
                    store: {
                        type: 'directcombo',
                        autoLoad: true,
                        directFn: Zenoss.remote.TemplateRouter.getThresholdTypes,
                        root: 'data',
                        fields: ['type']
                    }
                }]
            }});
        addThresholdDialog.show();
    }


     /**********************************************************************
     *
     * Edit Thresholds
     *
     */

    /**
     *@returns Zenoss.FormDialog Ext Dialog type associated with the
     *          selected threshold type
     **/
    function thresholdEdit(grid) {
        var record = grid.getSelectionModel().getSelected();


        function displayEditDialog(response) {

            var thrtypes = ["PredictiveThreshold", "MinMaxThreshold"]
            if (thrtypes.includes(response.record.type)){
                //test button should always be at the bottom of the form
                response.form.items[response.form.items.length - 1].items.push({
                    xtype:'panel',
                    columnWidth: 0.5,
                    baseCls: 'show-rpn-values',
                    items:[{
                        xtype: 'displayfield',
                        value: _t('Show values after RPN used'),
                        width: 300,
                    },{
                        xtype: 'button',
                        text: _t('Test with RPN'),
                        id: 'testDeviceButton',
                        handler: showRPNValues
                  }]});
            }

            var win = Ext.create( 'Zenoss.form.DataSourceEditDialog', {
                record: response.record,
                items: response.form,
                width: 850,
                singleColumn: response.form.items.length === 1 ? true : false,
                xtype: 'datasourceeditdialog',
                title: _t('Edit Threshold'),
                directFn: router.setInfo,
                id: 'editThresholdDialog',
                saveHandler: function() {
                    grid.refresh();
                    if (win) {
                        win.hide();
                    }
                }
            });

            win.show();
        }
 
        function showRPNValues (){
            //This is for picking up datapoints name in different type of thresholds
            var dpsobj, selectedds;
            dpsobj = Ext.ComponentQuery.query('[fieldLabel=DataPoints]')[0] ||
                     Ext.ComponentQuery.query('[fieldLabel=DataPoint]')[0]
            if (dpsobj.fieldLabel == 'DataPoint'){
                if (dpsobj.value == null){
                    selecteddps = [];
                } else {
                    selecteddps = [dpsobj.value];
                }
            } else {
                selecteddps = dpsobj.value
            }
            var minval = Ext.ComponentQuery.query('[name="minval"]')[0],
                maxval = Ext.ComponentQuery.query('[name="maxval"]')[0];
            router.getDataPointsRPNValues({thuid: record.data.uid, selecteddps: selecteddps,
                                           minval: minval.value, maxval:maxval.value}, addRPNtable)
        }

        function addRPNtable(response){
            Ext.create('Zenoss.stats.RPNValues', {
                        response: response
            }).show();
        };

        // send the request for all of the threshold's info to the server
        router.getThresholdDetails({uid: record.data.uid}, displayEditDialog);
    }


     /**********************************************************************
     *
     * Threshold Data Grid
     *
     */


    /**
     * @class Zenoss.thresholds.Model
     * @extends Ext.data.Model
     * Field definitions for the thresholds
     **/
    Ext.define('Zenoss.thresholds.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: ['name', 'type', 'dataPoints', 'severity', 'enabled','type', 'minval', 'maxval', 'uid']
    });

    /**
     * @class Zenoss.thresholds.Store
     * @extend Zenoss.DirectStore
     * Direct store for loading thresholds
     */
    Ext.define("Zenoss.thresholds.Store", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.thresholds.Model',
                directFn: router.getThresholds,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    /**
     * Definition for the Thresholds datagrid. This is used in
     * templates.js in the updateThresholds function.
     **/
    Ext.define("Zenoss.templates.thresholdDataGrid", {
        alias:['widget.thresholddatagrid'],
        extend:"Zenoss.ContextGridPanel",

        constructor: function(config) {
            var listeners = {},
                me = this,
                tbarItems = config.tbarItems || [];

            listeners = Ext.apply(listeners, {
                itemdblclick: function(gridview) {
                    thresholdEdit(gridview.ownerCt);
                }
            });

            config = config || {};
            Ext.applyIf(config, {
                itemId: Zenoss.templates.thresholdsId,
                selModel:   new Zenoss.SingleRowSelectionModel ({
                    listeners : {
                        /**
                         * If they have permission and they select a row, show the
                         * edit and delete buttons
                         **/
                        select: function () {
                            // enable the "Delete Threshold" button
                            if (Zenoss.Security.hasPermission('Manage DMD')) {
                                me.deleteButton.enable();
                                me.editButton.enable();
                            }
                        }
                    }
                }),
                viewConfig: {
                    plugins: {
                        ptype: 'gridviewdragdrop',
                        dragText: _t('Drag to add to Graph Definition'),
                        dragGroup: 'addtoGraph'
                    }
                },
                title: _t('Thresholds'),
                store: Ext.create('Zenoss.thresholds.Store', { }),
                listeners: listeners,
                tbar: tbarItems.concat([{
                    xtype: 'button',
                    iconCls: 'add',
                    itemId: 'thresholdAddButton',
                    ref: '../addButton',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function(btn) {
                        var templateUid = Zenoss.getCmp(dataSourcesId, this);
                        if (!templateUid) {
                            new Zenoss.dialog.ErrorDialog({message: _t('There is no template to which to add a threshold.')});
                            return;
                        }
                        showAddThresholdDialog(btn.refOwner);
                    },
                    scope: me,
                    listeners: {
                        render: function(t) {
                            Zenoss.registerTooltipFor('thresholdAddButton', t);
                        }
                    }
                }, {
                    ref: '../deleteButton',
                    itemId: 'thresholdDeleteButton',
                    xtype: 'button',
                    iconCls: 'delete',
                    disabled: true,
                    handler: function() {
                        var row = me.getSelectionModel().getSelected(),
                            uid,
                            params;
                        if (row){
                            uid = row.get("uid");
                            // show a confirmation
                     new Zenoss.dialog.SimpleMessageDialog({
                                title: _t('Delete Threshold'),
                                message: Ext.String.format(_t("Are you sure you want to delete this threshold? There is no undo.")),
                            buttons: [{
                                xtype: 'DialogButton',
                                text: _t('OK'),
                                handler: function() {
                                    params= {
                                        uid:uid
                                    };
                                    router.removeThreshold(params, function(){
                                        me.refresh();
                                        me.deleteButton.disable();
                                        me.editButton.disable();
                                    });
                                }
                            }, {
                                xtype: 'DialogButton',
                                text: _t('Cancel')
                            }]
                        }).show();
                        }
                    },
                    listeners: {
                        render: function(t) {
                            Zenoss.registerTooltipFor('thresholdDeleteButton', t);
                        }
                    }

                }, {
                    itemId: 'thresholdEditButton',
                    ref: '../editButton',
                    xtype: 'button',
                    iconCls: 'customize',
                    disabled: true,
                    handler: function(button) {
                        thresholdEdit(button.refOwner);
                    },
                    listeners: {
                        render: function(t) {
                            Zenoss.registerTooltipFor('thresholdEditButton', t);
                        }
                    }
                }]),
                columns: [{
                    dataIndex: 'name',
                    flex: 1,
                    header: _t('Name')
                }, {
                    dataIndex: 'type',
                    header: _t('Type')
                }, {
                    dataIndex: 'minval',
                    header: _t('Min. Value')
                }, {
                    dataIndex: 'maxval',
                    header: _t('Max. Value')
                }]
            });

            Zenoss.templates.thresholdDataGrid.superclass.constructor.apply(
                this, arguments);
        },
        getTemplateUid: function() {
            var tree = Zenoss.getCmp(treeId, this),
                node = tree.getSelectionModel().getSelectedNode();
            if (node) {
                return node.data.uid;
            }
        }
    });

    Ext.define('RPNValues', {
        extend: 'Ext.data.Model',
        fields: ['name', 'maxrpn', 'minrpn', 'rpnvalue']
    });

    Ext.define("Zenoss.stats.RPNValues", {
        extend: "Zenoss.dialog.BaseDialog",
        constructor: function(config) {
           var dialogStore = Ext.create('Ext.data.Store', {
               model: 'RPNValues',
               data: config.response.dpRPN
           });
           config = config || {};
           Ext.applyIf(config, {
               title: _t('Values with RPN used'),
               minWidth: 500,
               minHeight: 200,
               height: 400,
               autoScroll: true,
               items: Ext.create('Ext.grid.Panel', {
                   stripeRows: true,
                   store: dialogStore,
                   sortable: false,
                   columns: [{
                       header: "Datapoint Name",
                       sortable: false,
                       dataIndex: 'name',
                       flex: 2,
                   },{
                       header: "RPN formula",
                       dataIndex: 'rpnvalue',
                       flex: 2
                   },{
                       header: "Min value after rpn",
                       dataIndex: 'minrpn',
                       flex: 2
                   },{
                       header: "Max value after rpn",
                       dataIndex: 'maxrpn',
                       flex: 2
                   }]
               }),
           });
           this.callParent([config]);
        }
    });

}());
