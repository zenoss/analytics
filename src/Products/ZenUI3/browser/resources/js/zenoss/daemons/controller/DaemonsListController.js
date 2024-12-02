/* global Daemons */
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    var router = Zenoss.remote.ApplicationRouter;
    var HOSTS = {};
    Zenoss.remote.HostRouter.getAllHosts({}, function(response){
        if(response.success){
            HOSTS = response.data;
        }
    });

    Zenoss.render.hostIdtoHostname = function(value){
        return Ext.isDefined(HOSTS[value]) ? HOSTS[value].name : "";
    };

    /**
     * @class Daemons.controller.DaemonsListController
     * This is the controller for the list of control plane services and collector daemons.
     * @extends Ext.app.Controller
     */
    Ext.define('Daemons.controller.DaemonsListController', {
        models: ["Daemon"],
        views: [
            "daemons.List"
        ],
        refs: [{
            ref: 'treegrid',
            selector: 'daemonslist'
        }],
        extend: 'Ext.app.Controller',

        /**
         * This is a list of daemons that are currently restarting.
         * when it is not empty we will periodically check the server to get the
         * status and when it is not restarting anymore we update the icon.
         **/
        restartingDaemons: {},

        init: function() {
            // toolbar button handlers
            this.control(Ext.apply(Daemons.ListControllerActions || {}, {
                // start
                'daemonslist button[ref="start"]': {
                    click: this.startSelectedDaemons
                },
                // stop
                'daemonslist button[ref="stop"]': {
                    click: this.stopSelectedDaemons
                },
                // restart
                'daemonslist button[ref="restart"]': {
                    click: this.restartSelectedDaemons
                },
                // Column Actions
                // restart
                'daemonslist actioncolumn[ref="restartcolumn"]': {
                    click: Ext.bind(function(grid, cell, colIdx, rowIdx, event, record) {
                        this.updateRefreshIcon([record]);
                        this.updateSelectedDaemons([record], 'restart', 'state', Daemons.states.RESTARTING);
                    }, this)
                },
                // start/stop
                'daemonslist actioncolumn[ref="statuscolumn"]': {
                    click: Ext.bind(function(grid, cell, colIdx, rowIdx, event, record) {
                        // find out if we need to stop or start the record
                        if (record.get('state') === 'up') {
                            this.updateSelectedDaemons([record], 'stop', 'state', Daemons.states.STOPPED);
                        } else {
                            this.updateSelectedDaemons([record], 'start', 'state', Daemons.states.RUNNING);
                        }
                    }, this)
                },
                // enable/disable
                'daemonslist actioncolumn[ref="autostart"]': {
                    click: Ext.bind(function(grid, cell, colIdx, rowIdx, event, record) {
                        this.setAutoStartDaemons([record], !record.get('autostart'));
                    }, this)
                },
                // update the details information
                'daemonslist': {
                    select: this.setupDetails,
                    load: function() {
                        this.deepLinkFromHistory();
                    }
                },
                'daemonslist treeview': {
                    beforedrop: this.assignDevicesToCollector
                },
                'daemonslist daemonsearchfield': {
                    keydown: Ext.bind(function(input) {
                        if (!this.filterTask) {
                            this.filterTask = new Ext.util.DelayedTask(this.filterDaemonslist, this, [input]);
                        }
                        this.filterTask.delay(250);
                    }, this)
                }
            }));
        },
        filterDaemonslist: function(input) {
            var store = this.getTreegrid().getStore(),
                value = input.getValue(),
                reg;
            store.clearFilter(true);
            if (value.length === 0) {
                return;
            }

            reg = new RegExp(value, 'i');
            store.filter([{filterFn: function(item) {
                return (reg.test(item.get('name')) || reg.test(item.get('hostId')) || reg.test(item.get('id')));
            }}]);
        },
        /**
         * Updates the model representation of the selected rows
         * this will update the view as well.
         **/
        updateRows: function(selectedRows, field, value) {
            var i;
            for(i=0;i<selectedRows.length;i++) {
                selectedRows[i].set(field, value);
            }
            this.setupDetails();
        },
        /**
         * Performs the "action" on every selected daemon.
         **/
        updateSelectedDaemons: function(selectedRows, action, field, value) {
            var record,
                recordsToUpdate = [],
                uids = [],
                i=0;
            if (selectedRows.length) {

                // if it is an collector or hub then
                // perform the action on the child daemons
                for(i=0;i<selectedRows.length;i++) {
                    record = selectedRows[i];
                    if (record.isCollector() || record.isHub()) {
                        uids = uids.concat(this.getSubDaemonUids(record));
                        recordsToUpdate = recordsToUpdate.concat(this.getSubDaemons(record));
                    } else {
                        uids.push(record.get('uid'));
                        recordsToUpdate.push(record);
                    }

                }
                uids = Ext.Array.unique(uids);

                // call the server
                router[action]({
                    uids: uids
                }, function(response) {
                    if (response.success) {
                        // this will update the grid without refreshing it
                        this.updateRows(recordsToUpdate, field, value);
                    }
                }, this);
            }
        },
        getSubDaemonUids: function(record) {
            var records = this.getSubDaemons(record);
            return Ext.Array.pluck(Ext.Array.pluck(records, 'data'), 'uid');
        },
        getSubDaemons: function(record) {
            var daemons = [], children = record.childNodes || [];
            Ext.each(children, function(child) {
                if (child.isDaemon()) {
                    daemons.push(child);
                }
                if (child.isHub() || child.isCollector()) {
                    daemons = daemons.concat(this.getSubDaemons(child));
                }
            }, this);
            return daemons;
        },
        /**
         * Starts every daemon that is selected
         **/
        startSelectedDaemons: function() {
            this.updateSelectedDaemons(this.getTreegrid().getSelectionModel().getSelection(),
                                       'start', 'state', Daemons.states.RUNNING);
        },
        /**
         * Stops every daemon that is selected
         **/
        stopSelectedDaemons: function() {
            this.updateSelectedDaemons(this.getTreegrid().getSelectionModel().getSelection(),
                                       'stop', 'state', Daemons.states.STOPPED);
        },
        /**
         * restarts every daemon that is selected
         **/
        restartSelectedDaemons: function() {
            var selected = this.getTreegrid().getSelectionModel().getSelection();
            this.updateRefreshIcon(selected);
            this.updateSelectedDaemons(selected, 'restart', 'state', Daemons.states.RUNNING);
        },

        /**
         * Let the user know that the daemon is restarting.
         **/
        updateRefreshIcon: function(selectedRows) {
            var view = this.getTreegrid().getView(),
                i, el;
            for (i=0;i<selectedRows.length;i++) {
                el = view.getNode(selectedRows[i]).getElementsByClassName('restarticon')[0];
                el.src = '/++resource++zenui/img/ext4/icon/circle_arrows_ani.gif';
                this.restartingDaemons[selectedRows[i].get('id')] = {
                    row: selectedRows[i],
                    el: el
                };
            }
            this.pollForChanges();
        },

        /**
         * This periodically checks the current restarting daemons to see if they have finished
         * restarting.
         **/
        pollForChanges: function() {
            if (Ext.Object.getKeys(this.restartingDaemons).length === 0) {
                return;
            }
            if (!this.restartingTask) {
                this.restartingTask = new Ext.util.DelayedTask(this.doCheckForRestarting, this);
            }
            this.restartingTask.delay(1000);
        },
        doCheckForRestarting: function() {
            function callback(response) {
                var id = response.data.id;
                var record = this.restartingDaemons[id];
                if (!response.data.isRestarting && record.el) {
                    record.el.src = '/++resource++zenui/img/ext4/icon/circle_arrows_still.png';
                    delete this.restartingDaemons[id];
                }

                record.row.set('state', response.data.state);
            }

            for (var daemon in this.restartingDaemons ) {
                // check the server to see if we are still restarting
                router.getInfo({
                    id: this.restartingDaemons[daemon].row.get('id')
                }, callback, this);
            }
            this.pollForChanges();
        },

        /**
         * Updates the enabled flag for all the rows passed in.
         **/
        setAutoStartDaemons: function(rows, enabled) {
            var uids = [], i;
            for (i=0; i<rows.length; i++) {
                uids.push(rows[i].get('uid'));
                rows[i].set("autostart", enabled);
            }
            router.setAutoStart({
                uids: uids,
                enabled: enabled
            });
        },
        onRefresh: function() {
            var store = this.getTreegrid().getStore(),
                method = store.getProxy().directFn,
                expandedIds = [],
                rootNode = store.getRootNode(),
                rootId = rootNode.get("id"),
                nodes = {};
            expandedIds.push(rootId);
            var getExpandedChildren = function(n) {
                var i, currentNode;
                if (!n.hasChildNodes()) {
                    return;
                }
                for (i=0; i<n.childNodes.length; i++) {
                    currentNode = n.childNodes[i];
                    if (currentNode.isExpanded()) {
                        expandedIds.push(currentNode.get('id'));
                        getExpandedChildren(currentNode);
                    }
                }
            };
            getExpandedChildren(rootNode);
            method({
                id: expandedIds
            }, function(result){
                // this was an invalid resposne
                if (Ext.isDefined(result.success) && result.success === false) {
                    return;
                }
                var getChildren = function(n, parentId) {
                    var i=0, currentNode, modelNode, children;
                    for (i=0;i<n.length;i++) {
                        currentNode = n[i];
                        nodes[currentNode.id] = currentNode;
                        children = currentNode.children;
                        // see if we need to add it
                        modelNode = store.getNodeById(currentNode.id);
                        if (modelNode) {
                            modelNode.set(currentNode);
                        } else {
                            store.getNodeById(parentId).appendChild(currentNode);
                        }

                        if (children && children.length) {
                            getChildren(children, currentNode.id);
                        }
                    }
                };
                getChildren(result['children'], rootId);
                var nodeHash = store.tree.nodeHash, i, key, toRemove = [];

                // iterate through all the nodes in the store and make sure they
                // exits in the "nodes" struct
                for (key in nodeHash) {
                    if (nodeHash.hasOwnProperty(key) && !Ext.isDefined(nodes[key])) {
                        if (store.getNodeById(key).get('id') !== rootId) {
                            toRemove.push(store.getNodeById(key));
                        }
                    }
                }

                // remove all the nodes that were previously in the list but were not in the latest
                // refresh request
                for (i=0;i<toRemove.length;i++) {
                    var parentNode = toRemove[i].parentNode;
                    toRemove[i].remove();
                    // loaded=false to force reload node from router on next expansion
                    if (!parentNode.hasChildNodes()) {
                        parentNode.set({loaded: false});
                    }
                }
            });
        },
        /**
         * Lets the details panel know that we have a selected row
         **/
        setupDetails: function() {
            var grid = this.getTreegrid(), selected = grid.getSelectionModel().getSelection();
            if (selected.length) {
                this.getController('DetailsController').setContext(selected[0]);
                this.addHistory(selected[0].get("id"));
            }
        },
        addHistory: function(id) {
            Ext.History.add(id);
        },
        deepLinkFromHistory: function() {
            var token = Ext.History.getToken(),
                tree = this.getTreegrid(), node;

            if (token) {
                node = tree.getStore().getNodeById(token);
            }

            // if we were able to find the history select it otherwise
            // select the first visible node
            if (node) {
                tree.getSelectionModel().select(node);
            } else {
                tree.getSelectionModel().select(
                    tree.getRootNode().childNodes[0]
                );
            }
        },
        assignDevicesToCollector: function(node, data, treeNode){
            var records = data.records, me = this;
            // can only assign to collectors
            if (treeNode.get('type') === 'collector') {
                var win = Ext.create('Daemons.dialog.AssignCollectors', {
                    numRecords: records.length,
                    collectorId: treeNode.get('name'),
                    okHandler: function() {
                        // router request
                        var uids = Ext.Array.pluck(Ext.Array.pluck(records, 'data'), 'uid');
                        Zenoss.remote.DeviceRouter.setCollector({
                            uids: uids,
                            collector: treeNode.get('name'),
                            hashcheck: null
                        }, function(){
                            // will refresh the details
                            me.getController('DetailsController').refreshDevices();
                        });
                        win.close();
                    }
                });
                win.show();
            }
            return false;
        }
    });
})();
