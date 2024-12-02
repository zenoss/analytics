/* global unescape: true, FileReader:true */
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


// Script for the processes page.

Ext.onReady(function(){

Ext.Loader.setConfig({enabled:true});
Ext.ns('Zenoss', 'Zenoss.env');
var treeId = 'processTree';
var router = Zenoss.remote.ProcessRouter;

new Zenoss.MessageDialog({
    id: 'dirtyDialog',
    title: _t('Unsaved Data'),
    message: _t('The changes made in the form will be lost.'),
    okHandler: function() {
        Ext.getCmp('processForm').getForm().reset();
        Zenoss.env.node.getOwnerTree().getSelectionModel().select(Zenoss.env.node);
    }
});

/* ***************************************************************************
 *
 *   master_panel - the processes tree on the left
 *
 */

function beforeselectHandler(sm, node, oldNode) {
    if (node === oldNode) {
        return false;
    }
    if ( Ext.getCmp('processForm').getForm().isDirty() ) {
        // the user made changes to the form make sure that they don't care
        // about losing those changes
        Zenoss.env.node = node;
        Ext.getCmp('dirtyDialog').show();
        return false;
    }
    return true;
}

// function that gets run when the user clicks on a node in the tree
function selectionchangeHandler(sm, nodes) {
    if (nodes.length) {
        // load up appropriate data in the form
        var node = nodes[0],
            uid = node.get("uid"),
            grid = Ext.getCmp('navGrid');
        Ext.getCmp('processForm').setContext(uid);
        Ext.getCmp('detailCardPanel').setContext(uid);
        Ext.getCmp('footer_bar').setContext(uid);
        // don't allow the user to delete the root node
        Ext.getCmp('footer_bar').buttonDelete.setDisabled(
                node === Ext.getCmp(treeId).root);
        // refresh the process class grid
        grid.getSelectionModel().clearSelections();

        grid.setContext(node.get("uid"));
    }
}

var MoveProcessCallback = Ext.extend(Object, {
    constructor: function(tree, node) {
        this.tree = tree;
        this.node = node;
        MoveProcessCallback.superclass.constructor.call(this);
    },
    call: function(provider, response) {
        var node = this.node,
            tree = this.tree;
        node.setId(response.result.id);
        node.data.uid = response.result.uid;
        tree.refresh();

        Ext.History.add(tree.id + Ext.History.DELIMITER + node.get("id"));
    }
});

var ProcessTreePanel = Ext.extend(Zenoss.HierarchyTreePanel, {

    constructor: function(config) {
        Ext.applyIf(config, {
            id: treeId,
            searchField: true,
            cls: 'x-tree-noicon',
            directFn: router.getTree,
            router: router,
            selModel: new Zenoss.TreeSelectionModel({
                listeners: {
                    beforeselect: beforeselectHandler,
                    selectionchange: selectionchangeHandler
                }
            }),
            listeners: {
                scope: this,
                expandnode: this.onExpandnode
            },
            root: {
                id: 'Processes',
                uid: '/zport/dmd/Processes'
            },
            ddGroup: 'processDragDrop',
            viewConfig: {
                listeners: {
                    beforedrop: Ext.bind(this.onNodeDrop, this)
                }
            }
        });
        ProcessTreePanel.superclass.constructor.call(this, config);
    },
    onNodeDrop: function(element, event, target) {
        var uid, targetUid, params, callback, dropped;
        dropped = event.records[0];
        uid = dropped.get("uid");
        targetUid = target.get("uid");
        params = {uid: uid, targetUid: targetUid};
        callback = new MoveProcessCallback(this, dropped);
        router.moveProcess(params, callback.call, callback);
        return true;
    },

    onExpandnode: function(node) {
        if (node.id === '.zport.dmd.Processes') {
            // the root node has been loaded from the server.  All the nodes
            // in this TreePanel have been registered and the getNodeById
            // method will now return a node instance instead of null.
            var token = Ext.History.getToken();
            if (token) {
                var nodeId = unescape(token.split(Ext.History.DELIMITER).slice(1));
                var organizers = nodeId.split('.osProcessClasses.')[0].split('.').slice(4);
                var orgId = '.zport.dmd.Processes';
                // expand each of the organizers leading to the node in the token
                Ext.each(organizers, function(org) {
                    orgId += '.' + org;
                    this.getNodeById(orgId).expand();
                }, this);
                this.selectByToken(nodeId);
            }
        }
    },

    selectByToken: function(nodeId) {
        var tokenParts;
        // called from Ext.History.selectByToken defined in HistoryManager.js
        // overrides HierarchyTreePanel method
        tokenParts = nodeId.split('.osProcessClasses.');
        if (tokenParts[0]) {
            this.callParent([tokenParts[0]]);
        }

        if (tokenParts[1]) {
            Ext.getCmp('navGrid').filterAndSelectRow(tokenParts[1]);
        }

        // node is null prior to the TreePanel load event firing for the root
        // node with the id .zport.dmd.Processes (the id that comes from the
        // server). In this case the correct node will be selected once that
        // event fires and the onLoad method is called.
    }

});

/**
 * @class Zenoss.process.ProcessModel
 * @extends Ext.data.Model
 * Field definitions for processes
 **/
Ext.define('Zenoss.process.ProcessModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        {name:'name', type:'string'},
        {name:'description', type:'string'},
        {name:'count', type:'integer'},
        {name:'uid', type:'string'}
    ]
});

/**
 * @class Zenoss.process.ProcessStore
 * @extend Zenoss.DirectStore
 * Direct store for loading processes
 */
Ext.define("Zenoss.process.ProcessStore", {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.process.ProcessModel',
            initialSortColumn: "name",
            directFn: Zenoss.remote.ProcessRouter.query,
            root: 'processes',
            pageSize: 400
        });
        this.callParent(arguments);
    }
});


Ext.define("Zenoss.process.ProcessGrid", {
    extend:"Zenoss.FilterGridPanel",
    alias: ["widget.processgrid"],
    constructor: function(config) {
        Ext.applyIf(config, {
            id: 'navGrid',
            scroll: "vertical",
            viewConfig: {
                plugins: {
                    ptype: 'gridviewdragdrop',
                    ddGroup: 'processDragDrop'
                }
            },
            rowSelectorDepth: 5,
            store: Ext.create('Zenoss.process.ProcessStore', {}),
            selModel: new Zenoss.ExtraHooksSelectionModel({
                singleSelect: true,
                listeners: {
                    select: function(sm, record) {
                        var uid = record.data.uid, token, tokenParts, cardpanel;
                        cardpanel = Ext.getCmp('detailCardPanel');
                        Ext.getCmp('processForm').setContext(uid);
                        cardpanel.setContext(uid);
                        Ext.getCmp('footer_bar').setContext(uid);
                        // add to history
                        token = Ext.History.getToken();
                        if ( ! token ) {
                            token = treeId + ':' + Ext.getCmp(treeId).getRootNode().data.uid.replace(/\//g, '.');
                        }
                        tokenParts = token.split('.osProcessClasses.');
                        if ( tokenParts[1] !== record.data.name ) {
                            Ext.History.add( tokenParts[0] + '.osProcessClasses.' + record.data.name);
                        }
                    }
                }
            }),
            forceFit: true,
            columns: [ {
                dataIndex : 'name',
                header : _t('Process Class Name'),
                flex: 1,
                id : 'name'
            },{
                dataIndex : 'count',
                header : _t('Set Count'),
                filter: false,
                flex: 0,
                width: 100,
                id : 'count'
            }]
        });
        this.callParent(arguments);
        // preselect first record on store load;
        this.store.on('load', function(store, records) {
            this.getSelectionModel().select(records[0]);
        }, this);
    },

    filterAndSelectRow: function(serviceClassName) {
        var selections, selectedRecord;
        if (serviceClassName) {
            // the token includes a ServiceClass. Filter the grid
            // using the name of the ServiceClass and select the
            // correct row.
            selections = this.getSelectionModel().getSelection();
            if (selections.length) {
                selectedRecord = selections[0];
            }

            if ( ! selectedRecord || selectedRecord.data.name !== serviceClassName ) {
                this.serviceClassName = serviceClassName;
                this.getStore().on('datachanged', this.filterGrid, this, {single: true});
            }
        }else{
            this.setFilter('name', '');
        }
    },
    filterGrid: function() {
        var me = this,
        serviceClassName = this.serviceClassName;
        if (!serviceClassName) {
            return;
        }
        // look for it in our current store
        function selectrow() {
            var found = false;
            me.getStore().each(function(record){
                if (record.get("name") === serviceClassName) {
                    me.getSelectionModel().select(record);
                    found = true;
                }
            });
            return found;
        }
        if (!selectrow()) {
            // otherwise filter for it and find the service then
            this.setFilter('name', serviceClassName);
            this.getStore().on('datachanged', selectrow, this, {single: true});
        }
    },
    deleteSelectedRow: function() {
        var row = this.getSelectionModel().getSelected(),
        me = this;
        if (!row){
            return;
        }
        var uid = row.data.uid;
        router.deleteNode({uid:uid}, function(){
            me.refresh();
        });
    }
});

var panel = new Ext.Panel({
    layout: {
        type: 'border',
        align: 'stretch'
    },
    items:[
        {
            xtype: 'panel',
            split: true,
            region: "center",
            flex: 1,
            autoScroll: true,
            bodyStyle: {
                backgroundColor: "#d4e0ee"
            },
            items: [new ProcessTreePanel({})]
        },{
            xtype: "processgrid",
            region: "south",
            flex: 1,
            split: true,
            autoScroll: true
        }
    ]
});



/* **************************************************************************
 *
 *   top_detail_panel - the process form on the top right
 *
 */

// when the form loads, show/hide the regex fieldset
function actioncompleteHandler(basicForm, action) {
    if (action.type === 'directload') {
        var formPanel = Ext.getCmp('processForm');
        formPanel.isLoadInProgress = false;
        var processInfo = action.result.data;
        // disabling the forms will disable all of the elements in it
        if ( Zenoss.Security.doesNotHavePermission('Manage DMD') ) {
            formPanel.disable();
        }
        var isRoot = processInfo.name === 'Processes';
        Ext.getCmp('nameTextField2').setDisabled(isRoot);
        Ext.getCmp('regexIncludeTextField').setDisabled(!processInfo.hasRegex).allowBlank = !processInfo.hasRegex;
        Ext.getCmp('regexExcludeTextField').setDisabled(!processInfo.hasRegex);
        Ext.getCmp('regexReplaceTextField').setDisabled(!processInfo.hasRegex);
        Ext.getCmp('replacementTextField').setDisabled(!processInfo.hasRegex);
        var regexFieldSet = Ext.getCmp('regexFieldSet');
        regexFieldSet.setVisible(processInfo.hasRegex);
    } else if (action.type === 'directsubmit') {
        var processTree = Ext.getCmp(treeId);
        var selectionModel = processTree.getSelectionModel();
        var selectedNode = selectionModel.getSelectedNode();
        var nameTextField = Ext.getCmp('nameTextField2');
        if(selectedNode.data.text.text !== nameTextField.getValue()){
            selectedNode.data.text.text = nameTextField.getValue();
            Ext.getCmp('navGrid').refresh();
            processTree.refresh();
        }
        Ext.getCmp('detail_panel').detailCardPanel.setContext(selectedNode.data.uid);
    }
}

var nameTextField2 = {
    xtype: 'textfield',
    id: 'nameTextField2',
    fieldLabel: _t('Process Class Name'),
    name: 'name',
    allowBlank: false
};

var descriptionTextField = {
    xtype: 'textarea',
    fieldLabel: _t('Description'),
    name: 'description',
    grow: true
};

var regexIncludeTextField = {
    xtype: 'textfield',
    id: 'regexIncludeTextField',
    fieldLabel: _t('Include processes like'),
    name: 'includeRegex',
    allowBlank: false
};

var regexExcludeTextField = {
    xtype: 'textfield',
    id: 'regexExcludeTextField',
    fieldLabel: _t('Exclude processes like'),
    name: 'excludeRegex',
    allowBlank: true
};

var regexReplaceTextField = {
    xtype: 'textfield',
    id: 'regexReplaceTextField',
    fieldLabel: _t('Replace command line text'),
    name: 'replaceRegex',
    allowBlank: true
};

var replacementTextField = {
    xtype: 'textfield',
    id: 'replacementTextField',
    fieldLabel: _t('With'),
    name: 'replacement',
    allowBlank: true
};

var minCountThreshold = {
    xtype: 'numberfield',
    id: 'minProcessCount',
    fieldLabel: _t("Minimum"),
    name: 'minProcessCount',
    allowBlank: true
};

var maxCountThreshold = {
    xtype: 'numberfield',
    id: 'maxProcessCount',
    fieldLabel: _t("Maximum"),
    name: 'maxProcessCount',
    allowBlank: true
};

var minProcessMemoryThreshold = {
    xtype: 'numberfield',
    id: 'minProcessMemory',
    fieldLabel: _t('Minimum'),
    name: 'minProcessMemory',
    allowBlank: true
};

var maxProcessMemoryThreshold = {
    xtype: 'numberfield',
    id: 'maxProcessMemory',
    fieldLabel: _t('Maximum'),
    name: 'maxProcessMemory',
    allowBlank: true
};

var zMonitor = {
    xtype: 'zprop',
    ref: '../../zMonitor',
    title: _t('Enable Monitoring? (zMonitor)'),
    name: 'zMonitor',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        displayField: 'name',
        valueField: 'value',
        store: new Ext.data.ArrayStore({
            data: [['Yes', true], ['No', false]],
            model: 'Zenoss.model.NameValue'
        })
    }
};

var zAlertOnRestart = {
    xtype: 'zprop',
    ref: '../../zAlertOnRestart',
    title: _t('Send Event on Restart? (zAlertOnRestart)'),
    name: 'zAlertOnRestart',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        displayField: 'name',
        valueField: 'value',
        store: new Ext.data.ArrayStore({
            data: [['Yes', true], ['No', false]],
            model: 'Zenoss.model.NameValue'
        })
    }
};

var zFailSeverity = {
    xtype: 'zprop',
    ref: '../../zFailSeverity',
    title: _t('Failure Event Severity (zFailSeverity)'),
    name: 'zFailSeverity',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        store: Zenoss.env.SEVERITIES.slice(0, 5)
    }
};

var zModelerLock = {
    xtype: 'zprop',
    ref: '../../zModelerLock',
    title: _t('Lock Process Components? (zModelerLock)'),
    name: 'zModelerLock',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        displayField: 'name',
        valueField: 'value',
        store: new Ext.data.ArrayStore({
            data: [['Unlocked', 0], [_t('Lock from Deletes'), 1], [_t('Lock from Updates'), 2]],
            model: 'Zenoss.model.NameValue'
        })
    }
};

var zSendEventWhenBlockedFlag = {
    xtype: 'zprop',
    ref: '../../zSendEventWhenBlockedFlag',
    title: _t('Send an event when action is blocked? (zSendEventWhenBlockedFlag)'),
    name: 'zSendEventWhenBlockedFlag',
    localField: {
        xtype: 'select',
        queryMode: 'local',
        displayField: 'name',
        valueField: 'value',
        store: new Ext.data.ArrayStore({
            data: [['Yes', true], ['No', false]],
            model: 'Zenoss.model.NameValue'
        })
    }
};

var regexFieldSet = {
    xtype: 'fieldset',
    id: 'regexFieldSet',
    title: _t('Matching Rules (performance metrics will start over if changed)'),
    hidden: true,
    style: 'padding: 5px 0 0 0',
    anchor: '100%',
    defaults: {anchor:'97%'},
    items: [
        regexIncludeTextField,
        regexExcludeTextField,
        regexReplaceTextField,
        replacementTextField
    ]
}; // regexFieldSet

var processCountThreshold = {
    xtype: 'fieldset',
    id: 'processCountFieldSet',
    title: _t("Process Count Threshold"),
    hidden: false,
    style: 'padding: 5px 0 0 0',
    items: [
        minCountThreshold,
        maxCountThreshold
    ]
}; // processCountThreshold

var processMemoryThreshold = {
    xtype: 'fieldset',
    id: 'processMemoryFieldSet',
    title: _t("Process Memory Threshold (bytes)"),
    hidden: false,
    style: 'padding: 5px 0 0 0',
    items: [
        minProcessMemoryThreshold,
        maxProcessMemoryThreshold
    ]
}; // processMemoryThreshold

// the items that make up the form
var processFormItems = {
    layout: 'column',
    autoScroll: true,
    defaults: {
        layout: 'anchor',
        bodyStyle: 'padding: 15px',
        columnWidth: 0.5
    },
    items: [
        {defaults:{anchor:'95%'}, items: [nameTextField2, descriptionTextField, regexFieldSet, processCountThreshold, processMemoryThreshold]},
        {defaults:{anchor:'95%'}, items: [zMonitor, zAlertOnRestart, zFailSeverity, zModelerLock, zSendEventWhenBlockedFlag]}
    ]
}; // processFormItems


/************************************************************************
 *
 *   bottom_detail_panel - the device and event grid on the bottom right
 *
 **/


Ext.getCmp('center_panel').add(
        new Ext.Panel({
            layout: 'border',
            items: [{
                id: 'master_panel',
                region: 'west',
                layout: 'fit',
                width: 250,
                split: true,
                items: panel
            },{
                id: 'detail_panel',
                region: 'center',
                layout: 'border',
                items: [{
                    xtype: 'basedetailform',
                    layout: 'fit',
                    trackResetOnLoad: true,
                    id: 'processForm',
                    permission: 'Manage DMD',
                    region: 'center',
                    items: processFormItems,
                    router: router,
                    listeners: {
                        actioncomplete: actioncompleteHandler
                    }
                }, {
                    xtype: 'instancecardpanel',
                    id: 'detailCardPanel',
                    ref: 'detailCardPanel',
                    region: 'south',
                    split: true,
                    collapsed: false,
                    collapsible: false,
                    router: router,
                    bufferSize: 100,
                    nearLimit: 20,
                    showProcessCount: true,
                    instancesTitle: _t('Process Sets'),
                    zPropertyEditListeners: {
                        frameload: function() {
                            var formPanel = Ext.getCmp('processForm');
                            formPanel.setContext(formPanel.contextUid);
                        }
                    }
                }]
            }]
        }
    ));


var ContextGetter = Ext.extend(Object, {
    getUid: function() {
        var processes = Ext.getCmp('navGrid').getSelectionModel().getSelection();
        if (processes.length !== 1) {
            Ext.Msg.alert(_t('Error'), _t('You must select a process.'));
            return null;
        }
        return processes[0].data.uid;
    },
    getOrganizerUid: function() {
        var selected = Ext.getCmp('processTree').getSelectionModel().getSelectedNode();
        if ( ! selected ) {
                Ext.Msg.alert(_t('Error'), _t('You must select a process.'));
                return null;
            }
        return selected.data.uid;
    },
    hasTwoControls: function() {
        return true;
    }
});

/* ***********************************************************************
 *
 *   footer_panel - the add/remove tree node buttons at the bottom
 *
 */
function dispatcher(actionName, value) {
    var tree = Ext.getCmp(treeId);
    var grid = Ext.getCmp('navGrid');
    switch (actionName) {
        case 'addClass': tree.addNode('class', value); break;
        case 'addOrganizer': tree.addNode('organizer', value); break;
        case 'delete': grid.deleteSelectedRow(); break;
        case 'deleteOrganizer': tree.deleteSelectedNode(); break;
        default: break;
    }
}

var footer = Ext.getCmp('footer_bar');
Zenoss.footerHelper('Process Class', footer, {contextGetter: new ContextGetter()});
footer.on('buttonClick', dispatcher);
Ext.getCmp('footer_delete_button').setDisabled(true);


/**
 * @class Zenoss.SequenceModel
 * @extends Ext.data.Model
 * Model for sequence data grid
 **/
Ext.define('Zenoss.SequenceModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields:
        [ {name: 'uid'},
          {name: 'folder'},
          {name: 'name'},
          {name: 'includeRegex'},
          {name: 'monitor'},
          {name: 'count'}
        ]

});
/**
 * @class Zenoss.SequenceStore
 * @extend Zenoss.DirectStore
 * Direct store for loading up the sequence grid
 */
Ext.define("Zenoss.SequenceStore", {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.SequenceModel',
            directFn: router.getSequence,
            pageSize: 1000,
            scrollToLoadBuffer: 0,
            buffered: false,
            root: 'data'
        });
        this.callParent(arguments);
    }
});


Ext.define("Zenoss.SequenceGrid", {
    alias: ['widget.sequencegrid'],
    extend:"Zenoss.BaseSequenceGrid",
    constructor: function(config) {
        Ext.applyIf(config, {
            sortableColumns: false,
            multiSelect: true,
            forceFit: true,
            store: Ext.create('Zenoss.SequenceStore', {}),
            columns: [
                {dataIndex: 'folder', header: 'Folder', menuDisabled: true},
                {dataIndex: 'name', header: 'Name', menuDisabled: true},
                {dataIndex: 'includeRegex', header: 'Regex', menuDisabled: true },
                {dataIndex: 'monitor', header: 'Monitor', menuDisabled: true},
                {dataIndex: 'count', layout:'anchor', header: 'Count', menuDisabled: true}
            ]
        });
        this.callParent(arguments);
    }
});


Ext.getCmp('footer_bar').buttonContextMenu.menu.add({
    id: 'sequenceButton',
    iconCls: 'set',
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    tooltip: _t('Sequence the process classes'),
    text: _t('Change Sequence'),
    handler: function() {
        if ( ! Ext.getCmp('sequenceDialog') ) {
            new Zenoss.HideFitDialog({
                id: 'sequenceDialog',
                title: _t('Sequence'),
                layout: 'fit',
                items: [
                {
                    xtype: 'sequencegrid',
                    id: 'sequenceGrid'
                }],
                buttons: [{
                    xtype: 'HideDialogButton',
                    text: _t('Submit'),
                    handler: function() {
                        var records, uids;
                        records = Ext.getCmp('sequenceGrid').getStore().getRange();
                        uids = Ext.Array.pluck(Ext.Array.pluck(records, 'data'), 'uid');
                        router.setSequence({'uids': uids});
                    }
                 }, {
                    xtype: 'HideDialogButton',
                    text: _t('Cancel')
                }]
            });
        }
       Ext.getCmp('sequenceGrid').getStore().load();
       Ext.getCmp('sequenceDialog').show();
    }
});

/**
 * @class Zenoss.SequenceModel2
 * @extends Ext.data.Model
 * Model for sequence data grid
 **/
Ext.define('Zenoss.SequenceModel2',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
//    autoLoad: true,
    fields:
        [ {name: 'uid'},
          {name: 'folder'},
          {name: 'name'},
          {name: 'regex'},
          {name: 'excludeRegex'},
          {name: 'monitor'},
          {name: 'count'},
          {name: 'use'}
        ]

});

/**
 * @class Zenoss.SequenceStore2
 * @extend Zenoss.DirectStore
 * Direct store for loading up the sequence grid
 */
Ext.define("Zenoss.SequenceStore2", {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.SequenceModel2',
            directFn: router.getSequence2,
            root: 'data',
            initialSortColumn: 'uid'
        });
        Ext.apply(this, {
            single: false,
            count: 0,
            uids: []
        });
        this.callParent(arguments);
        var regex = Ext.getCmp('regexIncludeTextField').getValue();
        this.single = regex.length === 0;
    },
    listeners: {
        prefetch: function() {
            this.count = this.getCount();
        },
        datachanged: function() {
            var regex = Ext.getCmp('regexIncludeTextField').getValue();
            this.single = regex.length === 0;
            this.count = this.getCount();
            this.uids = [];
            this.each(function(rec) {
                this.store.uids.push(rec);
            });
        }
    }
});


Ext.define("Zenoss.SequenceGrid2", {
    alias: ['widget.sequencegrid2'],
    extend:"Ext.grid.GridPanel",
    constructor: function(config) {
        Ext.applyIf(config, {
            sortableColumns: false,
            sortableRows: false,
            forceFit: false,
            enableDragDrop: false,
            viewConfig: {
                forcefit: true
            },
            align : 'stretch',
            store: Ext.create('Zenoss.SequenceStore2', {}),
            columns: [
                {dataIndex: 'count', layout:'anchor', header: 'Count', menuDisabled: true, flex: 1},
                {dataIndex: 'name', header: 'Name', menuDisabled: true, flex: 2},
                {dataIndex: 'regex', header: 'Regex', menuDisabled: true, flex: 5},
                {dataIndex: 'excludeRegex', header: 'XRegex', menuDisabled: true,  flex: 4},
                {dataIndex: 'monitor', header: 'Monitor', menuDisabled: true, flex: 1}
            ]
        });
        this.callParent(arguments);
    }
});

function readBlob() {
    var files = document.getElementById("files").files;
    if (!files.length) {
      alert("Please select a file!");
      return;
    }

    var file = files[0];
    var start = 0;
    var stop = file.size - 1;

    var reader = new FileReader();

    // If we use onloadend, we need to check the readyState.
    reader.onloadend = function(evt) {
        if (evt.target.readyState === FileReader.DONE) { // DONE == 2
            var newContents = Ext.getCmp("input1").getValue() + evt.target.result;
            Ext.getCmp("input1").setValue(newContents);
        }
    };

    var blob = file.slice(start, stop + 1);
    reader.readAsBinaryString(blob);
  }

Ext.define('Zenoss.MatchedProcessModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
          {name: 'uid'},
          {name: 'matched'},
          {name: 'processClass'},
          {name: 'processSet'},
          {name: 'process'}
        ]
});

Ext.define("Zenoss.MatchProcessStore", {
    extend: "Zenoss.NonPaginatedStore", //NonPaginatedStore
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.MatchedProcessModel',
            directFn: router.applyOSProcessClassMatchers,
            initialSortColumn: 'uid',
            root: 'data',
            totalProperty: 'total'
        });
        this.callParent(arguments);
        // Default empty params
        var uids = [], lines = [];
        this.setBaseParam("uids", uids);
        this.setBaseParam("lines", lines);
    },
    listeners: {
        beforeload: function() {
            var uids = [];
            if (showAllProcessClasses) {
                Ext.getCmp('sequenceGrid2').getStore().uids.forEach(function (rec) {
                    uids.push(rec.data.uid);
                });
            } else {
                uids.push({
                    includeRegex: Ext.getCmp('regexIncludeTextField').getValue(),
                    excludeRegex: Ext.getCmp('regexExcludeTextField').getValue(),
                    replaceRegex: Ext.getCmp('regexReplaceTextField').getValue(),
                    replacement: Ext.getCmp('replacementTextField').getValue(),
                    name: Ext.getCmp('nameTextField2').getValue()
                });
            }
            this.setBaseParam("uids", uids);
            var lines = Ext.getCmp('input1').getValue().split('\n');
            this.setBaseParam("lines", lines);
        },
        load: function() {
            var m = this.count();
            var n = 0;
            processStore.each(function(record){
                var processList = record.get("process").split('\n');
                processList.forEach(function(processLine) {
                    var process = processLine.trim();
                    if (process.length > 0) {
                        if (process.substring(0, 0) !== '#') {
                            n++;
                        }
                    }
                });
            });
            var x = {};
            var y = {};
            this.each(function(matchedProcess) {
                var processClass = matchedProcess.get('processClass');
                var processSet = processClass + ":" + matchedProcess.get('processSet');
                var xx = x[processClass];
                if (! xx) {
                    xx = 1;
                } else {
                    xx++;
                }
                x[processClass] = xx;
                var yy = y[processSet];
                if (! yy) {
                    yy = 1;
                } else {
                    yy++;
                }
                y[processSet] = yy;
            });
            var xxx = 0;
            Ext.each(Object.keys(x), function(){
                xxx++;
            });
            var yyy = 0;
            Ext.each(Object.keys(y), function(){
                yyy++;
            });
            Ext.getCmp('outputTitle').setTitle('Output: ' + m.toString() + ' of ' + n.toString() + ' matched by ' + xxx + ' classes in ' + yyy + ' sets');
        }
    }
});

Ext.define("Zenoss.MatchProcessGrid", {
    alias: ['widget.matchProcessgrid'],
    extend:"Ext.grid.GridPanel",
    constructor: function(config) {
        Ext.applyIf(config, {
            enableDragDrop: false,
            viewConfig: {
                forcefit: true
            },
            sortableColumns: true,
            forceFit: false,
            store: Ext.create('Zenoss.MatchProcessStore', {}),
            columns: [
                {dataIndex: 'processClass', header: 'ProcessClass', sortable: true, sortType: 'asUCString', menuDisabled: true, flex: 1},
                {dataIndex: 'processSet', header: 'ProcessSet', sortable: true, sortType: 'asUCString', menuDisabled: true, flex: 2},
                {dataIndex: 'process', header: 'Process', sortable: true, sortType: 'asUCString', menuDisabled: false, flex: 5}
            ]
        });
        this.callParent(arguments);
    }
});

Ext.define('Zenoss.ProcessModel2',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
          {name: 'uid'},
          {name: 'process'}
        ]
});

Ext.define("Zenoss.ProcessStore2", {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.ProcessModel2',
            directFn: router.getProcessList,
            root: 'data',
            initialSortColumn: 'uid'
        });
        this.callParent(arguments);
        this.setBaseParam("deviceGuid", '');
    },
    listeners: {
        beforeprefetch: function() {
            Ext.MessageBox.wait('Fetching process list...');
            var deviceGuid = Ext.getCmp('devicecombo1').getValue();
            if (deviceGuid.length > 0) {
                this.setBaseParam("deviceGuid", deviceGuid);
            }
        }
    }
});

Ext.define("Zenoss.ProcessGrid2", {
    alias: ['widget.processGrid2'],
    extend:"Zenoss.BaseSequenceGrid",
    constructor: function(config) {
        Ext.applyIf(config, {
            sortableColumns: true,
            forceFit: false,
            store: Ext.create('Zenoss.ProcessStore2', {}),
            columns: [
                {dataIndex: 'uid', layout:'anchor', header: 'Matched', sortable: true, sortType: 'asUCString', menuDisabled: true, flex: 1},
                {dataIndex: 'process', header: 'Process', sortable: true, sortType: 'asUCString', menuDisabled: false, flex: 5}
            ]
        });
        this.callParent(arguments);
    }
});

var demoInput1 = [
                  '#',
                  '# Use this dialog to test regular expressions against sample input. Process',
                  '# monitoring uses the output of the Linux command "ps axho args" (or its',
                  '# equivalent) as input for regular expression matching. You may run that command',
                  '# on a system and copy-paste the result in this field, or load sample input',
                  '# from a local file (click the Choose File... button). Lines that begin with the hash',
                  '# character (#) are ignored.',
                  '#'
].join('\n');

var processGrid = Ext.create("Zenoss.ProcessGrid2", {});
var processStore = processGrid.getStore();
var showAllProcessClasses = true;

function getProcesses () {
    var newContents = Ext.getCmp('input1').getValue();
    if (newContents.length > 0) {
        newContents += '\n';
    }
    processStore.each(function(record){
        newContents += record.get("process") + '\n';
    });
    Ext.getCmp('input1').setValue(newContents);
    Ext.MessageBox.hide();
}

Ext.define("Zenoss.TestRegexDialog", {
    alias: ['widget.testRegexDialog'],
    extend:"Zenoss.HideFitDialog",
    constructor: function(config) {
        Ext.applyIf(config, {
            closeAction: 'destroy',
            title: _t('Test Process Class Regular Expressions'),
            width: window.innerWidth * 80 / 100,
            height: window.innerHeight * 80 / 100,
            layout: {
                type: 'vbox',
                align : 'stretch',
                pack  : 'start'
            },
            items: [
                {layout: {
                    type: 'hbox',
                    pack: 'start',
                    align: 'stretch'
                },
                items: [
                    {title: 'Source',
                        layout: {
                            type: 'vbox',
                            align : 'stretch',
                            pack  : 'start'
                        },
                        items: [
                            {layout: {
                                type: 'hbox',
                                pack: 'start',
                                align: 'stretch'
                            },
                            items: [
                                {fieldLabel: 'Device', xtype: 'rule.devicecombo', id: "devicecombo1", flex:2},
                                {xtype: 'button', ui: 'dialog-dark', text: _t('Add'),
                                    handler: function() {
                                        var deviceGuid = Ext.getCmp('devicecombo1').getValue();
                                        deviceGuid = deviceGuid.trim();
                                        if (deviceGuid.length === 0) {
                                            alert("Please select device first");
                                        } else {
                                            processStore.on('prefetch', getProcesses);
                                            processStore.load();
                                        }
                                    },
                                    autoWidth: true
                                }
                            ]},
                            {layout: {
                                type: 'hbox',
                                pack: 'start',
                                align: 'stretch'
                            },
                            items: [
                                    {fieldLabel: 'File', html: '<input type="file" id="files" name="file" />', ui: 'dialog-dark', flex:1},
                                    {
                                        xtype: 'button',
                                        ui: 'dialog-dark',
                                        autoWidth: true,
                                        text: _t('Add'),
                                        listeners: {
                                            click: function() {
                                                readBlob();
                                            }
                                        }
                                    }
                            ]},
                            {title: 'Input'},
                            {xtype: 'textareafield', grow: 'true', name: 'input1', id: 'input1',
                                value: demoInput1,
                                flex:4},
                            {xtype: 'button',  ui: 'dialog-dark', autoWidth: true, text: _t('Clear'),
                                listeners: {
                                    click: function() {
                                        Ext.getCmp('input1').setValue('');
                                    }
                                }
                            }
                        ],
                        flex:1},
                        {
                            layout:'card',
                            activeItem: showAllProcessClasses ? 0 : 1,
                            items: [{
                                id: 'card-0',
                                title: 'Process Classes',
                                layout: 'fit',
                                align : 'stretch',
                                items: [
                                {
                                    xtype: 'sequencegrid2',
                                    id: 'sequenceGrid2'
                                }],
                                flex:1
                            },{
                                id: 'card-1',
                                title: 'Process Class: ' + Ext.getCmp('nameTextField2').getValue(),
                                layout: {
                                    type: 'vbox',
                                    align : 'stretch',
                                    pack  : 'start'
                                },
                                items: [
                                    {fieldLabel: 'Include processes like', xtype: 'textfield', value: Ext.getCmp('regexIncludeTextField').getValue(), listeners: {change: function(){Ext.getCmp('regexIncludeTextField').setValue(this.getValue());}}},
                                    {fieldLabel: 'Exclude processes like', xtype: 'textfield', value: Ext.getCmp('regexExcludeTextField').getValue(), listeners: {change: function(){Ext.getCmp('regexExcludeTextField').setValue(this.getValue());}}},
                                    {fieldLabel: 'Replace command line text', xtype: 'textfield', value: Ext.getCmp('regexReplaceTextField').getValue(), listeners: {change: function(){Ext.getCmp('regexReplaceTextField').setValue(this.getValue());}}},
                                    {fieldLabel: 'With', xtype: 'textfield', value: Ext.getCmp('replacementTextField').getValue(), listeners: {change: function(){Ext.getCmp('replacementTextField').setValue(this.getValue());}}}
                                ], flex:1
                            }], flex:1
                        },
                ], flex:5},
                {title: 'Output', id: 'outputTitle', titleAlign: 'center'},
                {xtype: 'matchProcessgrid', id: 'output1', flex:5}
            ],
            buttons: [{
                xtype: 'button',
                ui: 'dialog-dark',
                text: _t('Test'),
                handler: function() {
                    Ext.getCmp('output1').getStore().removeAll();
                    Ext.getCmp('output1').getStore().load();
                }
             }, {
                xtype: 'HideDialogButton',
                text: _t('Done')
            }]
        });
        this.callParent(arguments);
        Ext.getCmp('sequenceGrid2').getStore().load();
        this.show();
    }
});


Ext.getCmp('footer_bar').buttonContextMenu.menu.add({
    id: 'regexTestButtonSingle',
    iconCls: 'set',
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    tooltip: _t('Test Process Class Regular Expressions'),
    text: _t('Test Process Class Regular Expressions'),
    handler: function() {
        if (Ext.getCmp('regexTestDialog') ) {
            Ext.getCmp('regexTestDialog').destroy();
        }
        showAllProcessClasses = false;
        if ( ! Ext.getCmp('regexTestDialog') ) {
            new Zenoss.TestRegexDialog(
            {
                id: 'regexTestDialog'
            });
        } else {
            Ext.getCmp('regexTestDialog').show();
        }
    }
});

Ext.getCmp('footer_bar').buttonContextMenu.menu.add({
    id: 'regexTestButtonAll',
    iconCls: 'set',
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    tooltip: _t('Test All Process Classes Regular Expressions'),
    text: _t('Test All Process Classes Regular Expressions'),
    handler: function() {
        if (Ext.getCmp('regexTestDialog')) {
            Ext.getCmp('regexTestDialog').destroy();
        }
        showAllProcessClasses = true;
        if ( ! Ext.getCmp('regexTestDialog') ) {
            new Zenoss.TestRegexDialog(
            {
                id: 'regexTestDialog'
            });
        } else {
            Ext.getCmp('regexTestDialog').show();
        }
    }
});

function handleRegexTestButtonSingle() {
    if (Ext.getCmp('regexIncludeTextField').getValue().length === 0) {
        Ext.getCmp('regexTestButtonSingle').setDisabled(true);
    } else {
        Ext.getCmp('regexTestButtonSingle').setDisabled(false);
    }
}

Ext.getCmp('footer_bar').buttonContextMenu.on('click', handleRegexTestButtonSingle);


}); // Ext.onReady
