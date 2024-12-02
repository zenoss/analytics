/* globals unescape:true */
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

var router, treeId, initTreeDialogs;

router = Zenoss.remote.TemplateRouter;
treeId = 'templateTree';



/**
 * The two default views
 **/
Ext.ns('Zenoss', 'Zenoss.templates');
Zenoss.templates.templateView = 'template';
Zenoss.templates.deviceClassView = 'deviceClass';


initTreeDialogs = function(tree) {

    new Zenoss.HideFormDialog({
        id: 'addTemplateDialog',
        title: _t('Add Monitoring Template'),
        items: {
            xtype: 'textfield',
            id: 'idTextfield',
            fieldLabel: _t('Name'),
            allowBlank: false
        },
        listeners: {
            'hide': function() {
                Ext.getCmp('idTextfield').setValue('');
            }
        },
        buttons: [
            {
                xtype: 'HideDialogButton',
                text: _t('Submit'),
                handler: function() {
                    var id = Ext.getCmp('idTextfield').getValue();
                    tree.addTemplate(id);
                }
            }, {
                xtype: 'HideDialogButton',
                text: _t('Cancel')
            }
        ]
    });

    new Zenoss.MessageDialog({
        id: 'deleteNodeDialog',
        title: _t('Delete Tree Node'),
        message: _t('The selected node will be deleted.'),
        okHandler: function(){
            tree.deleteTemplate();
        }
    });

};

Ext.ns('Zenoss');

/**
 * @class Zenoss.TemplateTreePanel
 * @extends Ext.tree.TreePanel
 * @constructor
 */
Ext.define("Zenoss.TemplateTreePanel", {
    alias: ['widget.TemplateTreePanel'],
    extend:"Zenoss.HierarchyTreePanel",

    constructor: function(config) {
        var currentView = config.currentView,
            directFn = router.getTemplates;
        if (currentView === Zenoss.templates.deviceClassView) {
            directFn = router.getDeviceClassTemplates;
        }
        this.currentView = currentView;

        Ext.applyIf(config, {
            id: treeId,
            rootVisible: false,
            autoScroll: true,
            containerScroll: true,
            useArrows: true,
            searchField: true,
            loadMask: true,
            router: router,
            cls: 'x-tree-noicon',
            idProperty: 'id',
            directFn: directFn,
            nodeName: 'Templates',
            root: {
                id: 'root',
                uid: '/zport/dmd/Devices',
                text: _t('Templates')
            }
        });

        this.callParent(arguments);
        initTreeDialogs(this);
        this.on('buttonClick', this.buttonClickHandler, this);
    },
    buttonClickHandler: function(buttonId) {
        switch(buttonId) {
            case 'addButton':
                Ext.getCmp('addTemplateDialog').show();
                break;
            case 'deleteButton':
                Ext.getCmp('deleteNodeDialog').show();
                break;
            default:
                break;
        }
    },

    addTemplate: function(id) {
        var rootNode, contextUid, params, tree;
        rootNode = this.getRootNode();
        contextUid = rootNode.data.uid;
        params = {contextUid: contextUid, id: id};
        tree = this;
        function callback(provider, response) {
            var result, nodeConfig, node, leaf;
            result = response.result;
            if (result.success) {
                nodeConfig = response.result.nodeConfig;
                node = tree.getLoader().createNode(nodeConfig);
                rootNode.appendChild(node);
                node.expand();
                leaf = node.childNodes[0];
                leaf.select();
            } else {
                Ext.Msg.alert('Error', result.msg);
            }
        }
        router.addTemplate(params, callback);
    },

    deleteTemplate: function() {
        var node, params, me;
        node = this.getSelectionModel().getSelectedNode();
        params = {uid: node.data.uid};
        me = this;
        function callback() {
            me.getRootNode().reload();
        }
        router.deleteTemplate(params, callback);
    },

    createDeepLinkPath: function(node) {
        var path;
        if (this.currentView !== Zenoss.templates.deviceClassView) {
            path = this.id + Ext.History.DELIMITER + node.data.uid;
        }else {
            path = this.id + Ext.History.DELIMITER + node.get("id");
        }

        return path;
    },
    onExpandnode: function(node) {
        // select the first template when the base URL is accessed without a
        // history token and without a filter value
        if ( ! this.searchField.getValue() && ! Ext.History.getToken() ) {
            if ( node === this.getRootNode() ) {
                node.childNodes[0].expand();
            } else {
                node.childNodes[0].select();
            }
        }
    },
    selectByToken: function(id) {
        if (this.currentView === Zenoss.templates.deviceClassView){
            this.callParent([unescape(id.replace(/\//g, '.'))]);
        }else{
            this.templateViewSelectByToken(id);
        }
    },
    getFilterFn: function(text) {
        if (this.currentView !== Zenoss.templates.deviceClassView){
            var regex = new RegExp(Ext.String.escapeRegex(text),'i');
            var fn = function(item){
                return regex.test(item.get('id'));
            };
            return fn;
        }
        // match against the displayed text
        return this.callParent(arguments);
    },
    addHistoryToken: function(view, node) {
        Ext.History.add(this.id + Ext.History.DELIMITER + node.get('uid'));
    },
    templateViewSelectByToken: function(uid) {
        var root = this.getRootNode(),
            selNode = Ext.bind(function(){
                // Translates from the History token into the
                // path for the tree
                // for example this:
                //     "/zport/dmd/Devices/rrdTemplates/ethernetCsmacd"
                // turns into:
                //     "/root/ethernetCsmacd/ethernetCsmacd..Devices"
                var templateSplit, pathParts, nameParts,
                templateName, dmdPath, path;

                if (uid.search('/rrdTemplates/') !== -1) {
                    // this is a device class
                    templateSplit = unescape(uid).split('/rrdTemplates/');
                    pathParts = templateSplit[0].split('/');
                    nameParts = templateSplit[1].split('/');
                    templateName = nameParts[0];
                } else {
                    // it is a template on a device
                    pathParts = uid.split('/');
                    templateName = pathParts.pop();

                    // determine if this is a component
                    var devicesIndex = pathParts.indexOf("devices");
                    if((pathParts.length - 1) > devicesIndex){
                        pathParts.splice(devicesIndex + 2, 1);
                        pathParts.splice(devicesIndex, 1);
                    }
                }

                if ( pathParts.length === 4 ) {
                    // Defined at devices, special case, include 'Devices'
                    dmdPath = 'Devices';
                } else {
                    // all the DeviceClass names under Devices separated by dots
                    dmdPath = pathParts.slice(4).join('.');
                }
                path = Ext.String.format('/root/{0}/{0}..{1}', templateName, dmdPath);
                this.selectPath(path);
            }, this);
        if (!root.isLoaded()) {
            // Listen on expand because if we listen on the store's load expand
            // gets double-called.
            root.on('expand', selNode, this, {single: true});
        } else {
            selNode();
        }

    },

    manualSelect: function(uid, templateName) {
        var theTree = this;
        var callback = function(success) {
            if (!success) {
                theTree.getRootNode().eachChild(function(node) {
                    if (templateName === node.data.id){
                        node.eachChild(function(node){
                            if (uid === node.data.uid) {
                                node.select();
                                return false;
                            }
                        });
                        return false;
                    }
                });
            }
        };
        return callback;
    }

});



})();
