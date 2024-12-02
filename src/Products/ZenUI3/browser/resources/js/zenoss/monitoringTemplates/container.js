/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

Ext.ns('Zenoss', 'Zenoss.templates');

var REMOTE = Zenoss.remote.DeviceRouter;

/**
 * Updates the data store for the template tree. This will select the
 * first template when refreshed.
 **/
function refreshTemplateTree() {
    var cmp = Ext.getCmp('templateTree');
    if (cmp && cmp.isVisible()) {

        cmp.refresh(function() {
            // select the first node
            var root = cmp.getRootNode();

            if (root.firstChild) {
                cmp.getSelectionModel().select(root.firstChild);
            }
        });

    }
}

Ext.define("Zenoss.templates.Container", {
    alias:['widget.templatecontainer'],
    extend:"Ext.Panel",
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'border',
            defaults: {
                split: true
            },
            items: [{
                xtype: 'DataSourceTreeGrid',
                id: 'dataSourceTreeGrid',
                region: 'center',
                ref: 'dataSourceTreeGrid',
                uid: config.uid,
                root: {
                    uid: config.uid,
                    id: config.uid
                }
            }, {
                xtype: 'panel',
                layout: 'border',
                region: 'east',
                width: '35%',
                defaults: {
                    split: true
                },
                items: [{
                    xtype: 'thresholddatagrid',
                    id: 'thresholdGrid',
                    ref: '../thresholdGrid',
                    region: 'north',
                    height: 300
                }, {
                    xtype: 'graphgrid',
                    id: 'graphGrid',
                    ref: '../graphGrid',
                    region: 'center'
                }]
            }]
        });
        Zenoss.templates.Container.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        this.updateTreeGrid(this.dataSourceTreeGrid, uid);
        this.updateGrid(this.thresholdGrid, uid);
        this.updateGrid(this.graphGrid, uid);
    },
    updateTreeGrid: function(treeGrid, uid){
        treeGrid.setContext(uid);
    },
    updateGrid: function(grid, uid) {
        grid.setContext(uid);
    }
});


Zenoss.BubblingSelectionModel = Ext.extend(Zenoss.TreeSelectionModel, {
    constructor: function(config) {
        Zenoss.BubblingSelectionModel.superclass.constructor.call(this, config);
        this.enableBubble('selectionchange');
        this.bubbleTarget = config.bubbleTarget;
    },
    getBubbleTarget: function() {
        return this.bubbleTarget;
    }
});

Zenoss.MonTemplateSelectionModel = Ext.extend(Zenoss.BubblingSelectionModel, {
    constructor: function(config) {
        Ext.applyIf(config, {
            listeners: {
                beforeselect: function(sm, node) {
                    return node.isLeaf();
                }
            }
        });
        Zenoss.MonTemplateSelectionModel.superclass.constructor.call(this, config);
    }
});


Ext.define('Zenoss.templates.TemplateTreeModel', {
    extend: 'Zenoss.model.Tree',
    fields: [ 'text', 'uid'],
    getId: function() {
        return this.get("uid");
    },
    proxy: {
        simpleSortMode: true,
        type: 'direct',
        directFn: REMOTE.getTemplates,
        paramOrder: ['uid']
    }
});

Ext.define("Zenoss.templates.MonTemplateTreePanel", {
    alias:['widget.montemplatetreepanel'],
    extend:"Ext.tree.TreePanel",
    constructor: function(config){

        // create the model
        Ext.applyIf(config, {
            useArrows: true,
            manageHeight: false,
            cls: 'x-tree-noicon',
            model: 'Zenoss.model.Tree',
            selModel: new Zenoss.MonTemplateSelectionModel({
                bubbleTarget: config.bubbleTarget
            }),
            store: Ext.create('Ext.data.TreeStore', {
                model: 'Zenoss.templates.TemplateTreeModel',
                nodeParam: 'uid'
            }),
            hideHeaders: true,
            columns: [{
                xtype: 'treecolumn',
                flex: 1,
                dataIndex: 'text'
            }],
            root: {
                text: _t('Monitoring Templates')
            }
        });

        this.callParent([config]);
    },
    initComponent: function(){
        this.callParent(arguments);
        this.getStore().on('load', function() {
            this.getRootNode().expand();
        }, this);
    },
    setContext: function(uid, callback, scope) {
        this.uid = uid;
        if ( uid.match('^/zport/dmd/Devices') ) {
            this.show();
            var root = this.getRootNode();
            if (root) {
                root.data.uid = uid;
                this.getStore().load({
                    callback: callback,
                    scope: scope
                });
            }
        } else {
            this.hide();
        }
    },
    onSelectionChange: function(nodes) {
        var detail, node, uid;
        if (nodes && nodes.length) {
            node = nodes[0];
            uid = node.get("id");
            detail = Ext.getCmp(this.initialConfig.detailPanelId);
            if ( ! detail.items.containsKey('montemplate') ) {
                detail.add({
                    xtype: 'templatecontainer',
                    id: 'montemplate',
                    ref: 'montemplate',
                    uid: uid
                });
            }
            detail.montemplate.setContext(uid);
            detail.getLayout().setActiveItem('montemplate');
        }
    },
    refresh: function(callback, scope) {
        this.setContext(this.uid, callback, scope);
    }
});


Ext.define("Zenoss.BindTemplatesItemSelector", {
    alias:['widget.bindtemplatesitemselector'],
    extend:"Ext.ux.form.ItemSelector",
        constructor: function(config) {
        Ext.applyIf(config, {
            imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
            drawUpIcon: false,
            drawDownIcon: false,
            drawTopIcon: false,
            drawBotIcon: false,
            displayField: 'name',
            width: 380,
            valueField: 'id',
            store:  Ext.create('Ext.data.ArrayStore', {
                data: [],
                model: 'Zenoss.model.IdName',
                sorters: [{
                    property: 'value'
                }]
            })
        });
        Zenoss.BindTemplatesItemSelector.superclass.constructor.apply(this, arguments);
    },
    setContext: function(uid) {
        REMOTE.getUnboundTemplates({uid: uid}, function(provider, response){
            var data = response.result.data;
            // stack the calls so we can make sure the store is setup correctly first
            REMOTE.getBoundTemplates({uid: uid}, function(provider, response){
                var results = [];
                Ext.each(response.result.data, function(row){
                    results.push(row[0]);
                    data.push(row);
                });
                this.store.loadData(data);
                this.bindStore(this.store);
                this.setValue(results);
            }, this);
        }, this);

    }
});


Ext.define("Zenoss.AddLocalTemplatesDialog", {
    alias:['widget.addlocaltemplatesdialog'],
    extend:"Zenoss.HideFitDialog",
    constructor: function(config){
        var me = this;
        Ext.applyIf(config, {
            title: _t('Add Local Template'),
            layout: 'anchor',
            items: [{
                xtype: 'form',
                ref: 'formPanel',
                listeners: {
                    validitychange: function(formPanel, valid) {
                        me.submitButton.setDisabled( ! valid );
                    }
                },
                items: [{
                    xtype: 'idfield',
                    fieldLabel: _t('Name'),
                    ref: 'templateName',
                    context: config.context
                }]
            }],
            listeners: {
                show: function() {
                    this.formPanel.templateName.setValue('');
                }

            },
            buttons: [
            {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',
                ref: '../submitButton',
                text: _t('Submit'),
                handler: function() {
                    var templateId = me.formPanel.templateName.getValue();

                    REMOTE.addLocalTemplate({
                       deviceUid: me.context,
                       templateId: templateId
                    }, refreshTemplateTree);
                }
            }, {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',
                text: _t('Cancel')
            }]
        });
        Zenoss.AddLocalTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});


Ext.define("Zenoss.BindTemplatesDialog", {
    alias:['widget.bindtemplatesdialog'],
    extend:"Zenoss.HideFitDialog",
    constructor: function(config){
        var me = this;
        var itemId = Ext.id();

        Ext.applyIf(config, {
            width: 600,
            height: 400,
            title: _t('Bind Templates'),
            items: [{
                xtype: 'panel',
                width:  550,
                layout: 'column',
                defaults: {
                    columnWidth: 0.5
                },
                items: [{
                    xtype: 'label',
                    style: {'padding':'0 0 5px 7px'},
                    text: 'Available'
                },{
                    xtype: 'label',
                    style: {'padding':'0 0 5px 0'},
                    text: 'Selected'
                }]
            },{
                xtype: 'bindtemplatesitemselector',
                ref: 'itemselector',
                width:500,
                height:200,
                id: itemId,
                context: config.context
            }],
            listeners: {
                show: function() {
                    Ext.getCmp(itemId).setContext(this.context);
                }
            },
            buttons: [
            {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',
                text: _t('Save'),
                handler: function(){
                    var templateIds;
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        templateIds = Ext.getCmp(itemId).getValue();
                        REMOTE.setBoundTemplates({
                            uid: me.context,
                            templateIds: templateIds
                        }, refreshTemplateTree);
                    }
                }
            }, {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',
                text: _t('Cancel')
            }]
        });
        Zenoss.BindTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});


Ext.define("Zenoss.ResetTemplatesDialog", {
    alias:['widget.resettemplatesdialog'],
    extend:"Zenoss.MessageDialog",
    constructor: function(config) {
        var me = this;
        Ext.applyIf(config, {
            title: _t('Reset Template Bindings'),
            message: _t('Are you sure you want to delete all local template bindings and use default values?'),
            buttons: [
                {
                    xtype: 'HideDialogButton',
                    ui: 'dialog-dark',
                    text: _t('Reset Bindings'),
                    handler: function() {
                        if (Zenoss.Security.hasPermission('Manage DMD')) {
                            REMOTE.resetBoundTemplates(
                                { uid: me.context },
                                refreshTemplateTree);
                        }
                    }
                }, {
                    xtype: 'HideDialogButton',
                    ui: 'dialog-dark',
                    text: _t('Cancel')
                }
            ]
        });
        Zenoss.ResetTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});



Ext.define("Zenoss.OverrideTemplatesDialog", {
    alias:['widget.overridetemplatesdialog'],
    extend:"Zenoss.HideFitDialog",
    constructor: function(config){
        var me = this;
        Ext.applyIf(config, {
            height: 200,
            width: 300,
            title: _t('Override Templates'),
            listeners: {
                show: function() {
                    // completely reload the combobox every time
                    // we show the dialog
                    me.submit.setDisabled(true);
                    me.comboBox.setValue(null);
                    me.comboBox.store.setBaseParam('query', me.context);
                    me.comboBox.store.setBaseParam('uid', me.context);

                }
            },
            items: [{
                xtype: 'label',
                html: _t('Select the bound template you wish to override.')
            },{
                xtype: 'combo',
                forceSelection: true,
                emptyText: _t('Select a template...'),
                minChars: 0,
                ref: 'comboBox',
                selectOnFocus: true,
                typeAhead: true,
                valueField: 'uid',
                displayField: 'label',
                listConfig: {
                    resizable: true
                },
                store: Ext.create('Zenoss.NonPaginatedStore', {
                    root: 'data',
                    model: 'Zenoss.model.Label',
                    directFn: REMOTE.getOverridableTemplates
                }),
                listeners: {
                    select: function(){
                        // disable submit if nothing is selected
                        me.submit.setDisabled(!me.comboBox.getValue());
                    }
                }
            }],
            buttons: [
            {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',
                ref: '../submit',
                disabled: true,
                text: _t('Submit'),
                handler: function(){
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        var templateUid = me.comboBox.getValue();
                        Zenoss.remote.TemplateRouter.copyTemplate({
                            uid: templateUid,
                            targetUid: me.context
                        }, refreshTemplateTree);
                    }
                }
            }, {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',
                text: _t('Cancel')
            }]
        });
        Zenoss.OverrideTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});


Ext.define("Zenoss.removeLocalTemplateDialog", {
    alias:['widget.removelocaltemplatesdialog'],
    extend:"Zenoss.HideFitDialog",
    constructor: function(config){
        var me = this;
        Ext.applyIf(config, {
            height: 200,
            width: 300,
            title: _t('Remove Local Template'),
            listeners: {
                show: function() {
                    // completely reload the combobox every time
                    // we show the dialog
                    me.submit.setDisabled(true);
                    me.comboBox.setValue(null);
                    me.comboBox.store.setBaseParam('query', me.context);
                    me.comboBox.store.setBaseParam('uid', me.context);
                }
            },
            items: [{
                xtype: 'label',
                html: _t('Select the locally defined template you wish to remove.')
            },{
                xtype: 'combo',
                forceSelection: true,
                width: 200,
                emptyText: _t('Select a template...'),
                minChars: 0,
                ref: 'comboBox',
                selectOnFocus: true,
                valueField: 'uid',
                displayField: 'label',
                typeAhead: true,
                store: Ext.create('Zenoss.NonPaginatedStore', {
                    root: 'data',
                    model: 'Zenoss.model.Label',
                    directFn: REMOTE.getLocalTemplates
                }),
                listeners: {
                    select: function(){
                        // disable submit if nothing is selected
                        me.submit.setDisabled(!me.comboBox.getValue());
                    }
                }
            }],
            buttons: [
            {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',
                ref: '../submit',
                disabled: true,
                text: _t('Submit'),
                handler: function(){
                    if (Zenoss.Security.hasPermission('Manage DMD')) {
                        var templateUid = me.comboBox.getValue();
                        REMOTE.removeLocalTemplate({
                            deviceUid: me.context,
                            templateUid: templateUid
                        }, refreshTemplateTree);
                    }
                }
            }, {
                xtype: 'HideDialogButton',
                ui: 'dialog-dark',
                text: _t('Cancel')
            }]
        });
        Zenoss.OverrideTemplatesDialog.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.context = uid;
    }
});


})();
