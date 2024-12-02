/* global unescape:true */
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.ns('Zenoss', 'Zenoss.Network', 'Zenoss.Form');

Ext.onReady(function () {

//********************************************
// Add/remove sub-network buttons and dialog
//********************************************

var treeConfigs = new Ext.util.MixedCollection(false, function(config) {
    return config.root.uid;
});

treeConfigs.addAll([{
    id: 'networks',
    root: {
        id: '.zport.dmd.Networks',
        uid: '/zport/dmd/Networks',
        text: null, // Use the name loaded from the remote
        allowDrop: false
    },
    // TODO: Make selectByPath work with trees and then change this to asyncGetTree
    directFn: Zenoss.remote.NetworkRouter.getTree,
    searchField: true,
    router: Zenoss.remote.NetworkRouter
}, {
    id: 'ipv6networks',
    root: {
        id: '.zport.dmd.IPv6Networks',
        uid: '/zport/dmd/IPv6Networks',
        text: 'IPv6 Networks', // Use the name loaded from the remote
        allowDrop: false
    },
    selectRootOnLoad: false,
    directFn: Zenoss.remote.Network6Router.getTree,
    searchField: true,
    loadMask: false,
    router: Zenoss.remote.Network6Router
}]);

var getRootId = function(fn) {
    var config;
    treeConfigs.each(function(item) {
        if (Zenoss.env.PARENT_CONTEXT.indexOf(item.root.uid) === 0) {
            config = item;
            return false; //stops iteration
        }
        return true;
    });
    if (fn) {
        return fn(config);
    }
    return config.id;
};

var addNetwork = function(id) {
    var tree = Ext.getCmp(getRootId());

    tree.router.addNode({newSubnet: id, contextUid: Zenoss.env.PARENT_CONTEXT},
        function(data) {
            if (data.success) {
                tree.refresh();
            }
        }
    );
};

var deleteNetwork = function() {
    var tree = Ext.getCmp(getRootId()),
        node = tree.getSelectionModel().getSelectedNode(),
        parentNode = node.parentNode,
        uid = node.data.uid;

    tree.router.deleteNode({uid:uid},
        function(data) {
            if (data.success) {
                tree.selectByToken(parentNode.get("id"));
                tree.addHistoryToken(tree.getView(), parentNode);
                tree.refresh();
            }
        }
    );
};

var discoverDevicesDialogSubmit = function() {
    var tree = Ext.getCmp(getRootId()),
        node = tree.getSelectionModel().getSelectedNode();
    tree.router.discoverDevices({uid: node.get("uid")});
};

var addNetworkDialogConfig = {
    title: _t('Add a Subnetwork'),
    items: [{
        xtype: 'textfield',
        name: 'id',
        vtype: 'ipaddresswithnetmask',
        fieldLabel: _t('Network / Subnet mask'),
        anchor: '80%',
        allowBlank: false,
        listeners: {
            validitychange: function(field, isvalid) {
                var win = field.ownerCt.ownerCt,
                    btn = win.query("button[ref='buttonSubmit']")[0];
                btn.setDisabled(!isvalid);
            }
        }
    }]
};

var discoverDevicesDialog = new Zenoss.MessageDialog({
    id: 'discoverDevicesDialog',
    title: _t('Discover Devices'),
    message: _t('Devices on the selected subnetwork will be discovered.'),
    okHandler: discoverDevicesDialogSubmit
});

//********************************************
// Navigation tree (select subnetwork)
//********************************************
function deselectOtherTree(treeid) {
    var tree, sm;
    if (treeid === 'ipv6networks') {
        tree = Ext.getCmp('networks');
    } else {
        tree = Ext.getCmp('ipv6networks');
    }
    sm = tree.getSelectionModel();
    if (sm.getSelectedNode()) {
        sm.deselect(sm.getSelectedNode(), true);
    }
}

function treeselectionchange(sm, newnodes) {
    deselectOtherTree(sm.id);
    Zenoss.env.treems = sm;
    if (!newnodes.length) {
        return;
    }
    var newnode = newnodes[0];
    var uid = newnode.data.uid;

    Ext.getCmp('NetworkDetailCardPanel').setContext(uid);

    if (Zenoss.Security.doesNotHavePermission('Manage DMD')) {
        return;
    }
    Ext.getCmp('network_context_menu').setContext(uid);
    Zenoss.env.PARENT_CONTEXT = uid;

    Ext.getCmp('footer_delete_button').setDisabled(treeConfigs.containsKey(uid));
}

Ext.define("Zenoss.Network.NetworkNavTree", {
    alias:['widget.networknavtree'],
    extend:"Zenoss.HierarchyTreePanel",

    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            selModel: Ext.create('Zenoss.TreeSelectionModel', {
                id: config.id,
                listeners: {
                    selectionchange: treeselectionchange
                }
            })
        });

        Zenoss.Network.NetworkNavTree.superclass.constructor.call(this, config);
    },
    selectByToken: function(tokenTreePath) {
        function selectTokenPath() {
            // called from onLoad and Ext.History.selectByToken defined in
            // HistoryManager.js. If node is null when called from the History
            // change event, then the TreePanel load event will call this function
            // when getNodeById is ready.
            var subParts = unescape(tokenTreePath).split('.ipaddresses.');
            var tokenNodeId = subParts[0];
            var node = this.getRootNode().findChild("id", tokenNodeId, true), selectIpAddress;

            if (node) {
                this.getSelectionModel().select(node);
                if (node.isExpandable()){
                    node.expand();
                }
                this.expandToChild(node);
                var ipAddress = subParts[1];
                var instanceGrid = Ext.getCmp('NetworkDetailCardPanel').getInstancesGrid();
                var store = instanceGrid.getStore();
                var selModel = instanceGrid.getSelectionModel();

                selectIpAddress = function() {
                    store.each(function(record){
                        if ( record.data.name === ipAddress ) {
                            selModel.selectRange( store.indexOf(record), store.indexOf(record) );
                            return false;
                        }
                    });
                };

                selectIpAddress();

                if ( ! selModel.hasSelection() ) {
                    // no row selectected, wait for the store to load and try again
                    store.on('load', selectIpAddress, store, {single:true});
                }
            }
        }
        this.getRootNode().on('expand', selectTokenPath, this, {single:true});
        Zenoss.HierarchyTreePanel.prototype.selectByToken.call(this, tokenTreePath);
    }
});



var treePanelItems = {
    xtype: 'HierarchyTreePanelSearch',
    items: []
};
treeConfigs.each(function(config) {
    treePanelItems.items.push(new Zenoss.Network.NetworkNavTree(config));
});


Ext.getCmp('master_panel').add(treePanelItems);

//********************************************
// IP Addresses grid
//********************************************

var statusRenderer = function (statusNum) {
    var color = 'red',
        desc = _t('Down');
    if (statusNum === 0) {
        color = 'green';
        desc = _t('Up');
    }
    else if (statusNum === 5) {
        color = 'gray';
        desc = _t('N/A');
    }
    return '<span style="color:' + color + '">' + desc + '</span>';
};

var ipAddressColumnConfig = [{
    id: 'name',
    dataIndex: 'name',
    header: _t('Address / Netmask'),
    sortable: true,
    flex: 1,
    width: 50,
    renderer: function(name, row, record) {
        return record.data.netmask ? name + '/' + record.data.netmask :
            name;
    }
}, {
    id: 'mangeDevice',
    dataIndex: 'manageDevice',
    header: _t('Manage Device'),
    sortable: true,
    width: 200,
    renderer: function(manageDevice) {
        if (!manageDevice) {
            return _t('No Device');
        }
        return Zenoss.render.link(manageDevice.uid, null, manageDevice.name);
    }
}, {
    id: 'interface',
    dataIndex: 'interface',
    header: _t('Interface / Device'),
    sortable: true,
    width: 300,
    renderer: function(iface){
        if (!iface) {
            return _t('No Interface');
        }
        return Zenoss.render.link(iface.uid, null, iface.name) + " / " + Zenoss.render.link(iface.device.uid, null, iface.device.name);
    }
},{
    id: 'macAddress',
    dataIndex: 'macAddress',
    sortable: true,
    header: _t('MAC Address'),
    width: 120
},{
    id: 'interfaceDescription',
    dataIndex: 'interfaceDescription',
    sortable: true,
    header: _t('Interface Desc.'),
    width: 150
}, {
    id: 'pingstatus',
    dataIndex: 'pingstatus',
    header: _t('Ping'),
    filter: false,
    sortable: false,
    width: 50,
    renderer: function(pingNum){
        return statusRenderer(pingNum);
    }
}, {
    id: 'snmpstatus',
    dataIndex: 'snmpstatus',
    header: _t('SNMP'),
    filter: false,
    sortable: false,
    width: 50,
    renderer: function(snmpNum){
        return statusRenderer(snmpNum);
    }
}
];


/**
 * @class Zenoss.network.IpAddressModel
 * @extends Ext.data.Model
 * Field definitions for the ip address grid
 **/
Ext.define('Zenoss.network.IpAddressModel',  {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: [
        {name: 'name'},
        {name: 'netmask'},
        {name: 'macAddress'},
        {name: 'interfaceDescription'},
        {name: 'device'},
        {name: 'interface'},
        {name: 'manageDevice'},
        {name: 'pingstatus'},
        {name: 'snmpstatus'},
        {name: 'uid'}
    ]
});

/**
 * @class Zenoss.network.IpAddressStore
 * @extend Zenoss.DirectStore
 * Direct store for loading ip addresses
 */
Ext.define("Zenoss.network.IpAddressStore", {
    extend: "Zenoss.DirectStore",
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            model: 'Zenoss.network.IpAddressModel',
            pageSize: 200,
            initialSortColumn: "name",
            directFn: Zenoss.remote.NetworkRouter.getIpAddresses,
            root: 'data'
        });
        this.callParent(arguments);
    }
});


var ipAddressGridConfig = {
        xtype: 'instancecardpanel',
        id: 'NetworkDetailCardPanel',
        region: 'center',
        collapsed: false,
        split: true,
        router: Zenoss.remote.NetworkRouter,
        instancesTitle: _t('IP Addresses'),
        columns: ipAddressColumnConfig,
        store: Ext.create('Zenoss.network.IpAddressStore', {}),
        sm: Ext.create('Zenoss.ExtraHooksSelectionModel', {
            mode: 'MULTI'
        })
    };
Ext.getCmp('detail_panel').add(ipAddressGridConfig);

(function(){
    // Remove extraneous toolbar items since we don't hide this panel
    var detailCardPanel = Ext.getCmp('NetworkDetailCardPanel'),
        toolbar = detailCardPanel.getDockedItems('toolbar')[0];
    Ext.each(toolbar.items.items.slice(2), function(item) {
        toolbar.remove(item);
    });
    // Set the toolbar's height since we removed the large icon
    toolbar.setHeight(31);

    toolbar.add( {
            xtype: 'button',
            iconCls: 'delete',
            handler: deleteIpAddresses
        },{
            xtype: 'tbspacer',
            width: 5
        }, {
            id: 'network-descriptionField',
            xtype: 'tbtext'
        },
        '->',
        {
            id: 'network-ipcountField',
            xtype: 'tbtext'
    });

    var oldSetContext = detailCardPanel.setContext;

    detailCardPanel.setContext = function(contextUid) {
        Zenoss.remote.NetworkRouter.getInfo( {
            uid: contextUid,
            keys: ['id', 'description', 'ipcount']
            },
            function(infoData) {
                Ext.getCmp('network-descriptionField').setText(
                    infoData.success ? Ext.htmlEncode(infoData.data.description) : '');
                Ext.getCmp('network-ipcountField').setText(
                    infoData.success ? 'IPs Used/Free: ' + infoData.data.ipcount : '');
                detailCardPanel.doLayout();
            }
        );

        return oldSetContext.call(this, contextUid);
    };
})();

//********************************************
// Delete Ip Addresses
//********************************************
function reloadGridAndTree() {
    var trees = [Ext.getCmp('networks'), Ext.getCmp('ipv6networks')];
    Ext.each(trees, function(tree){
        tree.refresh();
    });
    Ext.getCmp('NetworkDetailCardPanel').getInstancesGrid().refresh();
}


function deleteIpAddresses() {
    var grid = Ext.getCmp('NetworkDetailCardPanel').getInstancesGrid(),
        selections = grid.getSelectionModel().getSelection(),
        router = Zenoss.remote.NetworkRouter,
        uids;
    if (!selections.length) {
        // don't do anything
        return;
    }

    uids = Ext.Array.pluck(Ext.Array.pluck(selections, 'data'), 'uid');
    new Zenoss.dialog.SimpleMessageDialog({
        title: _t('Delete IP Addresses'),
        message: _t("Are you sure you want to delete these IP addresses? Please note that only IP addresses without interfaces can be deleted."),
        buttons: [{
            xtype: 'DialogButton',
            text: _t('OK'),
            handler: function() {
                router.removeIpAddresses({uids: uids}, function(response){
                    if (response.removedCount) {
                        Zenoss.message.info(_t("Deleted {0} IP addresses."), response.removedCount);
                        reloadGridAndTree();
                    }
                    if (response.errorCount) {
                        Zenoss.message.warning(_t("Unable to delete {0} IP addresses."), response.errorCount);
                    }
                });
            }
        }, {
            xtype: 'DialogButton',
            text: _t('Cancel')
        }]
    }).show();
}


//********************************************
// Footer
//********************************************

var dispatcher = function(actionName, value) {
    switch (actionName) {
        case 'addClass': addNetwork(value); break;
        case 'delete': deleteNetwork(); break;
        default: break;
    }
};

// Edit description dialog
var showEditDescriptionDialog = function() {
    var dialog = new Zenoss.SmartFormDialog({
        title: _t('Edit Description'),
        formId: 'editDescriptionDialog',
        items: [{
            xtype: 'textfield',
            id: 'description',
            name: 'description',
            anchor: '80%',
            fieldLabel: _t('Description'),
            allowBlank: true
            }],
        formApi: {
            load: Zenoss.remote.NetworkRouter.getInfo
        }
    });

    dialog.setSubmitHandler(function(values) {
        values.uid = Zenoss.env.PARENT_CONTEXT;
        Zenoss.remote.NetworkRouter.setInfo(values);
        Ext.getCmp('NetworkDetailCardPanel').setContext(values.uid);
    });

    dialog.getForm().load({
        params: { uid: Zenoss.env.PARENT_CONTEXT, keys: ['id', 'description'] },
        success: function() {
            dialog.show();
        },
        failure: function(form, action) {
            Ext.Msg.alert('Error', action.result.msg);
        }
    });
};


var fb = Ext.getCmp('footer_bar');
fb.on('buttonClick', dispatcher);
Zenoss.footerHelper('Subnetwork', fb, {
    hasOrganizers: false,
    addToZenPack: false,
    customAddDialog: addNetworkDialogConfig,
    buttonContextMenu: {
        xtype: 'ContextConfigureMenu',
        id: 'network_context_menu',
        menuIds: ['Network'],
        onGetMenuItems: function() {
            return [{
                tooltip: _t('Discover devices on selected subnetwork'),
                text: _t('Discover Devices'),
                iconCls: 'adddevice',
                ref: 'buttonDiscoverDevices',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD') ||
                    treeConfigs.containsKey(Zenoss.env.PARENT_CONTEXT) ||
                    Zenoss.env.PARENT_CONTEXT.indexOf('IPv6Networks') >= 0,
                handler: Ext.bind(discoverDevicesDialog.show, discoverDevicesDialog)
            },{
                tooltip: _t('Edit network description'),
                text: _t('Edit description'),
                ref: 'buttonEditDescription',
                disabled: Zenoss.Security.doesNotHavePermission('Manage DMD') ||
                    treeConfigs.containsKey(Zenoss.env.PARENT_CONTEXT),
                handler: showEditDescriptionDialog
            }];
        }
    }
});

});
