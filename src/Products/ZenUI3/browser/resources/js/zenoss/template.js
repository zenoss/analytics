/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.onReady(function(){

var router, treeId, dataSourcesId, thresholdsId, graphsId,
    beforeselectHandler, updateDataSources, updateThresholds, updateGraphs,
    selectionchangeHandler, selModel, footerBar, override, overrideHtml1,
    overrideHtml2, showOverrideDialog, resetCombo, addTemplateDialogConfig;


Ext.ns('Zenoss', 'Zenoss.templates');
router = Zenoss.remote.TemplateRouter;
treeId = 'templateTree';
dataSourcesId = 'dataSourceTreeGrid';
thresholdsId = Zenoss.templates.thresholdsId;
graphsId = 'graphGrid';

resetCombo = function(combo, uid) {
    combo.clearValue();
    combo.store.setContext(uid);
};

/**
 * Returns which of the two views that the user has selected. Can be
 * either:
 * 1. "template" : the default view where nodes are templates and leaves are device classes
 * 2. "deviceClass" : leaves are templates and nodes are deviceClasses
 **/
function getCurrentView(){
    var currentView = Ext.state.Manager.get('template_view');

    if (Ext.History.getToken() && Ext.History.getToken().search('/devices/') !== -1) {
        return 'template';
    }
    if (currentView) {
        return currentView;
    }
    currentView = 'template';
    Ext.state.Manager.set('template_view', currentView);
    return currentView;
}

/**
 * Will set the state for the default view. This will cause a page reload.
 **/
function setDefaultView(view) {
    var currentView = getCurrentView();
    if (currentView !== view){
        Ext.state.Manager.set('template_view', view);
        // make sure the state is saved before reloading
        Ext.state.Manager.provider.saveStateNow(function() {
            window.location = "/zport/dmd/template";
        });
    }
}

function reloadTree(selectedId) {
    var tree = Ext.getCmp(treeId);
    if (selectedId){
        tree.getStore().load({
            callback: function() {
                tree.getRootNode().childNodes[0].expand();
                tree.selectByToken(selectedId);
            }
        });
    }else{
        // select the first node
        tree.getStore().load({
            callback: function(){
                tree.getRootNode().childNodes[0].expand();
                tree.getRootNode().childNodes[0].childNodes[0].select();
            }
        });
    }
}

beforeselectHandler = function(sm, node) {
    return node.isLeaf();
};

updateDataSources = function(uid) {
    var panel = Ext.getCmp('center_detail_panel'),
        treeGrid = Zenoss.getCmp(dataSourcesId, panel);

    if (!treeGrid) {
        treeGrid = panel.add({
            xtype: 'DataSourceTreeGrid',
            uid: uid,
            root: {
                id: uid,
                uid: uid
            }
        });
    }
    // create a new async node since we may have had a dummy one
    treeGrid.setContext(uid);
};

updateThresholds = function(uid) {
    var panel;
    panel = Ext.getCmp('top_detail_panel');

    if ( ! Ext.getCmp(thresholdsId) ) {
        panel.add({id: thresholdsId, xtype:'thresholddatagrid'});
        panel.doLayout();
    }
    Ext.getCmp(thresholdsId).setContext(uid);
};

updateGraphs = function(uid) {
    var panel = Ext.getCmp('bottom_detail_panel'),
        graphGrid = Zenoss.getCmp(graphsId, panel);

    if (!graphGrid ) {
        graphGrid = panel.add({
            xtype: 'graphgrid',
            itemId: graphsId
        });
        panel.doLayout();
    }
    graphGrid.setContext(uid);
};


selectionchangeHandler = function(sm, nodes) {
    var node;
    if (nodes){
        // only single select
        node = nodes[0];
        updateDataSources(node.data.uid);
        updateThresholds(node.data.uid);
        updateGraphs(node.data.uid);
        // set the context for the id fields (they validate their id against this context)
        Zenoss.env.PARENT_CONTEXT = node.data.uid;
        // unfortunately because multiple templates exist on device class view we
        // have to track the history differently
        if (getCurrentView() === Zenoss.templates.templateView){
            Ext.History.add(treeId + Ext.History.DELIMITER + node.get("uid"));
        }else {
            Ext.History.add(treeId + Ext.History.DELIMITER + node.get("id"));
        }
    }

    // enable the footer bar buttons
    var footerBar = Ext.getCmp('footer_bar');
    footerBar.buttonContextMenu.setDisabled(!node);
    footerBar.buttonDelete.setDisabled(!node);
    footerBar.buttonAdd.setTooltip(_t('Add a monitoring template'));

    // disable/enable the add buttons
    Zenoss.getCmp(thresholdsId, footerBar).addButton.setDisabled(!node);
    Zenoss.getCmp(graphsId, footerBar).addButton.setDisabled(!node);
    Zenoss.getCmp(dataSourcesId, footerBar).disableToolBarButtons(!node);
};

selModel = new Zenoss.TreeSelectionModel({
    listeners: {
        beforeselect: beforeselectHandler,
        selectionchange: selectionchangeHandler
    }
});

Ext.getCmp('master_panel').add({
    xtype: 'HierarchyTreePanelSearch',
    items:[{
        xtype: 'TemplateTreePanel',
        selModel: selModel,
        enableDragDrop: false,
        currentView: getCurrentView()
    }]
});


/**********************************************************************
 *
 * Edit Template Information
 *
 */

/**
 * Shows the edit template dialog and sends the form values back to the server.
 **/
function showEditTemplateDialog(response) {
    var config, dialog, handler,
        data = response.data,
        dirtyOnly = true;

    // save function (also reloads the tree, in case we change the name)
    handler = function() {
        var values = Ext.getCmp('editTemplateDialog').editForm.getForm().getValues(false, dirtyOnly);
        values.uid = data.uid;
        router.setInfo(values, function(response){
            reloadTree(response.data.uid);
        });
    };

    // form config
    config = {
        submitHandler: handler,
        id: 'editTemplateDialog',
        height: 350,
        title: _t('Edit Template Details'),
        items: [{
            xtype: 'textfield',
            name: 'newId',
            width: 300,
            fieldLabel: _t('Name'),
            allowBlank: false,
            ref: 'templateName'
        },{
            xtype: 'textfield',
            name: 'targetPythonClass',
            width: 300,
            fieldLabel: _t('Target Class'),
            allowBlank: true,
            ref: 'targetPythonClass'
        },{
            xtype: 'textarea',
            name: 'description',
            width: 300,
            fieldLabel: _t('Description'),
            ref: 'description'
        }]
    };

    dialog = new Zenoss.SmartFormDialog(config);

    // populate the form
    dialog.editForm.templateName.setValue(data.name);
    dialog.editForm.targetPythonClass.setValue(data.targetPythonClass);
    dialog.editForm.description.setValue(data.description);
    dialog.show();
}

/**
 * Gets the selected template information from the server
 **/
function editSelectedTemplate() {
    var params = {
        uid: Ext.getCmp(treeId).getSelectionModel().getSelectedNode().data.uid
    };

    router.getInfo(params, showEditTemplateDialog);
}
/**********************************************************************
 *
 * Override Templates
 *
 */
override = function() {
    var node, params, callback;
    node = Ext.getCmp('templateTree').getSelectionModel().getSelectedNode();
    params = {
        uid: node.data.uid,
        targetUid: Ext.getCmp('targetCombo').getValue()
    };
    callback = function() {
        reloadTree();
    };
    router.copyTemplate(params, callback);
};

overrideHtml1 = function() {
    var html;
    html = _t('Do you wish to copy (override) the selected monitoring template? This will affect all devices using the monitoring template.');
    html += '<br/><br/>';
    return html;
};

overrideHtml2 = function() {
    var html;
    html = _t('If new thresholds, graphs, are added or removed, or datasources added or disabled, these will be saved to this local copy of template.');
    html += '<br/><br/>';
    html += _t('Copied templates will override identically named templates at higher levels.');
    return html;
};

/**
 *  Simple uid, label model used to the override targets
 **/
Ext.define("Zenoss.model.UidLabel", {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: ['uid', 'label']
});

new Zenoss.HideFormDialog({
    id: 'overrideDialog',
    title: _t('Copy / Override'),
    width: 500,
    items: [
    {
        xtype: 'panel',
        html: overrideHtml1()
    }, {
        xtype: 'button',
        ui:'dialog-dark',
        id: 'learnMore',
        text: _t('Learn more'),
        handler: function() {
            Ext.getCmp('learnMore').hide();
            Ext.getCmp('detailedExplanation').show();
        }
    }, {
        xtype: 'panel',
        id: 'detailedExplanation',
        html: overrideHtml2(),
        hidden: true
    }, {
        xtype: 'panel',
        html: '<br/>'
    }, {
        xtype: 'combo',
        id: 'targetCombo',
        fieldLabel: _t('Target'),
        quickTip: _t('The selected monitoring template will be copied to the specified device class or device.'),
        forceSelection: true,
        emptyText: _t('Select a target...'),
        minChars: 0,
        selectOnFocus: true,
        valueField: 'uid',
        displayField: 'label',
        typeAhead: true,
        allowBlank: false,
        width: 450,
        store: Ext.create('Zenoss.NonPaginatedStore', {
            root: 'data',
            autoLoad: false,
            directFn: router.getCopyTargets,
            model: 'Zenoss.model.UidLabel'
        }),
        listeners: {
            validitychange: function(combo, isValid){
                var window = Ext.getCmp('overrideDialog');
                if (window.isVisible()) {
                    Ext.getCmp('overrideDialog').submit.setDisabled(!isValid);
                }
            }
        }
    }],
    buttons: [
    {
        xtype: 'HideDialogButton',
        ref: '../submit',
        text: _t('Submit'),
        handler: function() {
            override();
        }
    }, {
        xtype: 'HideDialogButton',
        text: _t('Cancel')
    }]
});

showOverrideDialog = function() {
    var sm, uid, combo;
    sm = Ext.getCmp('templateTree').getSelectionModel();
    uid = sm.getSelectedNode().get("uid");
    Ext.getCmp('overrideDialog').show();
    combo = Ext.getCmp('targetCombo');
    resetCombo(combo, uid);
    Ext.getCmp('overrideDialog').submit.disable();
};

function bindSelectedTemplateHere() {
    var node = Ext.getCmp(treeId).getSelectionModel().getSelectedNode(),
    remote = Zenoss.remote.DeviceRouter,
    callback, path,
    params, uid;

    if (getCurrentView() === Zenoss.templates.deviceClassView) {
        uid = node.parentNode.data.uid;
    }else {
        // template view
        uid = node.data.uid.replace(/rrdTemplates\/(.)*$/, '');
    }
    path = node.data.id;
    callback = function(response){
        if (response.success) {
            reloadTree(path);
        }
    };
    params = {
        uid: uid,
        templateUid: node.data.uid
    };
    remote.bindOrUnbindTemplate(params, callback);
}

/**********************************************************************
 *
 * Footer Bar
 *
 */
addTemplateDialogConfig = {
    title: _t('Add Template'),
    id: 'addNewTemplateDialog',
    height: 250,
    width: 450,
    listeners: {
        show: function() {
            var cmp = Ext.getCmp('addNewTemplateDialog');
            // completely reload the combobox every time
            // we show the dialog
            cmp.comboBox.setValue(null);
        }
    },
    items: [{
        xtype: 'textfield',
        name: 'id',
        fieldLabel: _t('Name'),
        anchor: '80%',
        allowBlank: false
    }, {
        xtype: 'combo',
        anchor: '80%',
        fieldLabel: _t('Template Path'),
        forceSelection: true,
        width: 250,
        emptyText: _t('Select a template path...'),
        minChars: 0,
        queryMode: 'remote',
        ref: '../comboBox',
        selectOnFocus: true,
        typeAhead: true,
        listConfig: {
            resizable: true
        },
        displayField: 'label',
        valueField: 'uid',
        name: 'targetUid',
        store: Ext.create('Zenoss.NonPaginatedStore', {
            root: 'data',
            autoLoad: true,
            directFn: router.getAddTemplateTargets,
            model: 'Zenoss.model.UidLabel'
        })
    }]
};

/**********************************************************************
 *
 * Add to zenpack
 *
 */
function showAddToZenPackDialog() {
    var tree = Ext.getCmp(treeId),
        win = Ext.create('Zenoss.AddToZenPackWindow',  {});
    win.target = tree.getSelectionModel().getSelectedNode().data.uid;
    win.show();
}

footerBar = Ext.getCmp('footer_bar');
Zenoss.footerHelper(_t('Monitoring Template'),
                    footerBar, {
                        hasOrganizers: false,
                        addToZenPack: false,
                        customAddDialog: addTemplateDialogConfig
                    });

footerBar.buttonContextMenu.menu.add({
    text: _t('View and Edit Details'),
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    handler: editSelectedTemplate
},{
    xtype: 'menuitem',
    text: _t('Copy / Override Template'),
    handler: showOverrideDialog
},{
    xtype: 'menuitem',
    text: _t('Add to ZenPack'),
    handler: showAddToZenPackDialog

},{
    text: _t('Toggle Template Binding'),
    hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    handler: bindSelectedTemplateHere
});

footerBar.on('buttonClick', function(actionName, id, values) {
    var params, tree = Ext.getCmp(treeId);
    switch (actionName) {
        case 'addClass':
            params = {
                id: values.id,
                targetUid: values.targetUid
            };
            router.addTemplate(params, function(response) {
                reloadTree(response.nodeConfig.uid);
            });
        break;
        case 'delete':
            params = {
                uid: Ext.getCmp(treeId).getSelectionModel().getSelectedNode().data.uid
            };
            router.deleteTemplate(params,
            function(){
                reloadTree();
                tree.clearFilter();
                footerBar.buttonDelete.setDisabled(true);
                footerBar.buttonContextMenu.setDisabled(true);
            });
        break;
        default:
        break;
    }
});

/**
 * Add the view buttons
 **/

footerBar.add([{
    xtype: 'tbtext',
    text: _t('Group By: ')
    },' ',{
    xtype: 'button',
    enableToggle: true,
    toggleGroup: 'templateView',
    pressed: getCurrentView() === Zenoss.templates.templateView,
    text: _t('Template'),
    toggleHandler: function(button, state) {
        if (state) {
            setDefaultView(Zenoss.templates.templateView);
        } else {
            // stay pressed, but don't do anything
            this.toggle(true, true);
        }

    }
},{
    xtype: 'button',
    enableToggle: true,
    pressed: getCurrentView() === Zenoss.templates.deviceClassView,
    toggleGroup: 'templateView',
    text: _t('Device Class'),
    toggleHandler: function(button, state) {
        if (state) {
            setDefaultView(Zenoss.templates.deviceClassView);
        } else {
            // stay pressed, but don't do anything
            this.toggle(true, true);
        }
    }
}]);


    footerBar.add(['-',{
        xtype: 'tbtext',
        text: _t('Bound:')
    },{
        xtype: 'tbtext',
        cls: 'x-tree-node-icon tree-template-icon-bound-span'
    }, ' ', {
        xtype: 'tbtext',
        text: _t('Component:')
    }, {
        xtype: 'label',
        cls: 'x-tree-node-icon tree-template-icon-component-span'
    }]);

}); // Ext.onReady
