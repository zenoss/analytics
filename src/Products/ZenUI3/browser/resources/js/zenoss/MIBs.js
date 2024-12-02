/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

Ext.onReady(function() {

Ext.ns('Zenoss.ui.Mibs');

var router = Zenoss.remote.MibRouter;

// A model for OID types.
Ext.define('Zenoss.mibs.NodeType', {
    extend: 'Ext.data.Model',
    fields: [
        {name: 'name', type: 'string'},
        {name: 'label', type: 'string'},
        {name: 'accessOrObjects', type: 'string'},
        {name: 'addfn'},
        {name: 'deletefn'}
    ]
});

// A store of OID type instances
// Only two records: 'OID Mapping' and 'Trap'
var nodeTypes = Ext.create('Ext.data.Store', {
    model: 'Zenoss.mibs.NodeType',
    data: [{
        name: _t('OID Mapping'),
        label: _t('OID Mappings'),
        accessOrObjects: _t("Access"),
        addfn: router.addOidMapping,
        deletefn: router.deleteOidMapping
    }, {
        name: _t('Trap'),
        label: _t('Traps'),
        accessOrObjects: _t("Objects"),
        addfn: router.addTrap,
        deletefn: router.deleteTrap
    }],
    // proxy:'memory' required so that ExtJS doesn't try to
    // load data from an unspecified URL.
    proxy: 'memory'
});


/**
 * @class Zenoss.mibs.TrapModel
 * @extends Ext.data.Model
 * Field definitions for the traps
 **/
Ext.define('Zenoss.mibs.TrapModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        {name: 'uid'},
        {name: 'name'},
        {name: 'oid'},
        {name: 'nodetype'},
        {name: 'objects'},
        {name: 'status'},
        {name: 'description'}
    ]
});

/**
 * @class Zenoss.mibs.OidModel
 * @extends Ext.data.Model
 * Field definitions for the oids
 **/
Ext.define('Zenoss.mibs.OidModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        {name: 'uid'},
        {name: 'name'},
        {name: 'oid'},
        {name: 'nodetype'},
        {name: 'access'},
        {name: 'status'},
        {name: 'description'}
    ]
});


Ext.define('Zenoss.mibs.MibStore', {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            pageSize: 50,
            initialSortColumn: "name",
            totalProperty: 'count',
            root: 'data'
        });
        this.callParent(arguments);
    }
});


Ext.define('Zenoss.mibs.NodeGridPanel', {
    extend: 'Zenoss.BaseGridPanel',
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            defaults: {sortable: true},
            columns: [{
                width: 300,
                flex: 1,
                dataIndex: 'name',
                header: _t('Name')
            },{
                width: 180,
                dataIndex: 'oid',
                header: _t('OID')
            },{
                width: 100,
                dataIndex: 'nodetype',
                header: _t('Node Type')
            }],
            selModel: Ext.create('Zenoss.SingleRowSelectionModel', {
                listeners: {
                    select: function(sm, rec, ri) {
                        Ext.getCmp('node_details').getForm().setValues({
                            name: rec.data.name,
                            oid: rec.data.oid,
                            accessOrObjects: (rec.data.access === undefined)
                                ? rec.data.objects.join(', ')
                                : rec.data.access,
                            nodetype: rec.data.nodetype,
                            status: rec.data.status,
                            description: rec.data.description
                        });
                    }
                }
            })
        });
        this.callParent(arguments);
    }
});

var oid_grid = Ext.create('Zenoss.mibs.NodeGridPanel', {
    id: 'oid_grid',
    store: Ext.create('Zenoss.mibs.MibStore', {
        model: 'Zenoss.mibs.OidModel',
        directFn: router.getOidMappings
    })
});

var trap_grid = Ext.create('Zenoss.mibs.NodeGridPanel', {
    id: 'trap_grid',
    store: Ext.create('Zenoss.mibs.MibStore', {
        model: 'Zenoss.mibs.TrapModel',
        directFn: router.getTraps
    })
});


var node_details = Ext.create('Ext.form.Panel', {
    id: 'node_details',
    title: _t(nodeTypes.first().data.name + " Overview"),
    bodyPadding: 10,
    region: 'center',
    defaultType: 'displayfield',
    defaults: {
        labelWidth: 80
    },
    autoScroll: true,
    items: [{
        fieldLabel: _t('Name'),
        name: 'name'
    },{
        fieldLabel: _t('OID'),
        name: 'oid'
    },{
        id: 'access_or_objects',
        fieldLabel: nodeTypes.first().data.accessOrObjects,
        name: 'accessOrObjects'
    },{
        fieldLabel: _t('Node Type'),
        name: 'nodetype'
    },{
        fieldLabel: _t('Status'),
        name: 'status'
    },{
        fieldLabel: _t('Description'),
        name: 'description',
        renderer: Ext.util.Format.nl2br
    }]
});

function createConfirmAddNodeDialog(nodeType, ctx, info, addHandler) {
    var mibMatch = info.uid.match(/\/mibs\/(.+)\/nodes/),
        oldMib = mibMatch ? mibMatch[1] : "";
    return new Zenoss.dialog.CloseDialog({
        id: 'confirmAddNodeDialog',
        width: 400,
        title: "Add " + nodeType.name,
        items: [{
            xtype: 'panel',
            style: {
                backgroundColor: 'yellow',
                padding: '3px 5px'
            },
            html: '<p style="color: black;font-size:16px">That OID already exists!</p>',
            renderTo: Ext.getBody()
        }, {
            xtype: 'form',
            layout: 'form',
            buttonAlign: 'left',
            fieldDefaults: {labelAlign: 'top'},
            footerStyle: 'padding-left: 0',
            defaultType: 'fieldset',
            items: [{
                title: _t('Do you wish to replace the existing mapping'),
                defaultType: 'displayfield',
                defaults: {labelAlign: 'right', labelWidth: 50, labelPad: 15},
                layout: 'form',
                items: [
                    {fieldLabel: _t('Name'), value: info.name},
                    {fieldLabel: _t('OID'), value: info.oid},
                    {fieldLabel: _t('MIB'), value: oldMib}
                ]
            },{
                title: _t('with this new mapping?'),
                defaultType: 'displayfield',
                defaults: {labelAlign: 'right', labelWidth: 50, labelPad: 15},
                layout: 'form',
                items: [
                    {fieldLabel: _t('Name'), value: ctx.id},
                    {fieldLabel: _t('OID'), value: ctx.oid},
                    {fieldLabel: _t('MIB'), value: Zenoss.env.currentUid.split('/').pop()}
                ]
            }],
            buttons: [{
                xtype: 'DialogButton',
                text: _t('Yes'),
                handler: function() { addHandler(ctx); }
            }, Zenoss.dialog.CANCEL]
        }]
    });
}

function createAddNodeDialog(nodeType, handler) {
    return new Zenoss.dialog.CloseDialog({
        id: 'addNodeDialog',
        width: 300,
        title: "Add " + nodeType.name,
        items: [{
            xtype: 'form',
            buttonAlign: 'left',
            fieldDefaults: {
                labelAlign: 'top'
            },
            footerStyle: 'padding-left: 0',
            id: 'addNodeForm',
            defaultType: 'textfield',
            defaults: {allowBlank: false},
            items: [{
                fieldLabel: _t('ID'),
                name: 'id'
            },{
                fieldLabel: _t('OID'),
                name: 'oid'
            }],
            buttons: [{
                xtype: 'DialogButton',
                text: _t('Submit'),
                handler: function(button, evt) {
                    var form = Ext.getCmp('addNodeForm').getForm();
                    handler(form.findField('id').getValue(), form.findField('oid').getValue());
                }
            }, Zenoss.dialog.CANCEL]
        }]
    });
}

var MibBrowser = Ext.extend(Ext.Container, {
    currentUid: null,
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'border',
            id: 'mibbottom',
            items: [{
                xtype: 'panel',
                title: _t('MIB Overview'),
                region: 'north',
                height: 250,
                split: true,
                autoScroll: true,
                layout: 'border',
                items: [{
                    xtype: 'form',
                    region: 'west',
                    id: 'mib_form_left',
                    autoScroll: true,
                    width: 500,
                    bodyStyle: 'padding:5px 8px 0',
                    defaultType: 'displayfield',
                    items: [{
                        fieldLabel: _t('Name'),
                        ref: 'name'
                    },{
                        fieldLabel: _t('Contact'),
                        ref: 'contact',
                        renderer: Ext.util.Format.nl2br
                    }]
                },{
                    xtype: 'form',
                    region: 'center',
                    id: 'mib_form_right',
                    autoScroll: true,
                    bodyStyle: 'padding:5px 8px 0',
                    defaultType: 'displayfield',
                    items: [{
                        fieldLabel: _t('Language'),
                        ref: 'language'
                    },{
                        fieldLabel: _t('Description'),
                        ref: 'description',
                        renderer: Ext.util.Format.nl2br
                    }]
                }]
            },{
                xtype: 'panel',
                region: 'center',
                layout: 'border',
                split: true,
                tbar: {
                    cls: 'largetoolbar componenttbar',
                    height: 37,
                    items: [{
                        xtype: 'combo',
                        id: 'node_type_combo',
                        cls: 'mibcombobottom',
                        store: nodeTypes,
                        displayField: 'label',
                        value: nodeTypes.first(),
                        editable: false,
                        autoSelect: true,
                        forceSelection: true,
                        triggerAction: 'all',
                        selectOnFocus: false,
                        listeners: {
                            select: function(combo, records, options) {
                                if (!records || !records.length) {
                                    return;
                                }
                                var record = records[0],
                                    combo = Ext.getCmp('node_type_combo'),
                                    nodeType = combo.findRecordByDisplay(combo.getValue()).data,
                                    node_details = Ext.getCmp('node_details'),
                                    gridCardPanel = Ext.getCmp('gridCardPanel');

                                gridCardPanel.layout.setActiveItem(record.index);
                                gridCardPanel.layout.activeItem.setContext(Zenoss.env.PARENT_CONTEXT);
                                node_details.setTitle(nodeType.name + " Overview");
                                node_details.getForm().reset();
                                Ext.getCmp('access_or_objects').setFieldLabel(nodeType.accessOrObjects);
                            }
                        }
                    }, '-', {
                        xtype: 'button',
                        id: 'add_node_button',
                        iconCls: 'add',
                        handler: function(btn, evt) {
                            var combo = Ext.getCmp('node_type_combo'),
                                nodeType = combo.findRecordByDisplay(combo.getValue()).data,
                                addMibNode = function(ctx) {
                                    // The addMibNode function adds a node or trap.
                                    // Called by handleOidInfo or by the ConfirmAddNodeDialog.
                                    var params = {
                                        uid: Zenoss.env.currentUid,
                                        id: Ext.htmlEncode(ctx.id),
                                        oid: Ext.htmlEncode(ctx.oid),
                                    };
                                    nodeType.addfn(params, function(response) {
                                        if (response.success) {
                                            Zenoss.message.info(_t('OID was successfully added.'));
                                            Ext.getCmp('gridCardPanel').layout.activeItem.refresh();
                                        } else {
                                            Zenoss.message.info(_t('Could not add OID.'));
                                        }
                                    });
                                },
                                // Processes the response from the remote 'getOid' call.
                                handleOidInfo = function(response, remoteFn, ignored, ctx) {
                                    if (response.success) {
                                        var confirmDialog = createConfirmAddNodeDialog(
                                            nodeType, ctx, response.info, addMibNode
                                        );
                                        confirmDialog.show();
                                    } else {
                                        addMibNode(ctx);
                                    }
                                },
                                // Processes the data retrieved from the AddNodeDialog.
                                handleAddNodeDialog = function(id, oid) {
                                    router.getOid(
                                        { oid: Ext.htmlEncode(oid) },
                                        Ext.bind(handleOidInfo, undefined, {id:id, oid:oid}, true)
                                    );
                                },
                                addNodeDialog = createAddNodeDialog(nodeType, handleAddNodeDialog);
                            addNodeDialog.show();
                        }
                    }, {
                        xtype: 'button',
                        id: 'delete_node_button',
                        iconCls: 'delete',
                        handler: function() {
                            var combo = Ext.getCmp('node_type_combo'),
                                nodeType = combo.findRecordByDisplay(combo.getValue()).data,
                                grid = Ext.getCmp('gridCardPanel').layout.activeItem,
                                sm = grid.getSelectionModel(),
                                sel = sm.getSelected();
                            if (sel === undefined || sel === null) {
                                return;
                            }
                            nodeType.deletefn({uid: sel.get("uid")}, function() {
                                var node = Ext.getCmp('node_details');
                                node.getForm().reset();
                                grid.refresh();
                            });
                        }
                    }]
                },
                items: [{
                    region: 'west',
                    layout: 'card',
                    disabled: true,
                    id: 'gridCardPanel',
                    split: true,
                    width: 600,
                    items: [oid_grid, trap_grid ]
                }, node_details]
            }]
        });
        MibBrowser.superclass.constructor.call(this, config);
    },
    setContext: function(node) {
        var params = {
            uid: node.data.uid,
            useFieldSets: false
        };
        router.getInfo(params, this.populateForm);
    },
    populateForm: function(response) {
        Zenoss.env.currentUid = response.data.uid;
        var mib_form_left = Ext.getCmp('mib_form_left'),
            mib_form_right = Ext.getCmp('mib_form_right');
        mib_form_left.name.setValue(Ext.htmlEncode(response.data.name));
        mib_form_left.contact.setValue(Ext.htmlEncode(response.data.contact));
        mib_form_right.language.setValue(Ext.htmlEncode(response.data.language));
        mib_form_right.description.setValue(Ext.htmlEncode(response.data.description));
        Ext.getCmp('gridCardPanel').layout.activeItem.setContext(Zenoss.env.PARENT_CONTEXT);
    }
});

var mib_browser = new MibBrowser({});

/**********************************************************************
 *
 * Mib Tree
 *
 */

function getSelectedMibTreeNode(){
    return Ext.getCmp('mibtree').getSelectionModel().getSelectedNode();
}

function reloadTree(selectedUid) {
    var tree = Ext.getCmp('mibtree');
    tree.refresh(function(){
        tree.getRootNode().childNodes[0].expand();
        tree.selectByToken(selectedUid);
    });
}

/*
 * TODO: determine if selecting a new folder with no items in it
 *       should leave a blank panel or not
 */
Ext.define("Zenoss.MibTreePanel", {
    extend:"Zenoss.HierarchyTreePanel",
        constructor: function(config) {
            Ext.applyIf(config, {
                id: 'navTree',
                flex: 1,
                searchField: false,
                directFn: router.getOrganizerTree,
                router: router,
                selModel: treesm,
                relationshipIdentifier: 'mibs',
                pathSeparator: '/',
                selectRootOnLoad: true,
                ddGroup: 'serviceDragDrop',
                ddAppendOnly: true,
                listeners: {
                    scope: this,
                    expandnode: this.onExpandnode
                },
                viewConfig: {
                    listeners: {
                        drop: this.onNodeDrop,
                        scope: this
                    }

                }
            });
            this.callParent(arguments);
        },
        onNodeDrop: function(n, nodedata, model, drop, func, opt) {
            router.moveNode({
                    uids: [nodedata.records[0].data.uid],
                    target: nodedata.records[0].parentNode.data.uid
                },
                function() {
                    this.moveMibsCallback(nodedata.records[0].parentNode.data.uid);
                },
                this
            );
        },
        moveMibsCallback: function(targetId) {
            Ext.History.add('navTree' + Ext.History.DELIMITER + targetId);
            window.location.reload(); // instructed to by management :)
            //this.getRootNode().reload(this.rootNodeReloadCallback, this);
        },
        rootNodeReloadCallback: function() {
            this.getRootNode().select();
            this.getRootNode().expand(true);
        },
        onExpandnode: function(node) {
            var token, remainder;
            token = Ext.History.getToken();
            if (token) {
                remainder = token.split(Ext.History.DELIMITER)[1];
                this.selectByToken(remainder);
            }
        },

        selectByToken: function(token) {
            token = token.replace(/\//g, '.');
            var path = this.getNodePathById(token);
            this.selectPath(path);
        },
        initEvents: function() {
            Zenoss.MibTreePanel.superclass.initEvents.call(this);
            // don't add history token on click like HierarchyTreePanel does
            // this is handled in the selection model
            this.un('itemclick', this.addHistoryToken, this);
        }

});

/**********************************************************************
 *
 * Action Buttons
 *
 */

var treesm = new Zenoss.TreeSelectionModel({
    listeners: {
        'selectionchange': function(sm, nodes) {
            var newnode;
            if (nodes.length) {
                newnode = nodes[0];
            }
            var isRoot = false;

            if (newnode && newnode.data.leaf) {
                mib_browser.setContext(newnode);
                Ext.getCmp('gridCardPanel').setDisabled(false);
            }

            if (newnode) {
                // set the context for the new nodes
                Zenoss.env.PARENT_CONTEXT = newnode.data.uid;
                if (newnode.data.uid === '/zport/dmd/Mibs') {
                    isRoot = true;
                }
                Ext.getCmp('add-organizer-button').setDisabled(
                    newnode.data.leaf || Zenoss.Security.doesNotHavePermission('Manage DMD')
                );
                Ext.getCmp('edit-mib-action').setDisabled(
                    !newnode.data.leaf || Zenoss.Security.doesNotHavePermission('Manage DMD')
                );
                // do not allow them to delete the root node
                Ext.getCmp('delete-button').setDisabled(
                    isRoot || Zenoss.Security.doesNotHavePermission('Manage DMD')
                );
                // add to history
                Ext.History.add('mibtree' + Ext.History.DELIMITER + newnode.data.uid);
            }
        }
    }
});

var mib_tree = new Zenoss.MibTreePanel({
    id: 'mibtree',
    cls: 'mib-tree',
    ddGroup: 'mibtreedd',
    searchField: true,
    router: router,
    root: {
        id: 'Mibs',
        uid: '/zport/dmd/Mibs',
        text: _t('Mib Classes'),
        allowDrop: false
    },
    listeners: {
        click: function(node, e) {
            if (node.data.leaf) {
                mib_browser.setContext(node);
            }
        }
    },
    dropConfig: { appendOnly: true }
});


Ext.getCmp('center_panel').add({
    hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    id: 'center_panel_container',
    layout: 'border',
    defaults: {
        'border': false
    },
    items: [{
        id: 'master_panel',
        layout: 'fit',
        region: 'west',
        width: 250,
        maxWidth: 250,
        split: true,
        items: [mib_tree]
    }, {
        layout: 'fit',
        region: 'center',
        items: [mib_browser]
    }]
});

/**********************************************************************
 *
 * Edit a Mib
 *
 */
function showEditMibDialog(response){
    var data = response.data, win,
        items = response.form.items[0].items,
        win = Ext.create('Zenoss.dialog.BaseWindow', {
            id: 'editMIBDialog',
            title: _t('Edit MIB'),
            height: 360,
            width: 510,
            modal: true,
            autoScroll: true,
            plain: true,
            buttonAlight: 'left',
            items: {
                xtype:'form',
                ref: 'editForm',
                buttonAlign: 'left',
                items: items,
                listeners: {
                    validitychange: function(form, valid) {
                        if (win.isVisible()){
                            win.submitButton.setDisabled(!valid);
                        }
                    }
                }
            },
            buttons:[{
                xtype: 'DialogButton',
                ref: '../submitButton',
                text: _t('Submit'),
                handler: function(button) {
                    var form = button.refOwner.editForm.getForm(),
                        dirtyOnly = true,
                        opts = form.getValues(false, dirtyOnly);
                        opts.uid = data.uid;
                    router.setInfo(opts, function(response) {
                        reloadTree(response.data.uid);
                    });
                }
            },{
                xtype: 'DialogButton',
                text: _t('Cancel')
            }]
        });
    // show the edit form
    win.show();
}


/**********************************************************************
 *
 * Footer Bar
 *
 */

function createAction(typeName, text) {
    return new Zenoss.Action({
        text: _t('Add ') + text + '...',
        iconCls: 'add',
        handler: function() {
            var addDialog = new Zenoss.FormDialog({
                    title: _t('Create ') + text,
                    modal: true,
                    formId: Ext.id(),
                    formListeners: {
                        validitychange: function(field, isValid) {
                            if (addDialog.isVisible()) {
                                 addDialog.submitButton.setDisabled(!isValid);
                            }
                        }
                    },
                    width: 310,
                    items: [{
                        xtype: 'idfield',
                        fieldLabel: _t('ID'),
                        ref: '../nameField',
                        name: 'name',
                        tabIndex: 0,
                        allowBlank: false
                    }],
                    buttons: [{
                        xtype: 'DialogButton',
                        text: _t('Submit'),
                        ref: '../submitButton',
                        disabled: true,
                        tabIndex: 1,
                        handler: function() {
                            var newName;
                            newName = addDialog.nameField.getValue();
                            mib_tree.addNode(typeName, newName);
                        }
                    },
                        Zenoss.dialog.CANCEL
                    ]
                });
            addDialog.show();
        }
    });
}

function createLocalMIBAddAction() {
    return new Zenoss.Action({
        text: _t('Add MIB from Desktop') + '...',
        id: 'addmib-item',
        permission: 'Manage DMD',
        handler: function(btn, e){
            var node = getSelectedMibTreeNode(),
                src = node.data.uid + '/uploadfile',
                win = new Zenoss.dialog.CloseDialog({
                    id: 'fileuploadwindow',
                    width: 300,
                    title: _t('Add MIB from Desktop'),
                    listeners: {
                        close: function(panel) {
                            // show the message about the uploaded file
                            Zenoss.messenger.checkMessages();
                        }
                    },
                    items: [{
                        xtype: 'panel',
                        buttonAlign: 'left',
                        fieldDefaults: {
                            labelAlign: 'top'
                        },
                        footerStyle: 'padding-left: 0',
                        items: [{
                            xtype: 'panel',
                            width: 270,
                            height: 70,
                            layout: 'anchor',
                            html: '<iframe frameborder="0" src="' +  src  + '"></iframe>'
                        }]
                    }]
                });
            win.show();
        }
    });
}

function createDownloadMIBAddAction() {
    return new Zenoss.Action({
        text: _t('Download MIB') + '...',
        id: 'download-addmib-item',
        permission: 'Manage DMD',
        handler: function(btn, e){
            var win = new Zenoss.dialog.CloseDialog({
                width: 300,
                title: _t('Download MIB'),

                items: [{
                    xtype: 'form',
                    buttonAlign: 'left',
                    monitorValid: true,
                    fieldDefaults: {
                        labelAlign: 'top'
                    },
                    footerStyle: 'padding-left: 0',
                    items: [{
                        xtype: 'textfield',
                        name: 'package',
                        fieldLabel: _t('URL'),
                        id: "add-mib-url",
                        allowBlank: false
                    }],
                    buttons: [{
                        xtype: 'DialogButton',
                        text: _t('Add'),
                        formBind: true,
                        handler: function(b) {
                            var form = b.ownerCt.ownerCt.getForm(),
                                opts = form.getValues();
                            opts.organizer = Zenoss.env.PARENT_CONTEXT.replace('/zport/dmd/Mibs', '');
                            router.addMIB(opts,
                            function(response) {
                                if (!response.success) {
                                    new Zenoss.dialog.SimpleMessageDialog({
                                        message: response.msg,
                                        buttons: [{
                                            xtype: 'DialogButton',
                                            text: _t('OK')
                                        }]
                                    }).show();
                                }
                            });
                        }
                    }, Zenoss.dialog.CANCEL]
                }]
            });
            win.show();
        }
    });
}

var footerBar = Ext.getCmp('footer_bar');

footerBar.add({
    id: 'add-organizer-button',
    tooltip: _t('Add MIB organizer or MIB'),
    iconCls: 'add',
    disabled: true,
    menu: {
        width: 190, // mousing over longest menu item was changing width
        items: [
            createAction('organizer', _t('MIB Organizer')),
            createAction('MIB', _t('blank MIB')),
            createLocalMIBAddAction(),
            createDownloadMIBAddAction()
        ]
    }
});

/*
 * Delete a mib class
 */
function deleteNode() {
    var node = getSelectedMibTreeNode(),
        nodeType = "Mib";
    if (!node.data.leaf) {
        nodeType = "Organizer";
    }
    new Zenoss.dialog.SimpleMessageDialog({
        message: Ext.String.format(_t('Are you sure you want to delete the selected {0}?'), nodeType),
        title: _t('Delete Mib'),
        buttons: [{
            xtype: 'DialogButton',
            text: _t('Delete'),
            handler: function() {
                var params = {
                        uid: node.data.uid
                    },
                    parentUid = node.parentNode.data.uid,
                    callback = function(response) {
                        // after deleting the child, select the parent
                        reloadTree(parentUid);
                    };
                router.deleteNode(params, callback);
            }
        }, {
            xtype: 'DialogButton',
            text: _t('Cancel')
        }]
    }).show();
}

footerBar.add({
    id: 'delete-button',
    tooltip: _t('Delete an item'),
    iconCls: 'delete',
    handler: deleteNode
});

/*
 * add mib class to zenpack
 */
function addToZenPack(e) {
    var addtozenpack = new Zenoss.AddToZenPackWindow();
    addtozenpack.setTarget(treesm.getSelectedNode().data.uid);
    addtozenpack.show();
}

footerBar.add([{
    xtype: 'button',
    iconCls: 'customize',
    id: 'mibs-configure-menu',
    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    defaultType: 'menuitem',
    menu: {
        items: [{
            id: 'edit-mib-action',
            disabled: true,
            text: _t('Edit a Mib'),
            handler: function() {
                var node = getSelectedMibTreeNode();
                if (node) {
                    var params = {
                        uid: node.data.uid,
                        useFieldSets: false
                    };
                    router.getInfo(params, showEditMibDialog);
                }
            }
        }, {
            text: _t('Add to ZenPack'),
            handler: addToZenPack
        }]
    }
}]);

});
