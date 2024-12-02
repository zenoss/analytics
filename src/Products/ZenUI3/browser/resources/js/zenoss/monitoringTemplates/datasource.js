/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

var router, dataSourcesId, resetCombo,
    addMetricToGraph, editDataSourcesId, treeId;

Ext.ns('Zenoss');

router = Zenoss.remote.TemplateRouter;
dataSourcesId = 'dataSourceTreeGrid';
editDataSourcesId = "editDataSource";

// NOTE: this must match the tree id from the template.js file
treeId = 'templateTree';

addMetricToGraph = function(dataPointUid, graphUid) {
    var params, callback;
    params = {dataPointUid: dataPointUid, graphUid: graphUid};
    router.addDataPointToGraph(params, callback);
};

Ext.define('Zenoss.GraphModel', {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        'uid', 'name', 'graphPoints', 'units', 'height', 'width',
             'sequence'
    ]
});

Ext.define("Zenoss.GraphStore", {
    extend:"Zenoss.NonPaginatedStore",
    alias: ['widget.graphstore'],
    constructor: function(config) {
        Ext.applyIf(config, {
            root: 'data',
            directFn: router.getGraphs,
            model: 'Zenoss.GraphModel'
        });
        this.callParent(arguments);
    }
});


/**********************************************************************
 *
 * Add Data Source
 *
 */

/**
 * @class Zenoss.templates.DataSourceTypeModel
 * @extends Ext.data.Model
 *
 **/
Ext.define('Zenoss.templates.DataSourceTypeModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'type',
    fields: [
        {name: 'type'}
    ]
});


/**
 * @class Zenoss.templates.DataSourceModel
 * @extends Ext.data.Model
 * Field definitions for the datasource/datapoint grid
 **/
Ext.define('Zenoss.templates.DataSourceModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        {name: 'uid'},
        {name: 'name'},
        {name: 'source'},
        {name: 'enabled'},
        {name: 'type'}
    ]
});

/**
 * @class Zenoss.templates.DataSourceStore
 * @extend Ext.data.TreeStore
 * Direct store for loading datasources and datapoints
 */
Ext.define("Zenoss.templates.DataSourceStore", {
    extend: "Ext.data.TreeStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.templates.DataSourceModel',
            nodeParam: 'uid',
            remoteSort: false,
            proxy: {
                limitParam: undefined,
                startParam: undefined,
                pageParam: undefined,
                sortParam: undefined,
                type: 'direct',
                directFn: router.getDataSources,
                reader: {
                    root: 'data',
                    totalProperty: 'count'
                }
            }
        });
        this.callParent(arguments);
    }
});

/**
 * @class Zenoss.DataSourceTreeGrid
 * @extends Ext.Tree.Panel
 * @constructor
 */
Ext.define("Zenoss.DataSourceTreeGrid", {
    extend: "Ext.tree.Panel",
    alias: ['widget.DataSourceTreeGrid'],

    constructor: function(config) {
        var me = this,
            tbarItems = config.tbarItems || [],
            dsAddHandler = config.dsAddHandler || me.showAddDataSourceDialog,
            dsDelHandler = config.dsDelHandler || me.showDeleteDataSourceDialog,
            addToGraphHandler = config.addToGraphHandler || me.showAddToGraphDialog,
            dpAddHandler = config.dpAddHandler || me.showAddDataPointDialog,
            editEitherHandler = config.editEitherHandler || me.editDataSourceOrPoint;
            //dsDelHandler = config.dsDelHandler || showDeleteDataSourceDialog,
            //dsEditMenu = config.dsEditMenu || dataSourceMenu;
        Ext.applyIf(config, {
            useArrows: true,
            cls: 'x-tree-noicon',
            rootVisible: false,
            useTemplateSource: false,
            itemId: dataSourcesId,
            title: _t('Data Sources'),
            listeners: {
                // when they doubleclick we will open up the tree and
                // display the dialog
                beforeitemdblclick: me.editDataSourceOrPoint
            },
            store: Ext.create('Zenoss.templates.DataSourceStore', {}),
            tbar: tbarItems.concat([{
                    xtype: 'button',
                    iconCls: 'add',
                    itemId:'datasourceAddButton',
                    ref: '../addButton',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: dsAddHandler,
                    scope: me,
                    listeners: {
                        render: function(t) {
                            Zenoss.registerTooltipFor('datasourceAddButton', t);
                        }
                    }
            }, {
                xtype: 'button',
                iconCls: 'delete',
                ref: '../deleteButton',
                itemId: 'datasourceDeleteButton',
                disabled: true, //Zenoss.Security.doesNotHavePermission('Manage DMD'),
                listeners: {
                    render: function(t) {
                        Zenoss.registerTooltipFor('datasourceDeleteButton', t);
                    }
                },
                scope: me,
                handler: dsDelHandler
            },{
                xtype: 'button',
                itemId: 'datasourceEditButton',
                iconCls: 'customize',
                ref: '../customizeButton',
                disabled: true, //Zenoss.Security.doesNotHavePermission('Manage DMD'),
                listeners: {
                    render: function(t) {
                        Zenoss.registerTooltipFor('datasourceEditButton', t);
                    }
                },
                menu: new Ext.menu.Menu({
                    items: [{
                        xtype: 'menuitem',
                        text: _t('Add Data Point To Graph'),
                        disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        scope: me,
                        handler: addToGraphHandler
                    },{
                        xtype: 'menuitem',
                        text: _t('Add Data Point'),
                        disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        scope: me,
                        handler: dpAddHandler
                    },{
                        xtype: 'menuitem',
                        text: _t('View and Edit Details'),
                        disable: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        scope: me,
                        handler: editEitherHandler
                    }]
                })
            }]),
            columns: [{
                xtype: 'treecolumn', //this is so we know which column will show the tree
                text: 'Name',
                flex: 2,
                sortable: true,
                dataIndex: 'name'
            }, {
                dataIndex: 'source',
                flex: 1,
                header: 'Source',
                width: 250
            }, {
                dataIndex: 'enabled',
                header: 'Enabled',
                width: 60
            }, {
                dataIndex: 'type',
                header: 'Type',
                width: 90
            }],
            selModel: Ext.create('Zenoss.TreeSelectionModel', {
                mode: 'SINGLE',
                listeners: {
                    selectionchange: me.onSelectionChange,
                    scope: me
                }
            })
        });
        this.callParent(arguments);
    },
    onSelectionChange: function(t, records) {
        var disable = !records.length && !Zenoss.Security.hasPermission('Manage DMD');
        this.deleteButton.setDisabled(disable);
        this.customizeButton.setDisabled(disable);
    },
    disableToolBarButtons: function(bool) {
        this.addButton.setDisabled(bool && Zenoss.Security.hasPermission('Manage DMD'));
        this.deleteButton.setDisabled(bool && Zenoss.Security.hasPermission('Manage DMD'));
        this.customizeButton.setDisabled(bool && Zenoss.Security.hasPermission('Manage DMD'));
    },
    setContext: function(uid) {
        if (uid !== this.uid){
            this.uid = uid;
            this.refresh();
        }
    },
    refresh: function(callback, scope) {
        var root = this.getRootNode();
        root.setId(this.uid);
        root.data.uid = this.uid;
        root.uid = this.uid;
        if (callback) {
            this.getStore().load({
                callback: callback,
                scope: scope || this
            });
        }else {
            this.getStore().load();
        }

    },

    /**
     * Creates the dynamic delete message and shows the dialog
     **/
    showDeleteDataSourceDialog: function() {
        var msg, name, html, dialog,
            node = this.getSelectionModel().getSelectedNode(),
            me = this;
        if (node) {
            // set up the custom delete message
            msg = _t("Are you sure you want to remove {0}? There is no undo.");
            name = node.data.name;
            html = Ext.String.format(msg, name);

            // show the dialog
            dialog = new Zenoss.MessageDialog({
                // id: 'deleteDataSourceDialog',
                title: _t('Delete'),
                // msg is generated dynamically
                okHandler: function(){
                    var params,
                        selectedId = node.data.leaf ? node.parentNode.data.id : null,
                        callback;
                    params = {
                        uid: node.get("uid")
                    };
                    callback = function() {
                        me.refreshDataSourceGrid(selectedId);
                    };
                    router.deleteDataSource(params, me.refreshDataSourceGrid.bind(me, selectedId));
                }
            });
            dialog.setText(html);
            dialog.show();
        }else{
            new Zenoss.dialog.ErrorDialog({message: _t('You must select a Data Source or Data Point.')});
        }
    },
    /**
     * Displays the Add Data Point dialog and saves the inputted infomation
     * back to the server
     **/
    showAddDataPointDialog: function() {
        var selectedNode = this.getSelectionModel().getSelectedNode(),
            me = this, nodeId;

        // make sure they selected a node
        if (!selectedNode) {
            new Zenoss.dialog.ErrorDialog({message: _t('You must select a data source.')});
            return;
        }
        nodeId = selectedNode.data.id;

        // display the name dialog
        var win = Ext.create('Zenoss.dialog.BaseWindow', {
            title: _t('Add Data Point'),
            height: 160,
            width: 310,
            listeners: {
                validitychange: function(form, isValid) {
                    this.ownerCt.query('DialogButton')[0].setDisabled(!isValid);
                }
            },
            items:{
                xtype: 'form',
                buttonAlign: 'left',
                items: [{
                    xtype: 'idfield',
                    ref: 'metricName',
                    fieldLabel: _t('Name'),
                    allowBlank: false,
                    regex: Zenoss.env.textMasks.allowedNameTextDash,
                    regexText: Zenoss.env.textMasks.allowedNameTextFeedbackDash,
                    blankText: _t('Name is a required field')
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    ref: '../submitNewDataPoint',
                    text: _t('Submit'),
                    formBind: true,
                    handler: function() {
                        var parameters = {
                            name: this.refOwner.metricName.getValue(),
                            dataSourceUid: selectedNode.data.uid
                        };
                        return router.addDataPoint(parameters, function() {
                            if (nodeId) {
                                me.refreshDataSourceGrid(nodeId);
                            } else {
                                me.refreshDataSourceGrid();
                            }
                        });
                    }
                },{
                    xtype: 'DialogButton',
                    text: _t('Cancel')
                }]
            }
        });
        win.show();
    },
    /**
     * Shows the Add Data Source dialog and saves the inputted information
     * back to the server
     **/
    showAddDataSourceDialog: function() {
        var cmp = Zenoss.getCmp(treeId, this),
            selectedNode = cmp.getSelectionModel().getSelectedNode(),
            templateUid,
            me = this;

        if (me.useTemplateSource) {
            templateUid = me.ownerCt.getContext();
            if (!templateUid) {
                new Zenoss.dialog.ErrorDialog({message: _t('There is no template to which to add a datasource.')});
                return;
            }
        } else {
            // make sure they selected a node
            if (!selectedNode) {
                new Zenoss.dialog.ErrorDialog({message: _t('You must select a template.')});
                return;
            }
            templateUid = selectedNode.data.uid;
        }

        var win = Ext.create('Zenoss.dialog.BaseWindow', {
            title: _t('Add Data Source'),
            height: 180,
            width: 350,
            items:[{
                xtype: 'form',
                buttonAlign: 'left',
                listeners: {
                    validitychange: function (form, isValid) {
                        if (isValid) {
                            this.ownerCt.query('button')[0].enable();
                        } else {
                            this.ownerCt.query('button')[0].disable();
                        }
                    }
                },
                items: [{
                    xtype: 'idfield',
                    ref: 'dataSourceName',
                    fieldLabel: _t('Name'),
                    allowBlank: false,
                    regex: Zenoss.env.textMasks.allowedNameTextDash,
                    regexText: Zenoss.env.textMasks.allowedNameTextFeedbackDash,
                    blankText: _t('Name is a required field')
                }, {
                    xtype: 'combo',
                    ref: 'dataSourceTypeCombo',
                    allowBlank: false,
                    displayField: 'type',
                    fieldLabel: _t('Type'),
                    editable: false,
                    value: 'SNMP',
                    triggerAction: 'all',
                    store: {
                        type: 'directcombo',
                        model: 'Zenoss.templates.DataSourceTypeModel',
                        root: 'data',
                        directFn: router.getDataSourceTypes
                    }
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    ref: '../submitNewDataSource',
                    disabled: true,
                    text: _t('Submit'),
                    handler: function () {
                        var parameters = {
                            name: this.refOwner.dataSourceName.getValue(),
                            type: this.refOwner.dataSourceTypeCombo.getValue(),
                            templateUid: templateUid
                        };
                        return router.addDataSource(parameters, me.refreshDataSourceGrid.bind(me));
                    }
                }, Zenoss.dialog.CANCEL]
            }]
        });
        win.show();
    },
    showAddToGraphDialog: function() {
        var me = this,
            templateUid = me.uid,
            node = me.getSelectionModel().getSelectedNode(),
            metricName, html;

        if ( node && node.isLeaf() ) {
            metricName = node.data.name;
            html = '<div>Data Point</div>';
            html += '<div>' + metricName + '</div><br/>';
            var graphStore = new Zenoss.GraphStore({});
            graphStore.setBaseParam('uid', templateUid);

            var win = Ext.create('Zenoss.dialog.BaseWindow', {
                width: 400,
                height: 250,
                title: _t('Add Data Point to Graph'),
                closeAction: 'destroy',
                items: [{
                    xtype: 'panel',
                    ref: 'addToGraphMetricPanel'
                }, {
                    xtype: 'combo',
                    ref: 'graphCombo',
                    fieldLabel: _t('Graph'),
                    displayField: 'name',
                    valueField: 'uid',
                    width:300,
                    minChars: 999, // only do an all query
                    resizeable: true,
                    editable: false,
                    emptyText: 'Select a graph...',
                    store: graphStore,
                    listeners: {
                        change: function(t, newVal, oldVal){
                            t.refOwner.submit.setDisabled(!newVal);
                        }
                    }
                }],
                buttons: [{
                    xtype: 'DialogButton',
                    ref: '../submit',
                    text: _t('Submit'),
                    disabled: true,
                    handler: function(t) {
                        var datapointUid, graphUid;
                        datapointUid = node.data.uid;
                        graphUid = t.refOwner.graphCombo.getValue();
                        addMetricToGraph(datapointUid, graphUid);
                    }
                }, {
                    xtype: 'DialogButton',
                    text: _t('Cancel')
                }]
            });
            win.show();

            win.addToGraphMetricPanel.body.update(html);
        } else {
            new Zenoss.dialog.ErrorDialog({message: _t('You must select a Data Point.')});
        }
    },
    /**
     * Event handler for editing a specific datasource or
     * datapoint.
     **/
    editDataSourceOrPoint: function() {
        var me = this,
            selectedNode = me.getSelectionModel().getSelectedNode(),
            data,
            isDataPoint = false,
            params, editingReSelectId;

        // make sure they selected something
        if (!selectedNode) {
            new Zenoss.dialog.ErrorDialog({message: _t('You must select a Data Source or Data Point.')});
            return;
        }
        data = selectedNode.data;

        // find out if we are editing a datasource or a datapoint
        if (data.leaf) {
            isDataPoint = true;
            editingReSelectId = selectedNode.parentNode.data.id;
        }else{
            editingReSelectId = data.id;
        }

        // parameters for the router call
        params = {
            uid: data.uid
        };

        function findSubObject(keyObj, array) {
            var p, key, val, ret;
            for (p in keyObj) {
                if (keyObj.hasOwnProperty(p)) {
                    key = p;
                    val = keyObj[p];
                }
            }
            for (p in array) {
                if (p == key) {
                    if (array[p] == val) {
                        return array;
                    }
                } else if (array[p] instanceof Object) {
                    if (array.hasOwnProperty(p)) {
                        ret = findSubObject(keyObj, array[p]);
                        if (ret) {
                            return ret;
                        }
                    }
                }
            }
            return null;
        };

        // callback for the router request
        function displayEditDialog(response) {
            var win, newId, config = {};

            config.record = response.record;
            config.items = response.form;
            config.id = editDataSourcesId;
            config.isDataPoint = isDataPoint;
            config.title = _t('Edit Data Source');
            config.directFn = router.setInfo;
            config.width = 800;

            newId = findSubObject({name:"newId"}, config)
            if (newId) {
                newId.inputAttrTpl = null;
                newId.regex = Zenoss.env.textMasks.allowedNameTextDash;
                newId.regexText = Zenoss.env.textMasks.allowedNameTextFeedbackDash;
            }

            if (isDataPoint) {
                config.title = _t('Edit Data Point');
                config.directFn = me.submitDataPointForm;
                config.singleColumn = true;
            } else if (config.record.testable &&
                       Zenoss.Security.hasPermission('Change Device')){
                // add the test against device panel
                config.items.items.push({
                    xtype:'panel',
                    columnWidth: 0.5,
                    baseCls: 'test-against-device',
                    hidden: Zenoss.Security.doesNotHavePermission('Run Commands'),
                    title: _t('Monitor Against a Device'),
                    items:[{
                        xtype: 'textfield',
                        fieldLabel: _t('Device Name'),
                        ref: '../testDevice',
                        width: 300,
                        name: 'testDevice'
                    },{
                        xtype: 'hidden',
                        name: 'uid',
                        value: response.record.id
                    },{
                        xtype: 'button',
                        text: _t('Monitor'),
                        ref: '../testDeviceButton',
                        handler: me.monitorDataSource
                    }]});

            }

            config.saveHandler = me.closeEditDialog.bind(me, editingReSelectId);
            win = new Zenoss.form.DataSourceEditDialog(config);
            var cmdField = win.editForm.form.findField('commandTemplate');
            if (cmdField !== null) {
                cmdField.addListener('dirtychange', function() {
                    // win.testDeviceButto.disable();
                    var devField = win.testDevice;
                    devField.setValue(_t("Save and reopen this dialog to test."));
                    devField.disable();
                });
            }
            win.show();
        }
        // get the details
        if (isDataPoint) {
            router.getDataPointDetails(params, displayEditDialog);
        }else{
            router.getDataSourceDetails(params, displayEditDialog);
        }
    },
    /**
     * Used when we save the data grid, it needs to
     * explicitly get the "Alias" value and turn it into a
     * list before going back to the server
     **/
    submitDataPointForm: function(values, callback) {
        // will always have only one alias form
        var aliases = Ext.getCmp(editDataSourcesId).query('alias'),
            alias;
        // assert that we have one exactly one alias form
        if (aliases.length < 1) {
            throw "The DataPoint form does not have an alias field, it should have only one";
        }

        alias = aliases[0];
        values.aliases = alias.getValue();
        router.setInfo(values, callback);
    },
    /**
     * Closes the edit dialog and updates the store of the datasources.
     * This is called after the router request to save the edit dialog
     **/
    closeEditDialog: function(nodeId, response) {
        if (!response.success) {
            return;
        }
        var dialog = Ext.getCmp(editDataSourcesId);
        this.refreshDataSourceGrid(nodeId);

        // hide the dialog
        if (dialog) {
            dialog.hide();
        }
    },
    /**
     * Event handler for when a user wants to test a datasource
     * against a specific device.
     **/
    monitorDataSource: function() {
        var cmp = Ext.getCmp(editDataSourcesId),
            values = cmp.editForm.form.getValues(),
            win, testDevice;

        testDevice = values.testDevice;

        win = new Zenoss.CommandWindow({
            uids: testDevice,
            title: _t('Monitor Data Source'),
            data: values,
            target: Zenoss.render.link(null, values.uid) + '/monitor_datasource'
        });

        win.show();
    },
    /**
     * Causes the DataSources Grid to refresh from the server
     *
     **/
    refreshDataSourceGrid: function(selectedId) {
        var grid = this,
            node = grid.getSelectionModel().getSelectedNode();
        selectedId = node && node.data.id || selectedId;
        if (selectedId) {
            grid.refresh(function(){
                grid.getRootNode().cascade(function(node){
                    if (node.data.id === selectedId) {
                        node.expand();
                        node.select();
                    }
                });
            });
        }else{
            this.refresh();
        }
    }

});



})();
