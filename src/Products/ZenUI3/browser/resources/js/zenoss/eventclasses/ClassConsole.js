/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

Ext.onReady(function(){

    Ext.ns('Zenoss.eventclasses');
    // page level variables
    var REMOTE = Zenoss.remote.EventClassesRouter;

    /**
      * Returns the selection model for the last selected tree, if no
      * trees have been selected then return the selection model for devices
      **/
    function getSelectionModel(){
        if (Zenoss.env.treesm) {
            return Zenoss.env.treesm;
        }
        return Ext.getCmp('classes').getSelectionModel();
    }

    function initializeTreeDrop(tree) {
        // fired when the user actually drops a node
        tree.getView().on('beforedrop', function(element, e, targetnode) {
            var grid = Ext.getCmp('classesgrid_id'),
                targetuid = targetnode.data.uid,
                movedids =[],
                me = this,
                message = "",
                isOrganizer = true;

            // if instances is in the path, then its NOT an organizer. Hope no-one ever
            // calls an event class 'instances'
            isOrganizer = e.records[0].get("uid").indexOf('/instances/') === -1;

            for(var i=0; e.records.length > i; i++){
                movedids.push(e.records[i].get("uid"));
            }

            message = _t("Are you sure you want to move these items?");

            new Zenoss.dialog.SimpleMessageDialog({
                message: message,
                title: _t('Move Item'),
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('OK'),
                    handler: function() {
                        var refresh = function(refreshGrid){
                            var tree = getSelectionModel().getSelectedNode().getOwnerTree();
                            tree.refresh();
                            tree.getStore().on('load', function(){
                                var nodeId = targetnode.data.uid;
                                var node = tree.getRootNode().findChild("uid", nodeId, true);
                                tree.expandToChild(node);
                                tree.getView().select(node);
                            }, this, {single:true});
                            if(refreshGrid){
                                grid.refresh();
                            }
                        };
                        var params = {
                            UidsToMove: movedids,
                            targetUid: targetuid
                        };
                        if(isOrganizer){
                            REMOTE.moveClassOrganizer({'params':params}, function(response){
                                if(response.success) {
                                    refresh();
                                }
                            }, me);
                        }else{
                            REMOTE.moveInstance({'params':params}, function(response){
                                if(response.success) {
                                    refresh(true);
                                }
                            }, me);
                        }
                    }
                }, {
                    xtype: 'DialogButton',
                    text: _t('Cancel')
                }]
            }).show();
            // if we return true a dummy node will be appended to the tree
            return false;
        }, tree);
    }


    var classtree = {
        xtype: 'HierarchyTreePanel',
        loadMask: true,
        id: 'classes',
        searchField: true,
        directFn: REMOTE.asyncGetTree,
        allowOrganizerMove: true,
        stateful: true,
        stateId: 'evclass_tree',
        ddAppendOnly: true,
        root: {
            id: 'Classes',
            uid: '/zport/dmd/Events',
            text: 'Event Classes'
        },
        ddGroup: 'evclassgriddd',
        getContentPanel: function(){
            return Ext.getCmp('class_center_panel').items.items[Ext.getCmp('nav_combo').getSelectedIndex()];
        },
        setTransIcon: function(isTrans){
            if(isTrans === this.getSelectionModel().getSelectedNode().data.text.hasTransform) {
                return false;
            }
            this.refresh();
        },
        columns:[
                {
                    xtype:'treecolumn',
                    flex:1,
                    dataIndex:'text',
                    renderer:function (value, l, n) {
                        if(Ext.isString(value)){
                            return value;
                        }
                        var parentNode = n.parentNode;
                        var xfclass = value.hasTransform ? 'hastransform' : 'sanstransform';
                        var xfdesc  = value.hasTransform ? 'Has Transform' : 'Has no Transform';
                        var safeText = Ext.String.htmlEncode(value.text);
                        var safeDescription = Ext.String.htmlEncode(value.description);

                        var xform = Ext.String.format(" <span class='{0}' title='{1}'></span>", xfclass,xfdesc);
                        if(parentNode.data.root === true){
                            return Ext.String.format("{2}<span title='{0}' class='rootNode'>{1}</span>", safeDescription, safeText, xform);
                        }else{
                            return Ext.String.format("{2}<span title='{0}' class='subNode'>{1}</span>", safeDescription, safeText, xform);
                        }
                    }
                }
            ],
        selModel: Ext.create('Zenoss.TreeSelectionModel',{
            tree: 'classes',
            listeners: {
                selectionchange: function(sm, newnodes){
                    if (newnodes.length) {
                        var newnode = newnodes[0];
                        var uid = newnode.data.uid;
                        var contentPanel = classtree.getContentPanel();
                        contentPanel.setContext(uid);
                        Ext.getCmp('class_events').setContext(uid);
                        Ext.getCmp('footer_bar').setContext(uid);
                        Zenoss.env.contextUid = uid;
                        // explicitly set the new security context (to update permissions)
                        Zenoss.Security.setContext(uid);
                    }
                }
            }
        }),
        router: REMOTE,
        nodeName: 'EventClass',
        deleteNodeFn: function(args) {
            var parentNodeProcess = args.uid.split("/");
            parentNodeProcess.pop();
            var parentNode = parentNodeProcess.join("/");
            REMOTE.deleteEventClass({'uid':args.uid}, function(response){
                if(response.success){
                    var tree = getSelectionModel().getSelectedNode().getOwnerTree();
                    tree.refresh();
                    tree.getStore().on('load', function(){
                        var node = tree.getRootNode().findChild("uid", parentNode, true);
                        tree.expandToChild(node);
                        tree.getView().select(node);
                    }, this, {single:true});

                }
            });
        },
        listeners: {
            render: initializeTreeDrop,
            viewready: function(t){
                // fixes 20000px width bug on the targetEl div bug in Ext
                t.ownerCt.ownerCt.searchfield.container.setWidth(t.body.getWidth());
            }
        }
    };

    var treepanel = {
        xtype: 'HierarchyTreePanelSearch',
        items: [classtree]
    };

    Ext.define("Zenoss.eventclasses.NavigtaionCombo", {
        alias: ['widget.NavCombo'],
        extend: "Ext.form.ComboBox",
        constructor: function(config){
            config = config || {};
            Ext.applyIf(config, {
                id: 'nav_combo',
                width: 240,
                displayField: 'name',
                editable: false,
                typeAhead: false,
                value: _t('Mapping Instances'),
                listeners:{
                    select: function(combo){
                        var container = Ext.getCmp('class_center_panel');
                        container.layout.setActiveItem(combo.getSelectedIndex());
                        // set the context for the active item:
                        var contentPanel = classtree.getContentPanel();
                        contentPanel.setContext(Zenoss.env.contextUid);
                        Zenoss.Security.setContext(Zenoss.env.contextUid);
                    }
                },
                store:  Ext.create('Ext.data.ArrayStore', {
                     model: 'Zenoss.model.Name',
                     data: [[
                        _t('Mapping Instances')
                    ],[
                        _t('Configuration Properties')
                    ],[
                        _t('Overridden Objects')
                    ],[
                        _t('Transforms')
                    ],[
                        _t('Events')
                    ]]
                 })
            });
            this.callParent(arguments);
        }

    });

    var event_console = Ext.create('Zenoss.EventGridPanel', {
        id: 'eventclass_eventsgrid',
        stateId: 'eventclass_events',
        columns: Zenoss.env.getColumnDefinitions(['EventClass']),
        newwindowBtn: true,
        actionsMenu: false,
        commandsMenu: false,
        store: Ext.create('Zenoss.events.Store', {})
    });

    Ext.getCmp('center_panel').add({
        id: 'center_panel_container',
        layout: 'border',
        defaults: {
            split: true
        },
        items: [{
            xtype: 'panel',
            id: 'master_panel',
            cls: 'x-zenoss-master-panel',
            region: 'west',
            width: 275,
            maxWidth: 275,
            layout: 'fit',
            items: [
                treepanel
            ]
        },{
            xtype: 'contextcardpanel',
            id: 'class_center_panel',
            region: 'center',
            activeItem: 0,
            tbar: {
                cls: 'largetoolbar',
                height: 38,
                items: [
                    {
                        xtype: 'eventrainbow',
                        id: 'class_events',
                        width:152,
                        refresh: function(){
                            var me = this;
                            REMOTE.getEventsCounts({'uid':this.uid}, function(response){
                                if(response.success){
                                    me.updateRainbow(response.data);
                                }
                            });
                        }
                    },
                    '-',
                    {
                        xtype: 'NavCombo'
                    }
                ]
            },
            items: [
                {
                    xtype: 'classesgrid',
                    id: 'classesgrid_id',
                    viewConfig: {
                        plugins: {
                            ptype: 'gridviewdragdrop',
                            dragGroup: 'evclassgriddd'
                        }
                    }
                },{
                    xtype: 'configpropertypanel',
                    id: 'configpanel_id'
                },{
                    xtype: 'overriddenobjects',
                    id: 'overriddengrid_id'
                },{
                    xtype: 'xformmasterpanel'
                },
                    event_console

            ]
        }]
    });

    function getOrganizerFields(mode) {
        var items = [];

        if ( mode === 'add' ) {
            items.push({
                xtype: 'textfield',
                id: 'add_id',
                name: 'id',
                fieldLabel: _t('Name'),
                anchor: '80%',
                regex: Zenoss.env.textMasks.allowedNameText,
                regexText: Zenoss.env.textMasks.allowedNameTextFeedback,
                allowBlank: false
            });
        }

        items.push({
            xtype: 'textfield',
            id: 'description_id',
            name: 'description',
            regex: Zenoss.env.textMasks.allowedDescText,
            regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
            fieldLabel: _t('Description'),
            anchor: '80%',
            allowBlank: true
        });

        var rootId = classtree.root.id;// sometimes the page loads with nothing selected and throws error. Need a default.
        if(getSelectionModel().getSelectedNode()) {
            rootId = getSelectionModel().getSelectedNode().getOwnerTree().root.id;
        }
        return items;
    }

    // Footer bar for the main Even Class page.
    // This extends Zenoss.footerHelper in FooterBar.js
    /* ------------------------------------------------------------------------------ FOOTER --------------------------------- */
    var footerBar = Ext.getCmp('footer_bar');
        Zenoss.footerHelper(
        '',
        footerBar,
        {
            hasOrganizers: false,

            // this footer bar has an add to zenpack option, but it defines its
            // own in contrast to using the canned one in footerHelper
            addToZenPack: false,

            // the message to display when user hits the [-] delete button.
            onGetDeleteMessage: function (itemName) {
                var node = getSelectionModel().getSelectedNode(),
                    tree = node.getOwnerTree(),
                    rootId = tree.getRootNode().data.id,

                    msg = _t('Are you sure you want to delete the {0} {1}? <br/>There is <strong>no</strong> undo.');
                if (rootId===classtree.root.id) {
                    msg = [msg, '<br/><br/><strong>',
                           _t('WARNING'), '</strong>:',
                           _t(' This will also delete all classes in this {0}.'),
                           '<br/>'].join('');
                }
                msg = "";
                return Ext.String.format(msg, itemName.toLowerCase(), '/'+node.data.path);
            },
            onGetAddDialogItems: function () {
                // add new item to tree
                return getOrganizerFields('add');
            },
            onGetItemName: function() {
                // runs when adding new organizer
                // runs 2x when hitting delete
                var node = getSelectionModel().getSelectedNode();
                if ( node ) {
                    var tree = node.getOwnerTree();
                    return tree.nodeName;
                }
            },
            customAddDialog: {
            },
            buttonContextMenu: {
            xtype: 'ContextConfigureMenu',
                onSetContext: function(uid) {
                    Zenoss.env.PARENT_CONTEXT = uid;
                },
                onGetMenuItems: function() {
                    var menuItems = [];
                    menuItems.push({
                        xtype: 'menuitem',
                        text: _t('Edit'),
                        hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        handler: function() {
                            var node = getSelectionModel().getSelectedNode();
                            var dialog = new Zenoss.SmartFormDialog({
                                title: _t('Edit Event Class Description'),
                                formId: 'editDialog',
                                items: getOrganizerFields()
                            });
                            dialog.setSubmitHandler(function(values) {
                                REMOTE.editEventClassDescription({'uid':node.get("uid"),'description':values.description}, function(response){
                                    if(response.success){
                                        var tree = getSelectionModel().getSelectedNode().getOwnerTree();
                                        tree.refresh();
                                        tree.getStore().on('load', function(){
                                            tree.expandToChild(node);
                                        }, this, {single:true});
                                    }
                                });
                            });
                            dialog.on('beforerender', function(){
                                Ext.getCmp('description_id').setValue(node.data.text.description);
                            });
                            dialog.show();
                        }
                    });
                    menuItems.push({
                        xtype: 'menuitem',
                        text: _t('Add to ZenPack'),
                        hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        handler: function() {
                            var addToZenPackDialog = new Zenoss.AddToZenPackWindow({}),
                                node = getSelectionModel().getSelectedNode();
                            if (!Ext.isEmpty(node)) {
                                addToZenPackDialog.setTarget(node.get('uid'));
                                addToZenPackDialog.show();
                            }
                        }
                    });
                    return menuItems;
                }
            }
        }
    );

    footerBar.on('buttonClick', function(actionName, id, values) {
        var tree = getSelectionModel().getSelectedNode().getOwnerTree();
        switch (actionName) {
            // All items on this are organizers, no classes
            case 'addClass': tree.addChildNode(Ext.apply(values, {type: 'organizer'})); break;
            case 'addOrganizer': throw new Ext.Error('Not Implemented');
            case 'delete': tree.deleteSelectedNode(); break;
            default: break;
        }
    });

    // if there is no history, select the top node
    if (!Ext.History.getToken()) {
        var tree = Ext.getCmp('classes');
        Ext.History.add(tree.id + Ext.History.DELIMITER + tree.getRootNode().id);
    }

}); // Ext. OnReady
