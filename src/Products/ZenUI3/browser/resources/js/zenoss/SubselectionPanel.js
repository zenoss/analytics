/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function () {

    Ext.define("Zenoss.HorizontalSlidePanel", {
        alias:['widget.horizontalslide'],
        extend:"Ext.Panel",
        constructor:function (config) {
            this.headerText = Ext.create('Ext.toolbar.TextItem', {
                html:(config && config.text) ? config.text : ''
            });
            config = Ext.applyIf(config || {}, {
                cls: 'subselect',
                layout: 'card',
                activeItem: 0
            });
            var items = [];
            Ext.each(config.items, function (item, index) {
                var headerText = Ext.create('Ext.toolbar.TextItem', {
                    html:(item && item.text) ? item.text : ''
                });
                var navButton = Ext.create('Ext.Button', {
                    text:(item && item.buttonText) ? item.buttonText : '',
                    // make the button belong to the owner panel
                    ref:(item.buttonRef || 'navButton'),
                    cls:index ? 'toleft' : 'toright',
                    ui:'arrowslide',
                    handler:function () {
                        this.setActiveItem(index ? 0 : 1);

                    },
                    scope:this
                }, this);
                this[item.buttonRef] = navButton;
                navButton.hide();
                items.push({
                    layout:'fit',
                    tbar:{
                        cls:'subselect-head',
                        height:37,
                        items:[headerText, '->', navButton]
                    },
                    items:[item],
                    listeners:{
                        render:function (card) {
                            card.card = card.items.items[0];
                            card.card.parentCard = card;
                            card.headerText = headerText;
                            card.navButton = navButton;
                            var setHeaderText = function (text, qtip) {
                                this.headerText.setText(text);
                                Ext.QuickTips.unregister(this.headerText);

                                if (qtip) {
                                    Ext.QuickTips.register({
                                        target:this.headerText,
                                        text:qtip
                                    });
                                }
                            };
                            var setButtonText = function (text) {
                                this.navButton.setText(text);
                            };
                            card.setHeaderText = Ext.bind(setHeaderText, card);
                            card.setButtonText = Ext.bind(setButtonText, card);
                        }
                    }
                });
            }, this);
            config.items = items;
            Zenoss.HorizontalSlidePanel.superclass.constructor.call(this, config);
        },
        initEvents:function () {
            this.addEvents('beforecardchange');
            this.addEvents('cardchange');
            Zenoss.HorizontalSlidePanel.superclass.initEvents.call(this);
        },

        // handler for "slide" animation on card change;
        // we shouldn't override card layout "setActiveItem" method to not break anything when component change active card;
        setActiveItem: function(item) {
            var activeItem = this.layout.getActiveItem(),
                newCard = this.layout.parseActiveItem(item),
                newIndex = this.items.indexOf(newCard),
                index = this.items.indexOf(activeItem);

            if (newCard != activeItem) {
                this.fireEvent('beforecardchange', this, newCard, newIndex, activeItem, index);
                activeItem.el.stopAnimation();
                activeItem.el.slideOut((newIndex > index ? 'l' : 'r'), {
                    duration: 100,
                    remove: false,
                    callback: function () {
                        var newActive = this.layout.oldSetActiveItem(item);
                        newActive.el.stopAnimation();
                        newActive.el.slideIn((newIndex > index ? 'r' : 'l'), {
                            duration: 150,
                            remove: false,
                            callback: function () {
                                this.fireEvent('cardchange', this, newActive, newIndex, activeItem, index);
                            },
                            scope: this
                        });
                    },
                    scope: this
                });
            }
        }
    });


    /**
     * A MixedCollection for nav configs.
     *
     * Each item in the config is a normal dictionary with an xtype. The xtype specified will be used for the display
     * when the item is clicked.
     *
     * Example item structure:
     *
     * {
     *     text: 'Menu label',
     *     id: 'View id',
     *     xtype: 'somextype', // optional, defaults to Panel
     *     filterNav: function(navTree) {
     *         // An optional function that is called to determine if this item should be shown
     *         // Use navTree.contextUid for the context.
     *         // return true to display the item or false to remove it
     *     }
     * }
     */
    Zenoss.NavConfig = Ext.extend(Ext.util.MixedCollection, {
        constructor:function () {
            Zenoss.NavConfig.superclass.constructor.call(this, true, function (item) {
                return item.id;
            });
        }
    });

    Zenoss.NavManager = Ext.extend(Object, {
        all:null,
        constructor:function () {
            this.all = new Zenoss.NavConfig();
            this.all.addEvents('navready');
        },
        /**
         * Register a nav item tree. See `Zenoss.NavConfig` for item structure.
         *
         * Zenoss.nav.register({
         *     DeviceGroup: [
         *         {
         *             id: 'device_grid',
         *             text: 'Devices',
         *             listeners: {
         *                 render: updateNavTextWithCount
         *             }
         *         },
         *         {
         *             id: 'events_grid',
         *             text: _t('Events')
         *         }
         *     ]
         * });
         *
         * @param navSpec
         */
        register:function (navSpec) {
            for (var type in navSpec) {
                this.add(type, navSpec[type]);
            }
        },
        /**
         * Adds a nav of `type` with its `items`. If a nav of `type` already exists, the items are appended.
         *
         * @param type Type of nav menu to add (ex: Device, DeviceGroup)
         * @param items An array of nav items. See `Zenoss.NavConfig` for item structure.
         */
        add:function (type, items) {
            if (!this.all.containsKey(type)) {
                // Create an empty nav container
                var newNav = new Zenoss.NavConfig();
                newNav.id = type;
                this.all.add(type, newNav);

                this.appendTo(type, items);

                this.all.fireEvent('navready', newNav);
            }
            else {
                this.appendTo(type, items);
            }
        },
        /**
         * Get a nav config if it exists.
         *
         * @param type
         */
        get:function (type) {
            return this.all.getByKey(type);
        },
        /**
         * Add menu nodes to the end of a nav config
         *
         * @param type Nav config type
         * @param items Array of items. See `Zenoss.NavConfig` for item structure.
         */
        appendTo:function (type, items) {
            if (this.all.containsKey(type)) {
                var nav = this.all.getByKey(type);
                nav.addAll(items);
            }
            else {
                this.onAvailable(type, function (item) {
                    item.addAll(items);
                });
            }
        },
        /**
         * Registers a callback to be called as soon as a nav tree matching navId is added.
         *
         * @param navId
         * @param callback
         */
        onAvailable:function (navId, callback, scope) {
            function onAdd(item) {
                if (item.id === navId) {
                    callback.call(scope || item, item);
                    this.all.un('navready', onAdd, scope);
                }
            }

            this.all.on('navready', onAdd, this);
        }
    });

    Zenoss.nav = new Zenoss.NavManager();

// Zenoss.SubselectionNodeUI = Ext.extend(Ext.tree.TreeNodeUI, {
//     render: function() {
//         Zenoss.SubselectionNodeUI.superclass.render.call(this);
//         Ext.removeNode(this.getIconEl());
//     }
// });

// Zenoss.SubselectionNode = Ext.extend(Ext.tree.TreeNode, {
//     constructor: function(config) {
//         Ext.applyIf(config, {
//             leaf: true,
//             uiProvider: Zenoss.SubselectionNodeUI
//         });
//         Zenoss.SubselectionNode.superclass.constructor.call(this, config);
//         this.addEvents('render');
//     },
//     render: function(bulkRender) {
//         Zenoss.SubselectionNode.superclass.render.call(this, bulkRender);
//         this.fireEvent('render', this);
//     }

// });

// Ext.tree.TreePanel.nodeTypes.subselect = Zenoss.SubselectionNode;


    Ext.define("Zenoss.SubselectionPanel", {
        alias:['widget.subselection'],
        extend:"Ext.Panel",
        constructor:function (config) {
            var id = config.id || Ext.id();
            Ext.applyIf(config, {
                id:id,
                layout:'fit',
                bodyStyle:{ 'margin-top':10 },
                items:[
                    {
                        xtype:'treepanel',
                        ref:'treepanel',
                        hideHeaders: true,
                        header: false,
                        selModel:new Zenoss.TreeSelectionModel({
                            listeners:{
                                selectionchange:function (sm, node) {
                                    if (node) {
                                        var action = node.data.action;
                                        if (action) {
                                            if (Ext.isString(this.target)) {
                                                this.target = Ext.getCmp(this.target);
                                            }
                                            action.call(node, node, this.target);
                                        }
                                    }
                                },
                                scope:this
                            }
                        }),
                        id:'subselecttreepanel' + id,
                        rootVisible:false,
                        root:{nodeType:'node'}
                    }
                ]
            });
            Zenoss.SubselectionPanel.superclass.constructor.call(this, config);
        },
        initComponent:function () {
            Zenoss.SubselectionPanel.superclass.initComponent.call(this);
            this.treepanel = Ext.getCmp('subselecttreepanel' + this.id);
        },
        setContext:function (uid) {
            var type = Zenoss.types.type(uid),
                nodes = Zenoss.nav.get(type);
            if (nodes) {
                Zenoss.util.each(nodes, function (node) {
                    Ext.applyIf(node, {
                        nodeType:'subselect'
                    });
                });
                var root = new Ext.tree.AsyncTreeNode({
                    children:nodes,
                    listeners:{
                        load:function (node) {
                            var toselect = node.firstChild;
                            if (toselect) {
                                if (toselect.rendered) {
                                    toselect.select();
                                } else {
                                    toselect.on('render', function (node) {
                                        node.select();
                                    });
                                }
                            }
                        },
                        scope:this
                    }
                });
                this.treepanel.setRootNode(root);
            }
        }
    });

    Ext.define("Zenoss.DetailNavTreeModel", {
        extend:'Ext.data.Model',
        fields:Zenoss.model.BASE_TREE_FIELDS.concat([
            {
                name:'action',
                type:'function'
            }
        ])
    });

    Ext.define("Zenoss.DetailNavTreePanel", {
        alias:['widget.detailnavtreepanel'],
        extend:"Ext.tree.Panel",
        constructor:function (config) {
            Ext.applyIf(config, {
                store:Ext.create('Ext.data.TreeStore', {
                    model:'Zenoss.DetailNavTreeModel',
                    proxy:{
                        type:'memory',
                        reader:{
                            type:'json'
                        }
                    },
                    autoLoad:false
                }),
                useArrows:true,
                manageHeight: false,
                hideHeaders:true,
                columns:[
                    {
                        xtype:'treecolumn',
                        flex:1,
                        dataIndex:'text'
                    }
                ],
                selModel:new Zenoss.BubblingSelectionModel({
                    bubbleTarget:config.bubbleTarget
                }),
                id:'subselecttreepanel' + config.idSuffix,
                ref:'subselecttreepanel',
                rootVisible:false,
                iconCls:'x-tree-noicon',
                header: false,
                root:{nodeType:'node'}
            });
            this.callParent([config]);
        },
        setNodeVisible:function (node, visible) {
            if (Ext.isString(node)) {
                node = this.getNodeById(node);
            }
            var view = this.getView(),
                el = Ext.fly(view.getNodeByRecord(node));
            if (el) {
                el.setVisibilityMode(Ext.Element.DISPLAY);
                el.setVisible(visible);
            }
        }
    });


    /**
     * Used to manage and display detail navigation tree for a contextId
     *
     * @class Zenoss.DetailNavPanel
     * @extends Zenoss.SubselectionPanel
     */
    Ext.define("Zenoss.DetailNavPanel", {
        alias:['widget.detailnav'],
        extend:"Zenoss.SubselectionPanel",
        /**
         * @cfg {function} onGetNavConfig abstract function; hook to provide more nav items
         * @param {string} uid; item to get nav items for
         */
        onGetNavConfig:function () {
            return [];
        },
        /**
         * Called when an item in detail nav is selected
         * @param {object} this, the DetailNavPanel
         * @param {object} the navigation node selected
         */
        onSelectionChange:Ext.emptyFn,
        /**
         * Filter out from being in the detail nav; used to filter out nav nodes
         * and the content panels. Return true if it should be kept, false otherwise
         * @param {DetailNavPanel}
            * @param {Object} config
         */
        filterNav:function () {
            return true;
        },
        /**
         * The object id for which the detail navigation belongs to
         */
        contextId:null,
        /**
         * Menu ids used to get non dialog menus to be used in navigation;
         * Empty or null if no nav from old menu items is desired
         */
        menuIds:['More', 'Manage', 'Edit', 'Actions', 'Add', 'TopLevel'],
        /**
         * map of nav id to panel configuration
         */
        loaded:false,
        panelConfigMap:null,
        selectFirstNode:true,
        constructor:function (config) {
            Ext.applyIf(config, {
                id:Ext.id(),
                bodyCls:'detailnav',
                layout:'fit',
                bodyStyle:{ 'margin-top':10 }
            });
            // call second applyIf so config.id is set correctly
            Ext.applyIf(config, {
                items:{
                    xtype:'detailnavtreepanel',
                    ref:'navtreepanel',
                    idSuffix:config.id,
                    bubbleTarget:config.bubbleTarget
                }
            });
            Zenoss.DetailNavPanel.superclass.constructor.call(this, config);
        },
        initEvents:function () {
            this.addEvents(
                /**
                 * @event navloaded
                 * Fires after the navigation has been loaded
                 * @param {DetailNavPanel} this The DetailNavPanel
                 * @param {AsyncTreeNode} root The root node
                 */
                'navloaded',
                /*
                 * @event nodeloaded
                 * Fires after each navigation node has been loaded
                 * @param {DetailNavPanel} this The DetailNavPanel
                 * @param {Object} The Navigation config loaded
                 */
                'nodeloaded',
                /**
                 * @event contextchange
                 * Fires after the navigation has been loaded
                 * @param {DetailNavPanel} this The DetailNavPanel
                 */
                'contextchange'
            );
            Zenoss.DetailNavPanel.superclass.initEvents.call(this);
            if (this.selectFirstNode) {
                this.on('navloaded', this.selectFirst, this);
            }
        },
        setContext:function (uid) {
            //called to load the nav tree
            this.loaded = false;
            this.contextId = uid;
            this.treepanel.setRootNode([]);
            this.getNavConfig(uid);
            this.fireEvent('contextchange', this);
        },
        getSelectionModel:function () {
            return this.treepanel.getSelectionModel();
        },
        getNavConfig:function (uid) {
            //Direct call to get nav configs from server
            var me = this;
            var myCallback = function (provider, response) {
                var detailConfigs = response.result.detailConfigs;

                var filterFn = function (val) {
                    var show = true;
                    if (Ext.isFunction(val.filterNav)) {
                        show = val.filterNav(me);
                    }

                    return show && me.filterNav(me, val);
                };

                detailConfigs = Zenoss.util.filter(detailConfigs, filterFn, me);
                var nodes = me.onGetNavConfig(me.contextId);
                if (!Ext.isDefined(nodes) || nodes === null) {
                    nodes = [];
                }

                nodes = Zenoss.util.filter(nodes, filterFn, me);

                if (detailConfigs) {
                    nodes = nodes.concat(detailConfigs);
                }

                me.panelConfigMap = [];
                Zenoss.util.each(nodes, function (val) {
                    me.panelConfigMap[val.id] = val;
                });

                me.setNavTree(nodes);
            };
            var args = {
                'uid':uid
            };
            if (this.menuIds !== null && this.menuIds.length >= 1) {
                args['menuIds'] = this.menuIds;
            }
            if (Zenoss.env.lefthandnav) {
                myCallback(null, {
                    result:Zenoss.env.lefthandnav
                });
                delete Zenoss.env.lefthandnav;
            } else {
                Zenoss.remote.DetailNavRouter.getDetailNavConfigs(args, myCallback, this);
            }

        },
        reset:function () {
            return this.treepanel.setRootNode({});
        },
        selectFirst:function (me, root) {
            var sel = me.getSelectionModel().getSelectedNode(),
                token = Ext.History.getToken(),
                firstToken = me.id + Ext.History.DELIMITER + root.firstChild.id;
            if (!sel) {
                if (!token || (token && token === firstToken)) {
                    me.getSelectionModel().select(root.firstChild);
                }
            }
        },
        /**
         * Set the nodes to display in the nav tree.
         * @param nodes Zenoss.NavConfig Nodes to set the nav to
         */
        setNavTree:function (nodes) {
            //get any configs registered by the page
            var root;
            if (nodes) {
                root = this.treepanel.getRootNode();
                Zenoss.util.each(nodes, function (node) {
                    Ext.applyIf(node, {
                        nodeType:'subselect',
                        leaf:true
                    });
                    root.appendChild(node);
                });

                // Send an alert for all nodes after all nodes have been loaded
                Zenoss.util.each(nodes, function (navConfig) {
                    this.fireEvent('nodeloaded', this, navConfig);
                }, this);

            }
            this.loaded = true;
            this.fireEvent('navloaded', this, root);

            root.expand(false, function(){
                if (this.manualAdjustHeight) {
                    //HACK: cheat to make sure that all nodes are visible
                    var view = this.treepanel.getView();
                    var height = Ext.fly(view.getNode(0)).getHeight();
                    this.setHeight((height * nodes.length) + 35);
                }
            }, this);
            // ZEN-29341 set default selected element to keep focus
            // after device tree refresh
            var selectionModel = this.treepanel.getSelectionModel();
            if (!selectionModel.getLastSelected()) {
                selectionModel.select(0);
            };
            this.doLayout();


        }
    });


    Ext.define("Zenoss.DetailNavCombo", {
        alias:['widget.detailnavcombo'],
        extend:"Ext.form.ComboBox",
        target:null,
        contextUid:null,
        lastSelItem:null,
        panelConfigMap:null,
        queryMode:'local',
        editable:false,
        forceSelection:true,
        typeAhead:false,
        triggerAction:'all',
        filterNav:function () {
            return true;
        },
        menuIds:['More', 'Manage', 'Edit', 'Actions', 'Add', 'TopLevel'],
        onSelectionChange:Ext.emptyFn,
        onGetNavConfig:function () {
            return [];
        },
        constructor:function (config) {
            Ext.applyIf(config, {
                store:new Ext.data.ArrayStore({
                    'id':0,
                    model: 'Zenoss.model.ValueText',
                    autoDestroy:true
                })
            });
            this.callParent(arguments);
        },
        getTarget:function () {
            var target = this.target;
            return Ext.isString(target) ? Ext.getCmp(target) : target;
        },
        initEvents:function () {
            Zenoss.DetailNavCombo.superclass.initEvents.call(this);
            this.on('select', this.onItemSelected, this);
        },
        onItemSelected:function (me, item) {
            var item = item[0],
                target = this.getTarget(),
                id = item.get('value'),
                config = this.panelConfigMap[id],
                action = config.action || function (node, target) {
                    if (!(id in target.items.map)) {
                        if (config) {
                            target.add(config);
                            target.doLayout();
                        }
                    }
                    target.items.map[id].setContext(this.contextUid);
                    target.layout.setActiveItem(id);
                };
            this.lastSelItem = item;
            action.call(this, item, target, this);
        },
        selectAt:function (idx) {
            var record = this.store.getAt(idx || 0);
            this.selectByItem(record);
        },
        selectByItem:function (item) {
            this.lastSelItem = item || this.store.getAt(0);
            this.select(this.lastSelItem);
            this.fireEvent('select', this, [this.lastSelItem]);
        },
        setContext:function (uid) {
            // make sure the context actually changed.
            if (uid === this.contextUid) {
                return;
            }
            this.contextUid = uid;
            var args = {uid:uid};
            if (!Ext.isEmpty(this.menuIds)) {
                args.menuIds = this.menuIds;
            }

            Zenoss.remote.DetailNavRouter.getDetailNavConfigs(args, function (r) {
                var detailConfigs = r.detailConfigs,
                    items = [],
                    nodes = [],
                    lastSelItem = this.lastSelItem,
                    hasItem = false,
                    panelMap = {};
                var filterFn = function (val) {
                    var show = true;
                    if (Ext.isFunction(val.filterNav)) {
                        show = val.filterNav(this);
                    }

                    return show && this.filterNav(val);
                };

                nodes = this.onGetNavConfig(uid);
                nodes = Zenoss.util.filter(nodes, filterFn, this);

                detailConfigs = Zenoss.util.filter(detailConfigs, filterFn, this);

                nodes = nodes.concat(detailConfigs);

                Ext.each(nodes, function (cfg) {
                    items.push([cfg.id, cfg.text]);
                    panelMap[cfg.id] = cfg;
                    // when switching component types we need to make sure
                    // that they share a common menu item
                    if (lastSelItem && cfg.id === lastSelItem.getId()) {
                        hasItem = true;
                    }
                });

                this.panelConfigMap = panelMap;
                this.store = new Ext.data.ArrayStore({
                    'id':0,
                    model: 'Zenoss.model.ValueText',
                    data:items,
                    autoDestroy:true
                });
                this.valueField = 'value';
                this.displayField = 'text';
                this.list = null;
                this.bindStore(this.store);
                this.doComponentLayout();
                // "sticky" menu selection, show same item as was shown for last context
                if (hasItem) {
                    this.selectByItem(this.lastSelItem);
                } else {
                    this.selectAt(0);
                }
            }, this);
        }
    });


    Ext.define("Zenoss.DetailContainer", {
        alias:['widget.detailcontainer'],
        extend:"Ext.Container",
        constructor:function (config) {
            Ext.applyIf(config, {
                autoScroll:true,
                listeners:{
                    selectionchange:this.onSelectionChange,
                    scope:this
                }
            });
            Ext.each(config.items, function (item) {
                item.bubbleTarget = this;
            }, this);
            this.callParent(arguments);
        },
        setContext:function (uid) {
            this.items.each(function (item) {
                item.setContext(uid);
            });
        },

        /**
         *  When used in devdetail.js, there will be two separate trees in here.
         *  So we need to handle the times that the user first selected
         *  something from one tree and then selected something from the other tree.
         *  We need to deselect the other tree nicely.
         * @param eventSelModel
         * @param node    should be the node that just got SELECTED.
         */
        onSelectionChange:function (eventSelModel, node) {
            var itemSelModel;
            // if node is empty then stuff just got deselected
            // from a tree, and there is nothing to do here when that happens
            if (node.length > 0) {
                this.items.each(function (item) {
                    itemSelModel = item.getSelectionModel();
                    if (itemSelModel === eventSelModel) {
                        item.onSelectionChange(node);
                    } else {
                        itemSelModel.deselectAll();
                    }
                });
            }
        }
    });


})();
