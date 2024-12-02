/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function () {

    Ext.ns('Zenoss');

    /**
     * @class Zenoss.HierarchyTreePanel
     * @extends Ext.tree.TreePanel
     * The primary way of navigating one or more hierarchical structures. A
     * more advanced Subsections Tree Panel. Configurable as a drop target.
     * Accepts array containing one or more trees (as nested arrays). In at
     * least one case data needs to be asynchronous. Used on screens:
     *   Device Classification Setup Screen
     *   Devices
     *   Device
     *   Event Classification
     *   Templates
     *   Manufacturers
     *   Processes
     *   Services
     *   Report List
     * @constructor
     */



    /**
     * The default sort for hierarchical tree panels.
     * Show anything with a folder icon first and then sort Alpha.
     * by the "text" property.
     * To override this pass a custom sort function in the Tree Panel's
     * config.sortFn property.
     **/
    function sortTreeNodes(o1, o2) {
        function getText(object) {
            // text is sometimes an object and sometimes a string
            if (Ext.isObject(object.get('text'))) {
                return object.get('text').text.toLowerCase();
            }
            return object.get('text').toLowerCase();
        }

        function alphcmp(obj1, obj2) {
            var text1 = getText(obj1),
                text2 = getText(obj2);

            // sort by text
            if (text1 === text2) {
                return 0;
            }
            return text1 < text2 ? -1 : 1;
        }


        // always show folders first
        if (o1.get('iconCls') === 'folder' && o2.get('iconCls') !== 'folder') {
            return -1;
        }
        if (o2.get('iconCls') === 'folder' && o1.get('iconCls') !== 'folder') {
            return 1;
        }

        // otherwise sort by text
        return alphcmp(o1, o2);
    }

    Zenoss.sortTreeNodes = sortTreeNodes;

    /**
     * Base Tree Selection model for zenoss. Defines
     * the getSelectedNode method that existed in 3.X trees.
     **/
    Ext.define('Zenoss.TreeSelectionModel', {
        extend: 'Ext.selection.TreeModel',
        getSelectedNode: function () {
            var selections = this.getSelection();
            if (selections.length) {
                return selections[0];
            }
            return null;
        }

    });

    Ext.define('Zenoss.HierarchyTreePanelSearch', {
        extend: 'Ext.Panel',
        alias: ['widget.HierarchyTreePanelSearch'],
        constructor: function (config) {
            var oldConfig = config;
            config = {
                cls: 'x-hierarchy-search-panel',
                bodyStyle: 'background-color:#d4e0ee;',
                items: [
                    {
                        xtype: 'searchfield',
                        id: config.id || Ext.id(),
                        height: 25,
                        hidden: !Zenoss.settings.enableTreeFilters,
                        cls: 'x-hierarchy-search',
                        enableKeyEvents: true,
                        ref: 'searchfield'
                    },
                    {
                        xtype: 'panel',
                        ui: 'hierarchy',
                        padding: '5px 0 0 0',
                        items: oldConfig.items,
                        flex: 1,
                        autoScroll: true,
                        regSearchListeners: function (listeners) {
                            this.ownerCt.query('.searchfield')[0].on(listeners);
                        }
                    }
                ],
                layout: {
                    type: 'vbox',
                    align: 'stretch'
                },
                listeners: {
                    afterrender: function (t) {
                        // fixes 20000px width bug on the targetEl div bug in Ext
                        t.searchfield.container.setWidth(t.ownerCt.getWidth());
                    }
                }
            };

            Zenoss.HierarchyTreePanelSearch.superclass.constructor.call(this, config);
        }
    });

    /**
     *  Right click handlers for nodes.
     **/
    Zenoss.treeContextMenu = function (view, node, item, index, e, opti) {
        // Register the context node with the menu so that a Menu Item's handler function can access
        // it via its parentMenu property.
        var tree = view.panel;
        if (!tree.contextMenu) {
            tree.contextMenu = new Ext.menu.Menu({
                items: [
                    {
                        ref: 'refreshtree',
                        text: _t('Refresh Tree'),
                        handler: function (item, e) {
                            var tree = item.parentMenu.tree;
                            tree.getStore().load({
                                scope: tree,
                                callback: function (records, opts, success) {
                                    if (success) {
                                        var root = tree.getRootNode();
                                        var treeState = tree.getTreeState(root);
                                        var childNodes = opts.response.result[0];
                                        root.removeAll();
                                        root.appendChild(childNodes);
                                        tree.restoreTreeState(treeState);
                                    }
                                }
                            });
                        }
                    },
                    {
                        ref: 'expandall',
                        text: _t('Expand All'),
                        handler: function (item, e) {
                            var tree = item.parentMenu.tree;
                            tree.expandAll();
                        }
                    },
                    {
                        ref: 'collapsall',
                        text: _t('Collapse All'),
                        handler: function (item, e) {
                            var tree = item.parentMenu.tree;
                            tree.collapseAll();
                            // by default we usually expand the first child
                            tree.getRootNode().expand();
                            if (tree.getRootNode().childNodes.length) {
                                tree.getRootNode().childNodes[0].expand();
                            }
                        }
                    },
                    '-',
                    {
                        ref: 'expandnode',
                        text: _t('Expand Node'),
                        handler: function (item, e) {
                            var node = item.parentMenu.contextNode;
                            if (node) {
                                node.expand(true, true);
                            }
                        }
                    },
                    {
                        ref: 'newwindow',
                        text: _t('Open in New Window'),
                        handler: function (item, e) {
                            var node = item.parentMenu.contextNode,
                                tree, path,
                                href = window.location.protocol + '//' + window.location.host + window.location.pathname;
                            if (node && node.data.uid) {
                                tree = item.parentMenu.tree;
                                path = tree.createDeepLinkPath(node);
                                window.open(href + '#' + path);
                            }
                        }
                    }
                ]
            });
        }
        var c = tree.contextMenu;
        c.tree = tree;
        c.contextNode = node;
        e.preventDefault();
        c.showAt(e.getXY());
    };

    /**
     * @class Zenoss.HierarchyTreePanel
     * @extends Ext.tree.Panel
     * Base classe for most of the trees that appear on the left hand side
     * of various pages
     **/
    Ext.define('Zenoss.HierarchyTreePanel', {
        extend: 'Ext.tree.Panel',
        alias: ['widget.HierarchyTreePanel'],
        constructor: function (config) {
            Ext.applyIf(config, {
                enableDragDrop: true,
                loadMask: true
            });
            config.listeners = config.listeners || {};
            Ext.applyIf(config.listeners, {
                itemcontextmenu: Zenoss.treeContextMenu,
                scope: this
            });

            config.viewConfig = config.viewConfig || {};
            if (config.enableDragDrop) {
                var dd_permission = Zenoss.Security.hasPermission('Change Device');
                if (config.forceEnableDd) {
                    dd_permission = true;
                }
                Ext.applyIf(config.viewConfig, {
                    loadMask: config.loadMask,
                    plugins: {
                        ptype: 'treeviewdragdrop',
                        enableDrag: dd_permission,
                        enableDrop: dd_permission,
                        ddGroup: config.ddGroup
                    }
                });
            } else {
                Ext.applyIf(config.viewConfig, {
                    loadMask: config.loadMask
                });
            }
            Ext.applyIf(config, {
                ui: 'hierarchy',
                frame: false,
                useArrows: true,
                autoScroll: true,
                manageHeight: false,
                relationshipIdentifier: null,
                containerScroll: true,
                selectRootOnLoad: true,
                rootVisible: false,
                rootDepth: config.rootVisible ? 0 : 1,
                allowOrganizerMove: true,
                pathSeparator: "/",
                nodeIdSeparator: ".",
                hideHeaders: true,
                columns: [
                    {
                        xtype: 'treecolumn',
                        flex: 1,
                        dataIndex: 'text',
                        renderer: function (value, l, n) {
                            if (Ext.isString(value)) {
                                return value;
                            }
                            var parentNode = n.parentNode,
                                safeText = Ext.String.htmlEncode(value.text),
                                safeDescription = Ext.String.htmlEncode(value.description),
                                count;

                            if (Ext.isEmpty(value.count)) {
                                count = "";
                            } else {
                                count = Ext.String.format(" <span title='{0}'>({1})</span>", safeDescription, value.count);
                            }
                            if (parentNode.data.root === true) {
                                return Ext.String.format("<span class='rootNode'>{0}{1}</span>", safeText, count);
                            } else {
                                return Ext.String.format("<span class='subNode'>{0}</span>{1}", safeText, count);
                            }

                        }
                    }
                ]

            });
            if (config.router) {
                Ext.applyIf(config, {
                    addNodeFn: config.router.addNode,
                    deleteNodeFn: config.router.deleteNode
                });
            }
            else {
                Ext.applyIf(config, {
                    addNodeFn: Ext.emptyFn,
                    deleteNodeFn: Ext.emptyFn
                });
            }
            var root = config.root || {};
            if (config.directFn && !config.loader) {
                var modelId = Ext.String.format('Zenoss.tree.{0}Model', config.id);

                Ext.define(modelId, {
                    extend: 'Ext.data.Model',
                    treeId: config.id,
                    idProperty: config.idProperty || 'id',
                    getOwnerTree: function () {
                        return Ext.getCmp(this.treeId);
                    },
                    /**
                     * Used by the tree store to determine what
                     * to send to the server
                     **/
                    getId: function () {
                        return this.get("uid");
                    },
                    proxy: {
                        simpleSortMode: true,
                        type: 'direct',
                        directFn: config.directFn,
                        paramOrder: ['uid']
                    },
                    fields: Zenoss.model.BASE_TREE_FIELDS.concat(config.extraFields || [])
                });
                config.store = new Ext.create('Ext.data.TreeStore', {
                    clearOnLoad: false,
                    model: modelId,
                    nodeParam: 'uid',
                    defaultRootId: root.uid,
                    remoteSort: false,
                    sorters: {
                        sorterFn: config.sortFn || Zenoss.sortTreeNodes,
                        direction: 'asc'
                    },
                    uiProviders: {
                        // 'hierarchy': Zenoss.HierarchyTreeNodeUI
                    }
                });
                Ext.destroyMembers(config, 'directFn', 'ddGroup');
            }
            Ext.applyIf(root, {
                id: root.id,
                uid: root.uid,
                text: _t(root.text || root.id)
            });
            this.root = root;
            this.stateHash = {};
            if (config.stateful) {
                this.stateEvents = this.stateEvents || [];
                this.stateEvents.push('expandnode', 'collapsenode');
            }

            Zenoss.HierarchyTreePanel.superclass.constructor.apply(this, arguments);
        },
        setNodeVisible: function (nodeId, visible) {
            var node = this.getStore().getNodeById(nodeId),
                view = this.getView(),
                el = Ext.fly(view.getNodeByRecord(node));
            if (el) {
                el.setVisibilityMode(Ext.Element.DISPLAY);
                el.setVisible(visible);
            }
        },
        getState: function () {
            return { stateHash: this.stateHash };
        },
        applyState: function (state) {
            if (state) {
                Ext.apply(this, state);
                this.setStateListener();
            }
        },
        setStateListener: function () {
            this.store.on({
                load: {
                    scope: this, fn: function () {
                        for (var p in this.stateHash) {
                            if (this.stateHash.hasOwnProperty(p)) {
                                this.expandPath(this.stateHash[p]);
                            }
                        }
                    }
                }
            });
        },
        initEvents: function () {
            var me = this;
            Zenoss.HierarchyTreePanel.superclass.initEvents.call(this);

            if (this.selectRootOnLoad && !Ext.History.getToken()) {
                this.getRootNode().on('expand', function () {
                    // The first child is our real root
                    if (this.getRootNode().firstChild) {
                        me.addHistoryToken(me.getView(), this.getRootNode().firstChild);
                        me.getRootNode().firstChild.expand();
                        me.getSelectionModel().select(this.getRootNode().firstChild);
                    }
                }, this, { single: true });
            } else {

                // always expand the first shown root if we can
                this.getRootNode().on('expand', function () {
                    if (this.getRootNode().firstChild) {
                        this.getRootNode().firstChild.expand();
                    }
                }, this, { single: true });
            }
            this.addEvents('filter');
            this.on('itemclick', this.addHistoryToken, this);
            this.on({
                beforeexpandnode: function (node) {
                    this.stateHash[node.id] = node.getPath();
                },
                beforecollapsenode: function (node) {
                    delete this.stateHash[node.id];
                    var tPath = node.getPath();
                    for (var t in this.stateHash) {
                        if (this.stateHash.hasOwnProperty(t)) {
                            if (-1 !== this.stateHash[t].indexOf(tPath)) {
                                delete this.stateHash[t];
                            }
                        }
                    }
                }
            });    // add some listeners for state
        },
        addHistoryToken: function (view, node) {
            Ext.History.add(this.id + Ext.History.DELIMITER + node.get('id'));
        },
        update: function (data) {
            function doUpdate(root, data) {
                Ext.each(data, function (datum) {
                    var node = root.findChild('id', datum.id);
                    if (node) {
                        node.data = datum;
                        node.setText(node.data.text);
                        doUpdate(node, datum.children);
                    }
                });
            }

            doUpdate(this.getRootNode(), data);

        },
        selectByToken: function (nodeId) {
            nodeId = unescape(nodeId);
            var root = this.getRootNode(),
                selNode = Ext.bind(function () {
                    var sel = this.getSelectionModel().getSelectedNode();

                    if (!(sel && nodeId === sel.id)) {
                        var path = this.getNodePathById(nodeId);
                        this.selectNodeByPath(path);
                    }
                }, this);

            if (!root.isLoaded()) {
                // Listen on expand because if we listen on the store's load expand
                // gets double-called.
                root.on('expand', selNode, this, { single: true });
            } else {
                selNode();
            }
        },
        /**
         * Expand the tree along the given path.
         *
         * This is a copy of the the expandNode function from ExtJS with
         * modifications to detect and skip path segments that do not
         * exist in the tree.
         *
         * @param {String} path The path to expand. The path should include a leading separator.
         * @param {String} [field] The field to get the data from. Defaults to the model idProperty.
         * @param {String} [separator='/'] A separator to use.
         * @param {Function} [callback] A function to execute when the expand finishes. The callback will be called with
         * (success, lastNode) where success is if the expand was successful and lastNode is the last node that was expanded.
         * @param {Object} [scope] The scope of the callback function
         */
        expandNodeByPath: function (path, field, separator, callback, scope) {
            var me = this,
                current = me.getRootNode(),
                index = 1,
                keys,
                expander;

            field = field || me.getRootNode().idProperty;
            separator = separator || '/';

            if (Ext.isEmpty(path)) {
                Ext.callback(callback, scope || me, [false, null]);
                return;
            }

            keys = path.split(separator);
            if (current.get(field) !== keys[1]) {
                Ext.callback(callback, scope || me, [false, current]);
                return;
            }

            expander = function () {
                if (++index === keys.length) {
                    Ext.callback(callback, scope || me, [true, current]);
                    return;
                }
                if (keys[index] === undefined) {
                    return;
                }
                var node = current.findChild(field, keys[index]);
                if (node) {
                    current = node;
                }
                current.expand(false, expander);
            };
            current.expand(false, expander);
        },
        /**
         * Expand the tree to the path of a particular node, then select it.
         *
         * This is a copy of the selectNode function from ExtJS with the
         * modification to call the expandNodeByPath function defined above.
         *
         * @param {String} path The path to select. The path should include a leading separator.
         * @param {String} [field] The field to get the data from. Defaults to the model idProperty.
         * @param {String} [separator='/'] A separator to use.
         * @param {Function} [callback] A function to execute when the select finishes. The callback will be called with
         * (bSuccess, oLastNode) where bSuccess is if the select was successful and oLastNode is the last node that was expanded.
         * @param {Object} [scope] The scope of the callback function
         */
        selectNodeByPath: function (path, field, separator, callback, scope) {
            var me = this,
                root,
                keys,
                last;

            field = field || me.getRootNode().idProperty;
            separator = separator || '/';

            keys = path.split(separator);
            last = keys.pop();
            if (keys.length > 1) {
                me.expandNodeByPath(
                    keys.join(separator), field, separator,
                    function (success, node) {
                        var lastNode = node;
                        if (success && node) {
                            node = node.findChild(field, last);
                            if (node) {
                                me.getSelectionModel().select(node);
                                Ext.callback(callback, scope || me, [true, node]);
                                return;
                            }
                        }
                        Ext.callback(callback, scope || me, [false, lastNode]);
                    },
                    me);
            } else {
                root = me.getRootNode();
                if (root.getId() === last) {
                    me.getSelectionModel().select(root);
                    Ext.callback(callback, scope || me, [true, root]);
                } else {
                    Ext.callback(callback, scope || me, [false, null]);
                }
            }
        },
        /**
         * Given a nodeId this returns the full path to the node. By convention
         * nodeIds are the uid with a "." in place of a "/". So for example on the
         * infrastructure page this method would recieve ".zport.dmd.Device.Server" and
         * return "/Devices/.zport.dmd.Devices/.zport.dmd.Devices.Server"
         *
         * Override this method if your tree implements a custom path setup
         **/
        getNodePathById: function (nodeId) {
            var depth = this.root.uid.split('/').length - this.rootDepth,
                parts = nodeId.split(this.nodeIdSeparator),
                path = [],
                segment = Ext.Array.splice(parts, 0, depth + 1).join(this.nodeIdSeparator);

            // grab the first depth pieces of the id (e.g. .zport.dmd.Devices)
            path.push(this.initialConfig.root.id);
            // each segment of the path will have the previous segment as a piece of it
            path.push(segment);

            Ext.each(parts, function (piece) {
                // We need to skip the piece of the path that represents the
                // relationship between the organizer and the object:
                // e.g.: .zport.dmd.Something.SampleOrganizer.{relationshipIdentifier}.myObject
                // We do still need to add it to the segment that is reused for
                // each piece of the overall path.
                segment = segment + this.nodeIdSeparator + piece;
                if (piece !== this.relationshipIdentifier) {
                    path.push(segment);
                }
                else {
                    // stop iterating over the path once we've found the
                    // relationshipIdentifier, but make sure to push on the
                    // last 'chunk'.
                    // Trying to get something like this:
                    // foo.bar.baz.{relationshipIdentifier}.monkey =>
                    //     ["foo.bar.baz", "monkey"]
                    var idPartsWithoutRelationshipId = nodeId.split(
                        this.nodeIdSeparator + this.relationshipIdentifier + this.nodeIdSeparator);

                    if (idPartsWithoutRelationshipId.length > 1) {
                        path.push(segment + this.nodeIdSeparator + idPartsWithoutRelationshipId.pop());
                        // stop Ext.each iteration - this prevents generating
                        // segements for any further parts of the 'path' that
                        // may have been generated by splitting by the nodeIdSeparator
                        // such as in the case of mibs:
                        // .zport.dmd.Mibs.TestMib.mibs.1.2.4.5.6.6.7.2
                        return false;
                    }
                }
            }, this);
            return "/" + path.join(this.pathSeparator);
        },
        /**
         * This takes a node anywhere in the hierarchy and
         * will go back up to the parents and expand until it hits
         * the root node. This is a workaround for selectPath being nonfunctional
         * in Ext4
         *@param Ext.data.NodeInterface child
         **/
        expandToChild: function (child) {
            var parentNode = child.parentNode;

            // go back up and expand to this point
            while (parentNode) {
                // at the pseudo root nothing is further up
                if (Ext.isEmpty(parentNode.get('path'))) {
                    break;
                }

                if (!parentNode.isExpanded() && parentNode.hasChildNodes()) {
                    parentNode.expand();
                }
                parentNode = parentNode.parentNode;
            }
        },
        createDeepLinkPath: function (node) {
            var path = this.id + Ext.History.DELIMITER + node.get("uid").replace(/\//g, '.');
            return path;
        },
        afterRender: function () {
            Zenoss.HierarchyTreePanel.superclass.afterRender.call(this);
            var liveSearch = Zenoss.settings.enableLiveSearch,
                listeners = {
                    scope: this,
                    keypress: function (field, e) {
                        if (e.getKey() === e.ENTER) {
                            this.filterTree(field);
                        }
                    }
                };

            if (liveSearch) {
                listeners.change = this.filterTree;
            }
            if (this.searchField && this.ownerCt.regSearchListeners) {
                this.ownerCt.regSearchListeners(listeners);
            }
            this.getRootNode().expand(false, true, function (node) {
                node.expandChildNodes();
            });
        },
        expandAll: function () {
            // we have a hidden pseudo-root so we need to
            // expand all from the first visible root
            if (this.getRootNode().firstChild) {
                this.getRootNode().firstChild.expand(true);
            } else {
                this.callParent(arguments);
            }
        },
        filterTree: function (e) {
            if (!this.onFilterTask) {
                this.onFilterTask = new Ext.util.DelayedTask(function () {
                    this.doFilter(e);
                }, this);
            }

            this.onFilterTask.delay(1000);
        },
        postFilter: function () {
            var rootNode = this.getRootNode(),
                childNodes = rootNode.childNodes;


            // select the first leaf
            while (childNodes.length) {
                if (childNodes[0].childNodes.length) {
                    childNodes = childNodes[0].childNodes;
                } else {
                    break;
                }
            }

            this.getSelectionModel().select(childNodes[0]);

            // and then focus on back on the filter text
            this.up('HierarchyTreePanelSearch').down('searchfield').focus([false]);
        },
        getFilterFn: function (text) {
            var regex = new RegExp(Ext.String.escapeRegex(text), 'i');
            var fn = function (item) {
                // text can be either an object with the property text or a string
                var attr = item.get('text');
                if (Ext.isObject(attr)) {
                    attr = attr.text;
                }
                return regex.test(attr);
            };
            return fn;
        },
        doFilter: function (e) {
            var text = e.getValue(),
                store = this.getStore();
            store.clearFilter(true);

            this.fireEvent('filter', e);
            if (text) {
                store.filter(new Ext.util.Filter({
                    filterFn: this.getFilterFn(text)
                }));
            }
        },
        addNode: function (type, id) {
            this.addChildNode({ type: type, id: id });
        },
        addChildNode: function (params) {
            var selectedNode = this.getSelectionModel().getSelectedNode();
            var parentNode;
            if (selectedNode.leaf) {
                parentNode = selectedNode.parentNode;
            } else {
                parentNode = selectedNode;
            }
            var contextUid = parentNode.data.uid;
            Ext.applyIf(params, {
                contextUid: contextUid
            });

            this.addTreeNode(params);
        },
        addTreeNode: function (params) {
            var callback = function (provider, response) {
                var result = response.result;
                var me = this;
                if (result.success) {
                    // look for another node on result and assume it's the new node, grab it's id
                    // TODO would be best to normalize the names of result node
                    var nodeId = Zenoss.env.PARENT_CONTEXT + '/' + params.id;
                    this.getStore().load({
                        callback: function () {
                            nodeId = nodeId.replace(/\//g, '.');
                            me.selectByToken(nodeId);
                        }
                    });

                    this.refresh();
                }
                else {
                    Ext.Msg.alert('Error', result.msg);
                }
            };

            this.addNodeFn(params, Ext.bind(callback, this));
        },
        deleteSelectedNode: function () {
            var node = this.getSelectionModel().getSelectedNode();
            var me = this;
            var parentNode = node.parentNode;
            var uid = node.get('uid');
            var params = { uid: uid };

            function callback(provider, response) {
                // Only update the UI if the response indicates success
                if (Zenoss.util.isSuccessful(response)) {
                    // Select the parent node since the current one was deleted.
                    me.getSelectionModel().select(parentNode);

                    // Refresh the parent node's tree to remove our node.
                    me.getStore().load({
                        callback: function () {
                            me.selectByToken(parentNode.get('uid'));
                            me.getRootNode().firstChild.expand();
                        }
                    });
                }
            }

            // all hierarchytreepanel's have an invisible root node with depth of 0
            if (node.getDepth() <= 1) {
                Zenoss.message.error(_t('You can not delete the root node'));
                return;
            }

            this.deleteNodeFn(params, callback);
            this.refresh();
        },
        canMoveOrganizer: function (organizerUid, targetUid) {
            var orgPieces = organizerUid.split('/'),
                targetPieces = targetUid.split('/');

            // make sure we can actually move organizers
            if (!this.allowOrganizerMove) {
                return false;
            }

            // Relying on a coincidence that the third item
            // is the top level organizer (e.g. Locations, Groups)
            return orgPieces[3] === targetPieces[3];
        },
        refresh: function (callback, scope) {
            // Disable “Loading…” mask during the request
            this.view.loadMask.disabled = true;
            this.getStore().load({
                scope: this,
                callback: function (records, opts, success) {
                    if (success) {
                        var root = this.getRootNode();
                        var treeState = this.getTreeState(root);
                        var childNodes = opts.response.result[0];
                        root.removeAll();
                        root.appendChild(childNodes);
                        this.restoreTreeState(treeState);
                    }
                }
            });
        },
        getTreeState: function (root) {
            var expandedNodes = [];
            var collapsedNodes = [];
            var me = this;
            (function inorder(node) {
                var nid = node.get('id');
                var hid = me.isHidden(nid, collapsedNodes);
                if (node.data.expanded && !hid) {
                    expandedNodes.push(nid);
                } else {
                    collapsedNodes.push(nid);
                }
                if (node.childNodes) {
                    node.childNodes.forEach(function (child) {
                        inorder(child);
                    });
                }
            })(root);
            return expandedNodes;
        },
        restoreTreeState: function (treeState) {
            var me = this;
            // ex: '/Devices/.zport.dmd.Devices/.zport.dmd.Devices.AWS/.zport.dmd.Devices.AWS.EC2'
            me.getExpansionPaths(treeState).forEach(function (expansionPath) {
                me.expandNodeByPath(expansionPath);
            });
        },
        getExpansionPaths: function(treeState) {
            var me = this;
            var outPaths = [];
            var prefix = '/' + treeState[0];
            treeState.forEach(function (path) {
                // devices paths start at tree level 3
                if (me.treeLevel(path) > 3) {
                    outPaths.push(me.pathExpand(prefix, path));
                }
            });
            return outPaths;
        },
        pathExpand: function (prefix, path) {
            var delimeter = '.';
            var pathDepth = this.treeLevel(path);
            var expandedPath = prefix;
            // begin after 3rd occurrence of '.'
            var pos = path.split(delimeter, 3).join(delimeter).length + 1;
            for (var i = 3; i < pathDepth; i++) {
                var nextStop = path.indexOf(delimeter, pos);
                pos = nextStop < 0 ? path.length : nextStop;
                expandedPath += ('/' + path.substr(0, pos++));
            }
            return expandedPath;
        },
        treeLevel: function (path) {
            return path.split('.').length;
        },
        isHidden: function (path, collapsed) {
            var found = false;
            collapsed.forEach(function (coll) {
                if (path.startsWith(coll)) {
                    found = true;
                }
            });
            return found;
        }

    }); // HierarchyTreePanel

})();
