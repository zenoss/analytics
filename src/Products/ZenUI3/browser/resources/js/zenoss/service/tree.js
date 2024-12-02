/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

    var zs = Ext.ns('Zenoss.Service.Nav');

    /**********************************************************************
    *
    * Tree Navigation Functionality
    *
    */

    zs.getSelectedOrganizer = function() {
        var tree, selected;
        tree = Ext.getCmp('navTree');
        selected = tree.getSelectionModel().getSelectedNode();
        if ( ! selected ) {
            // No node is really selected (a ServiceClass is selected in the
            // navGrid). Find the node that had the selected css class added
            // to it when the ServiceClass was selected
            tree.getRootNode().cascade(function(node){
                // TreeNodeUI delegates addClass and removeClass to it's
                // elNode, but not hasClass (so this gets ugly)
                var wrap = node.getUI().getEl();
                var elNode = wrap.childNodes[0];
                if ( Ext.fly(elNode).hasClass('x-tree-selected') ) {
                    selected = node;
                    return false;
                }
            });
        }
        return selected;
    };

    zs.treeBeforeSelectHandler = function(sm, node, oldNode) {
        var form = Ext.getCmp('serviceForm').getForm();
        if ( form.isDirty() ) {
            Ext.MessageBox.show({
                title: _t('Unsaved Data'),
                msg: _t('The changes made in the form will be lost.'),
                fn: function(buttonid){
                    if (buttonid==='ok') {
                        form.reset();
                        node.select();
                    }
                },
                buttons: Ext.MessageBox.OKCANCEL
            });
            return false;
        }

        return true;
    };

    // function that gets run when the user clicks on a node in the tree
    zs.treeSelectionChangeHandler = function(sm, nodes) {
        var oldToken, newToken, token, remainder, remainderParts, isRoot, node;
        if (nodes.length) {
            node = nodes[0];
            Ext.getCmp('serviceForm').setContext(node.data.uid);
            Ext.getCmp('detail_panel').detailCardPanel.setContext(node.data.uid);
            Zenoss.env.PARENT_CONTEXT = node.data.uid;

            oldToken = unescape(Ext.History.getToken());
            newToken = 'navTree' + Ext.History.DELIMITER + node.get("id");
            if ( oldToken.indexOf(newToken + '.serviceclasses.') !== 0 ) {
                Ext.History.add(newToken);
                token = newToken;
            } else {
                token = oldToken;
            }

            Ext.getCmp('navGrid').getSelectionModel().clearSelections();
            Ext.getCmp('navGrid').setContext(node.get('uid'));
            if (token) {
                remainder = token.split(Ext.History.DELIMITER)[1];
                if ( remainder ) {
                    remainderParts = remainder.split('.serviceclasses.');
                    if ( remainderParts[1] ) {
                        Ext.getCmp('navGrid').filterAndSelectRow(remainderParts[1]);
                    } else {
                        Ext.getCmp('navGrid').setFilter('name', '');
                    }
                }
            }

            isRoot = node === Ext.getCmp('navTree').getRootNode();
            Ext.getCmp('footer_bar').buttonDelete.setDisabled(isRoot);
        }
    };

    var selModel = new Zenoss.TreeSelectionModel({
        listeners: {
            beforeselect: zs.treeBeforeSelectHandler,
            selectionchange: zs.treeSelectionChangeHandler
        }
    });

    Ext.define("Zenoss.Service.Nav.ServiceTreePanel", {
        extend:"Zenoss.HierarchyTreePanel",
        alias: ['widget.servicetreepanel'],

        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                id: 'navTree',
                flex: 1,
                cls: 'x-tree-noicon',
                searchField: false,
                directFn: Zenoss.remote.ServiceRouter.getOrganizerTree,
                router: Zenoss.remote.ServiceRouter,
                selModel: selModel,
                selectRootOnLoad: true,
                viewConfig: {
                    loadMask: true,
                    plugins: {
                        ptype: 'treeviewdragdrop',
                        enableDrag: Zenoss.Security.hasPermission('Change Device'),
                        enableDrop: Zenoss.Security.hasPermission('Change Device'),
                        ddGroup: 'serviceDragDrop'
                    },
                    listeners: {
                        beforedrop: Ext.bind(this.onNodeDrop, this)
                    }
                },
                listeners: {
                    scope: this,
                    expandnode: this.onExpandnode
                }
            });
            this.callParent(arguments);
        },
        onNodeDrop: function(element, event, target) {
            var sourceUids, targetUid, targetId;
            sourceUids = Ext.Array.pluck(Ext.Array.pluck(event.records, "data"), "uid");
            targetUid = target.get("uid");
            targetId = target.data.id;

            Zenoss.remote.ServiceRouter.moveServices(
                {
                    sourceUids: sourceUids,
                    targetUid: targetUid
                }, function () {
                    this.moveServicesCallback(targetId);
                },
                this);
        },
        moveServicesCallback: function(targetId) {
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
            var tokenParts;
            token = unescape(token);
            tokenParts = token.split('.serviceclasses.');
            this.callParent([tokenParts[0]]);

            if (tokenParts[1]) {
                Ext.getCmp('navGrid').filterAndSelectRow(tokenParts[1]);
            }
        },

        initEvents: function() {
            zs.ServiceTreePanel.superclass.initEvents.call(this);
            // don't add history token on click like HierarchyTreePanel does
            // this is handled in the selection model
            this.un('itemclick', this.addHistoryToken, this);
        }

    });


})();
