/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010-2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

var ZC = Ext.ns('Zenoss.component'),
    NM = ZC.nameMap = {};

ZC.registerName = function(meta_type, name, plural) {
    NM[meta_type] = [name, plural];
};

ZC.displayName = function(meta_type) {
    return NM[meta_type] || [meta_type, meta_type];
};

ZC.displayNames = function() {
    return NM;
};

var router = Zenoss.remote.TemplateRouter;

function render_link(ob) {
    if (ob && ob.uid) {
        return Zenoss.render.link(ob.uid);
    } else {
        return ob;
    }
}
function getComponentEventPanelColumnDefinitions() {
    var fields = ['eventState',
                  'severity',
                  'eventClass',
                  'summary',
                  'firstTime',
                  'lastTime',
                  'count'],
        cols;
    cols = Zenoss.util.filter(Zenoss.env.COLUMN_DEFINITIONS, function(col){
        return Ext.Array.indexOf(fields, col.dataIndex) !== -1;
    });

    // delete the ids to make sure we do not have duplicates,
    // they are not needed
    Ext.Array.each(cols, function(col){
        if (col.id) {
            delete col.id;
        }
    });

    return cols;
}

function tbarButtoner(target, buttonDefs, combo, cardId, that) {
    var tbar = target.getDockedItems()[0];
    if (tbar._btns) {
        Ext.each(tbar._btns, tbar.remove, tbar);
    }
    var btns = tbar.add(buttonDefs);
    tbar.doLayout();
    tbar._btns = btns;
    combo.on('select', function(c){
        if (c.value!==cardId) {
            Ext.each(btns, tbar.remove, tbar);
        }
    }, that, {single:true});
}

Ext.define('Zenoss.component.TplUidNameModel', {
    extend: 'Ext.data.Model',
    idProperty: 'uid',
    fields: ['qtip', 'definition', 'hidden', 'leaf', 'description', 'name', 'text', 'id', 'meta_type', 'targetPythonClass', 'inspector_type', 'icon_cls', 'children', 'uid']
});

// getGraphDef can fetch graph defs and automatically
// caches them
var getGraphDef = (function(){
    var graphDefsCache = {};
    return function getGraphDef(data, cb, scope){
        var name = data.uid,
            cached = graphDefsCache[name];

        // use cached result if available
        if(cached){
            // NOTE - result must be cloned because the receiver
            // can do whatever they want with the referenced object
            cb.call(scope, Ext.clone(cached.result), cached.event, cached.success);
            return;
        }

        // create a new callback that will cache the result,
        // then call the original callback
        var callback = function(result, event, success){
            if(!success){
                cb.call(scope, result, event, success);
                return;
            }

            // cache result
            graphDefsCache[name] = {
                result: result,
                event: event,
                success: success
            };
            cb.call(scope, Ext.clone(result), event, success);
        };

        Zenoss.remote.DeviceRouter.getGraphDefs(data, callback, scope);
    };
})();

Zenoss.nav.register({
    Component: [{
        nodeType: 'subselect',
        id: 'Graphs',
        text: _t('Graphs'),
        action: function(node, target, combo) {
            var uid = combo.contextUid,
                cardid = 'graph_panel',
                graphs = {
                    id: cardid,
                    xtype: 'graphpanel',
                    viewName: 'graphs',
                    text: _t('Graphs'),
                    directFn: getGraphDef
                };

            if (!Ext.get('graph_panel')) {
                target.add(graphs);
            }
            target.layout.setActiveItem(cardid);
            target.layout.activeItem.setContext(uid);
        }
    },{
        nodeType: 'subselect',
        id: 'Events',
        text: _t('Events'),
        action: function(node, target, combo) {
            var uid = combo.contextUid,
                cardid = 'event_panel',
                showPanel = function() {
                    target.layout.setActiveItem(cardid);
                    target.layout.activeItem.setContext(uid);
                };
            if (!Ext.get('event_panel')) {
                target.add({
                    id: cardid,
                    xtype: 'SimpleEventGridPanel',
                    stateId: 'component-event-console',
                    columns: getComponentEventPanelColumnDefinitions()
                });
            }
            var buttonDefs = [
                '-',
                new Zenoss.ActionButton({
                    iconCls: 'acknowledge',
                    tooltip: _t('Acknowledge events'),
                    permission: 'Manage Events',
                    handler: function() {
                        Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.acknowledge);
                    }
                }),
                new Zenoss.ActionButton({
                    iconCls: 'close',
                    tooltip: _t('Close events'),
                    permission: 'Manage Events',
                    handler: function() {
                        Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.close);
                    }
                }),
                new Zenoss.ActionButton({
                    iconCls: 'refresh',
                    permission: 'View',
                    tooltip: _t('Refresh events'),
                    handler: function(btn) {
                        var grid = btn.grid || this.ownerCt.ownerCt;
                        if(grid.getComponent("event_panel")) {
                            grid = grid.getComponent("event_panel");
                        }
                        grid.refresh();
                    }
                }),
                '-',
                new Zenoss.ActionButton({
                    iconCls: 'newwindow',
                    permission: 'View',
                    tooltip: _t('Go to event console'),
                    handler: function() {
                        var curState = Ext.state.Manager.get('evconsole') || {},
                        filters = curState.filters || {},
                        pat = /devices\/([^\/]+)(\/.*\/([^\/]+)$)?/,
                        st, url, matches = Ext.getCmp('event_panel').uid.match(pat);
                        if (matches){
                            filters.device = matches[1];
                            // using "name" from the parent grid here as the UID doesn't contain the component as was expected
                            filters.component = Ext.getCmp('component_card').componentgrid.getView().getSelectionModel().getSelected().get("name");
                        }
                        curState.filters = filters;
                        st = encodeURIComponent(Zenoss.util.base64.encode(Ext.encode(curState)));
                        url = '/zport/dmd/Events/evconsole?state=' + st;
                        window.open(url, '_newtab', "");
                    }
                })
            ];
            tbarButtoner(target, buttonDefs, combo, "Events", this);
            showPanel();
        }
    },{
        nodeType: 'subselect',
        id: 'Edit',
        text: _t('Details'),
        action: function(node, target, combo) {
            var uid = combo.contextUid,
                editPanel = Ext.getCmp('edit_panel');
            if (!editPanel) {
                // create a static container that will handle forms;
                editPanel = target.add({
                    xtype: 'container',
                    id: 'edit_panel',
                    layout: 'fit'
                });
            }
            target.layout.setActiveItem('edit_panel');
            editPanel.setLoading(true);
            Zenoss.form.getGeneratedForm(uid, function(config){
                // remove previous form and add new one;
                editPanel.removeAll(true);
                editPanel.add(Ext.apply({autoScroll: true}, config));
                editPanel.setLoading(false);
            });
        }
    },{
        nodeType: 'subselect',
        id: 'ComponentTemplate',
        text: _t('Templates'),
        action: function(node, target, combo) {
            var cardid = 'templates_panel',
                contextUid = combo.contextUid;
            if (!Ext.get(cardid)) {
                target.add(Ext.create('Zenoss.ComponentTemplatePanel',{
                    ref: 'componentTemplatePanel',
                    id: cardid,
                    contextUid: contextUid
                }));
            }
            var tplCombo = Ext.create('Ext.form.field.ComboBox', {
                xtype: 'combo',
                ref: '../templateCombo',
                displayField: 'name',
                valueField: 'uid',
                initialSortColumn: 'name',
                width: 200,
                editable: false,
                forceSelection: true,
                autoSelect: true,
                store: new Zenoss.NonPaginatedStore({
                    model: 'Zenoss.component.TplUidNameModel',
                    directFn: router.getObjTemplates,
                    autoLoad: true,
                    listeners: {
                        beforeload: function(store, operation){
                            if (!operation.params) {
                                operation.params = {};
                                operation.params.uid = contextUid;
                            } else {
                                operation.params.uid = contextUid;
                                delete operation.params.query;
                            }
                        },
                        load: function(store, records) {
                            if (records.length === 0) {
                                return;
                            }
                            if (!target.componentTemplatePanel) {
                                return;
                            }
                            var tplUid = records[0].data.uid;
                            target.componentTemplatePanel.setContext(tplUid);
                            if (tplCombo.store) {
                                tplCombo.setValue(tplUid);
                            }
                            if (tplCombo.refOwner) {
                                if (tplUid.startswith(contextUid)) {
                                    tplCombo.refOwner.createLocalCopyButton.disable();
                                    tplCombo.refOwner.deleteLocalCopyButton.enable();
                                } else {
                                    tplCombo.refOwner.createLocalCopyButton.enable();
                                    tplCombo.refOwner.deleteLocalCopyButton.disable();
                                }
                            }
                        }
                    }
                }),
                listeners: {
                    select: function(combo, records){
                        var tplUid = records[0].data.uid;
                        target.componentTemplatePanel.setContext(tplUid);
                        if (tplUid.startswith(contextUid)) {
                            this.refOwner.createLocalCopyButton.disable();
                            this.refOwner.deleteLocalCopyButton.enable();
                        } else {
                            this.refOwner.createLocalCopyButton.enable();
                            this.refOwner.deleteLocalCopyButton.disable();
                        }
                    }
                }
            });
            var buttonDefs = [
                '->',
                {
                    xtype: 'label',
                    text: _t('Template:'),
                    margin: '0 10 0 0'
                },
                tplCombo,
                '-',
                {
                    ref: '../createLocalCopyButton',
                    xtype: 'button',
                    disabled: true,
                    text: _t('Create Local Copy'),
                    handler: function() {
                        var tplTbar = this.refOwner,
                            templateName = tplTbar.templateCombo.getValue(),
                            createLocalArgs;
                        if (templateName) {
                            createLocalArgs = {
                                uid: contextUid,
                                templateName: templateName
                            };
                            router.makeLocalRRDTemplate(createLocalArgs, function(response) {
                                target.componentTemplatePanel.setContext(response.tplUid);
                                tplTbar.createLocalCopyButton.disable();
                                tplTbar.deleteLocalCopyButton.enable();
                            });
                        }
                    }
                },{
                    ref: '../deleteLocalCopyButton',
                    xtype: 'button',
                    text: _t('Delete Local Copy'),
                    disabled: true,
                    tooltip: _t('Delete the local copy of this template'),
                    handler: function() {
                        var tplTbar = this.refOwner,
                            templateName = tplTbar.templateCombo.getValue(),
                            removeLocalArgs;
                        if (templateName) {
                            // show a confirmation
                            new Zenoss.dialog.SimpleMessageDialog({
                                title: _t('Delete Copy'),
                                message: Ext.String.format(_t("Are you sure you want to delete the local copy of this template? There is no undo.")),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        removeLocalArgs = {
                                            uid: contextUid,
                                            templateName: templateName
                                        };
                                        router.removeLocalRRDTemplate(removeLocalArgs, function(response) {
                                            target.componentTemplatePanel.setContext(response.tplUid);
                                            tplTbar.createLocalCopyButton.enable();
                                            tplTbar.deleteLocalCopyButton.disable();
                                        });
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
                        }
                    }
                }
            ];
            tbarButtoner(target, buttonDefs, combo, "Templates", this);
            target.layout.setActiveItem('templates_panel');
        }
    }]
});

Ext.define("Zenoss.component.ComponentDetailNav", {
    alias:['widget.componentnav'],
    extend:"Zenoss.DetailNavPanel",
    constructor: function(config) {
        Ext.applyIf(config, {
            autoHeight: true,
            autoScroll: true,
            containerScroll: true,
            menuIds: []
        });
        ZC.ComponentDetailNav.superclass.constructor.call(this, config);
        this.relayEvents(this.getSelectionModel(), ['selectionchange']);
        this.on('selectionchange', this.onSelectionChange);
    },
    onGetNavConfig: function() {
        var grid = this.ownerCt.ownerCt.ownerCt.componentgrid,
            items = [],
            monitor = false;
        Zenoss.env.GRID = grid;
        Ext.each(grid.store.data.items, function(record){
            if (record.data.monitor) { monitor = true; }
        });
        Zenoss.util.each(Zenoss.nav.get('Component'), function(item){
            if (!(item.id==='Graphs' && !monitor)) {
                items.push(item);
            }
        });
        return items;
    },
    filterNav: function(navpanel, config){
        //nav items to be excluded
        var excluded = [
            'status',
            'events',
            'resetcommunity',
            'pushconfig',
            'objtemplates',
            'modeldevice',
            'historyevents'
        ];
        return (Ext.Array.indexOf(excluded, config.id)===-1);
    },
    onSelectionChange: function(sm, node) {
        var target = this.target || Ext.getCmp('component_detail_panel'),
            action = node.data.action || Ext.bind(function(node, target) {
                var id = node.get('id');
                if (!(id in target.items.map)) {
                    var config = this.panelConfigMap[id];
                    if(config) {
                        target.add(config);
                        target.doLayout();
                    }
                }
                target.items.map[id].setContext(this.contextId);
                target.layout.setActiveItem(id);
            }, this);
        action(node, target);
    }
});


/**
 *@class Zenoss.component.ComponentPanel
 *@extends Ext.Panel
 **/
Ext.define("Zenoss.component.ComponentPanel", {
    alias:['widget.componentpanel'],
    extend:"Ext.Panel",
    constructor: function(config) {
        var tbar = config.gridtbar,
            tbarid = Ext.id();
        if (tbar) {
            if (Ext.isArray(tbar)) {
                tbar = {items:tbar};
            }
            Ext.apply(tbar, {
                id: tbarid
            });
        }
        config = Ext.applyIf(config||{}, {
            tbarid: tbarid,
            layout: 'border',
            token: null,
            items: [{
                region: 'north',
                height: 250,
                split: true,
                ref: 'gridcontainer',
                tbar: tbar,
                layout: 'fit'
            },{
                xtype: 'contextcardpanel',
                region: 'center',
                ref: 'detailcontainer',
                split: true,
                tbar: {
                    cls: 'largetoolbar componenttbar',
                    height: 32,
                    items: [{
                        xtype: 'tbtext',
                        text: _t("Display: ")
                    },{
                        xtype: 'detailnavcombo',
                        menuIds: [],
                        onGetNavConfig: Ext.bind(function(uid) {
                            var grid = this.componentgrid,
                                items = [],
                                monitor = false;
                            Ext.each(grid.store.data.items, function(record){
                                if (record.data.uid===uid && record.data.monitor) {
                                    monitor = true;
                                }
                            });
                            Zenoss.util.each(Zenoss.nav.get('Component'), function(item){
                                items.push(item);
                            });
                            return items;
                        }, this),
                        filterNav: function(cfg) {
                            var excluded = [
                                'status',
                                'events',
                                'resetcommunity',
                                'pushconfig',
                                'objtemplates',
                                'template',
                                'modeldevice',
                                'historyevents'
                            ];
                            return (Ext.Array.indexOf(excluded, cfg.id)===-1);
                        },
                        ref: '../../componentnavcombo',
                        getTarget: Ext.bind(function() {
                            return this.detailcontainer;
                        }, this)
                    }]
                }
            }]
        });
        ZC.ComponentPanel.superclass.constructor.call(this, config);
        this.addEvents('contextchange');
    },
    getGridToolbar: function(){
        return Ext.getCmp(this.tbarid);
    },
    selectByToken: function(token) {
        if (token) {
            if (this.componentgrid) {
                var grid = this.componentgrid;
                grid.selectByToken(token);
            } else {
                this.token = token;
            }
        }
    },
    setContext: function(uid, type) {
        this.contextUid = uid;
        if (type!==this.componentType) {
            this.componentType = type;

            var compType = this.componentType + 'Panel',
                xtype = Ext.ClassManager.getByAlias('widget.' + compType) ? compType : 'ComponentGridPanel';
            this.gridcontainer.removeAll();
            this.gridcontainer.add({
                xtype: xtype,
                componentType: this.componentType,
                ref: '../componentgrid',
                listeners: {
                    render: function(grid) {
                        grid.setContext(uid);
                    },
                    rangeselect: function() {
                        this.detailcontainer.removeAll();
                        this.componentnavcombo.reset();
                    },
                    select: function(sm, row) {
                        // top grid selection change
                        if (row) {
                            // When infinite grids are resized the "selectionchange" event can be fired
                            // even though the selected row hasn't changed.. This can be very expensive and cause rendering
                            // errors when the layout manager tries to render the layouts of things that have already
                            // been removed.
                            if (this.previousRow && this.previousRow.id === row.id) {
                                return;
                            }
                            this.previousRow = row;
                            Zenoss.env.compUUID = row.data.uuid;
                            this.componentnavcombo.setContext(row.data.uid);
                            var delimiter = Ext.History.DELIMITER,
                                token = Ext.History.getToken().split(delimiter, 1);
                            token = token + delimiter + this.componentType + delimiter + row.data.uid;
                            // set the currenttoken so the "change" event isn't fired. Events are not able
                            // to be suspended because we don't know when the change event will be fired.
                            Ext.util.History.currentToken = token;
                            Ext.util.History.setHash(token);
                            Ext.getCmp('component_monitor_menu_item').setDisabled(!row.data.usesMonitorAttribute);
                        } else {
                            this.detailcontainer.removeAll();
                            this.componentnavcombo.reset();
                        }
                    },
                    scope: this
                }
            });
            this.gridcontainer.doLayout();
            if (this.token) {
                this.componentgrid.selectByToken(this.token);
            }
        } else {
            this.componentgrid.setContext(uid);
        }
        this.fireEvent('contextchange', this, uid, type);

    }
});

/**
 *@class Zenoss.component.ComponentGridPanel
 *@extends Zenoss.BaseGridPanel
 * Base class for all of the component grids including the custom
 * grids extended by zenpacks.
 **/
Ext.define("Zenoss.component.ComponentGridPanel", {
    alias:['widget.ComponentGridPanel'],
    extend:"Zenoss.BaseGridPanel",
    lastHash: null,
    constructor: function(config) {
        config = config || {};
        config.fields = config.fields || [
            {name: 'severity'},
            {name: 'name'},
            {name: 'monitored'},
            {name: 'locking'}
        ];
        config.fields.push({name: 'uuid'});
        config.fields.push({name: 'uid'});
        config.fields.push({name: 'meta_type'});
        config.fields.push({name: 'monitor'});

        // compat for autoExpandColumn
        var expandColumn = config.autoExpandColumn;
        if (expandColumn && config.columns) {
            Ext.each(config.columns, function(col){
                if (expandColumn === col.id) {
                    col.flex = 1;
                }
            });
        }
        // delete the id fields so there are no duplicate ids
        Ext.each(config.columns, function(col){
            delete col.id;
        });
        var modelId = Ext.id();
        Ext.define(modelId, {
            extend: 'Ext.data.Model',
            idProperty: 'uuid',
            fields: config.fields
        });
        config.sortInfo = config.sortInfo || {};

        var store = new ZC.BaseComponentStore({
            model: modelId,
            initialSortColumn: config.sortInfo.field || 'name',
            initialSortDirection: config.sortInfo.direction || 'ASC',
            directFn: config.directFn || Zenoss.remote.DeviceRouter.getComponents,
            buffered: Zenoss.settings.enableInfiniteGridForComponents
        });

        config = Ext.applyIf(config, {
            autoExpandColumn: 'name',
            store: store,
            columns: [{
                id: 'component_severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 50
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                flex: 1
            }, {
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 65,
                sortable: true
            }, {
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons,
                width: 65
            }],
            selModel: new Ext.selection.RowModel({
                mode: 'MULTI',
                getSelected: function() {
                    var rows = this.getSelection();
                    if (!rows.length) {
                        return null;
                    }
                    return rows[0];
                }
            })
        });
        ZC.ComponentGridPanel.superclass.constructor.call(this, config);
        this.relayEvents(this.getSelectionModel(), ['rangeselect']);
        this.store.proxy.on('load',
            function(proxy, o) {
                this.lastHash = o.result.hash || this.lastHash;
            },
            this);
    },
    applyOptions: function(){
        // apply options to all future parameters, not just this operation.
        var params = this.getStore().getProxy().extraParams;

        Ext.apply(params, {
            uid: this.contextUid,
            keys: Ext.Array.pluck(this.fields, 'name'),
            meta_type: this.componentType,
            name: this.componentName
        });
    },
    filter: function(name) {
        this.componentName = name;
        this.refresh();
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.getStore().on('guaranteedrange', function(){
            var token = Ext.History.getToken();
            if (token.split(Ext.History.DELIMITER).length!==3) {
                this.getSelectionModel().selectRange(0, 0);
            }
        }, this, {single:true});
        this.callParent(arguments);
    },
    selectByToken: function(uid) {
        var store = this.getStore(),
            selectionModel = this.getSelectionModel(),
            view = this.getView(),
            me = this,
            selectToken = function() {
                function gridSelect() {
                    var found = false, i=0;
                    store.each(function(r){
                        if (r.get('uid') === uid) {
                            if (!selectionModel.isSelected(r)) {
                                selectionModel.select(r);
                            }
                            view.focusRow(r.index);
                            found = true;
                            store.un('guaranteedrange', gridSelect, me);
                            return false;
                        }
                        i++;
                        return true;
                    });
                    return found;
                }

                // see if it is in the current buffer
                var found = gridSelect();
                if (!found) {

                    // find the index, scroll to that position
                    // and then select the component
                    var o = {componentUid:uid};
                    Ext.apply(o, store.getProxy().extraParams);
                    // make sure we have the sort and the direction.
                    // since this only happens on initia
                    Ext.applyIf(o, {
                        sort: me.getStore().sorters.first().property,
                        dir: me.getStore().sorters.first().direction
                    });
                    Zenoss.remote.DeviceRouter.findComponentIndex(o, function(r){
                        // will return a null if not found
                        if (Ext.isNumeric(r.index)) {
                            if (store.buffered){
                                // infinite grids fire guaranteedrange event
                                store.on('guaranteedrange', gridSelect, me);
                                var scroller = me.verticalScroller;
                                me.getView().scrollBy({ x: 0, y: scroller.rowHeight * r.index }, true);
                            } else {
                                // paginated grids fire load event
                                store.loadPage(store.getPageFromRecordIndex(r.index));
                                store.on('load', gridSelect, me);
                            }
                        } else {
                            // We can't find the index, it might be an invalid UID so
                            // select the first item so the details section isn't blank.
                            if (!selectionModel.getSelection()) {
                                selectionModel.select(0);
                            }

                        }
                    });
                }
        };

        if (!store.loaded) {
            store.on('guaranteedrange', selectToken, this, {single: true});
        } else {
            selectToken();
        }

    }
});



Ext.define("Zenoss.component.BaseComponentStore", {
    extend:"Zenoss.DirectStore",
    constructor: function(config) {
        var bufferSize = Zenoss.settings.componentGridBufferSize;
        // work around a bug in ExtJs 4.1.3. TODO: remove this after
        // we update the library.
        if (config.buffered) {
            if (bufferSize < 100) {
                bufferSize = 100;
            }
        }
        Ext.applyIf(config, {
            pageSize: bufferSize,
            directFn: config.directFn
        });
        ZC.BaseComponentStore.superclass.constructor.call(this, config);
        this.on('guaranteedrange', function(){
            this.loaded = true;
        }, this);
        // paginated grid fires load instead of guaranteedrange
        this.on('load', function(){
            if(!this.loaded){
                this.fireEvent('guaranteedrange', this);
            }
        }, this);
    }
});


Ext.define("Zenoss.component.IpInterfacePanel", {
    alias:['widget.IpInterfacePanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpInterface',
            autoExpandColumn: 'description',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'description'},
                {name: 'ipAddressObjs'},
                {name: 'network'},//, mapping:'network.uid'},
                {name: 'macaddress'},
                {name: 'usesMonitorAttribute'},
                {name: 'operStatus'},
                {name: 'adminStatus'},
                {name: 'status'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'duplex'},
                {name: 'netmask'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 50
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('IP Interface'),
                width: 250
            },{
                id: 'ipAddresses',
                dataIndex: 'ipAddressObjs',
                header: _t('IP Addresses'),
                renderer: function(ipaddresses) {
                    var returnString = '';
                    Ext.each(ipaddresses, function(ipaddress, index) {
                        if (index > 0) {
                            returnString += ', ';
                        }
                        if (ipaddress && Ext.isObject(ipaddress) && ipaddress.netmask) {
                            var name = ipaddress.name + '/' + ipaddress.netmask;
                            returnString += Zenoss.render.link(ipaddress.uid, undefined, name);
                        }
                        else if (Ext.isString(ipaddress)) {
                            returnString += ipaddress;
                        }
                    });
                    return returnString;
                }
            },{
                id: 'description',
                dataIndex: 'description',
                header: _t('Description')
            },{
                id: 'macaddress',
                dataIndex: 'macaddress',
                header: _t('MAC Address'),
                width: 120
            },{
                id: 'status',
                dataIndex: 'status',
                header: _t('Monitored'),
                renderer: Zenoss.render.pingStatus,
                width: 80
            },{
                id: 'operStatus',
                dataIndex: 'operStatus',
                header: _t('Operational Status'),
                width: 110
            },{
                id: 'adminStatus',
                dataIndex: 'adminStatus',
                header: _t('Admin Status'),
                width: 80
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                width: 72,
                renderer: Zenoss.render.locking_icons
            }]

        });
        ZC.IpInterfacePanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('IpInterface', _t('Interface'), _t('Interfaces'));

Ext.define("Zenoss.component.WinServicePanel", {
    alias:['widget.WinServicePanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'WinService',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'status'},
                {name: 'name'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'caption'},
                {name: 'startMode'},
                {name: 'startName'},
                {name: 'serviceClassUid'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                flex: 1,
                header: _t('Service Name'),
                renderer: Zenoss.render.WinServiceClass
            },{
                id: 'caption',
                dataIndex: 'caption',
                header: _t('Caption')
            },{
                id: 'startMode',
                dataIndex: 'startMode',
                header: _t('Start Mode')
            },{
                id: 'startName',
                dataIndex: 'startName',
                header: _t('Start Name')
            },{
                id: 'status',
                dataIndex: 'status',
                header: _t('Status'),
                renderer: Zenoss.render.pingStatus,
                width: 60
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.WinServicePanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('WinService', _t('Windows Service'), _t('Windows Services'));


Ext.define("Zenoss.component.IpRouteEntryPanel", {
    alias:['widget.IpRouteEntryPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpRouteEntry',
            autoExpandColumn: 'destination',
            fields: [
                {name: 'uid'},
                {name: 'destination'},
                {name: 'nextHop'},
                {name: 'id'}, // needed for nextHop link
                {name: 'device'}, // needed for nextHop link
                {name: 'interface'},
                {name: 'protocol'},
                {name: 'type'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'destination',
                dataIndex: 'destination',
                header: _t('Destination'),
                renderer: render_link
            },{
                id: 'nextHop',
                dataIndex: 'nextHop',
                header: _t('Next Hop'),
                renderer: Zenoss.render.nextHop,
                width: 250
            },{
                id: 'interface',
                dataIndex: 'interface',
                header: _t('Interface'),
                renderer: Zenoss.render.default_uid_renderer
            },{
                id: 'protocol',
                dataIndex: 'protocol',
                header: _t('Protocol')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type'),
                width: 50
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpRouteEntryPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('IpRouteEntry', _t('Network Route'), _t('Network Routes'));

Ext.define("Zenoss.component.IpServicePanel", {
    alias:['widget.IpServicePanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'IpService',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'status'},
                {name: 'severity'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'protocol'},
                {name: 'description'},
                {name: 'ipaddresses'},
                {name: 'port'},
                {name: 'serviceClassUid'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name'),
                flex: 1,
                renderer: Zenoss.render.IpServiceClass
            },{
                id: 'protocol',
                dataIndex: 'protocol',
                header: _t('Protocol')
            },{
                id: 'port',
                dataIndex: 'port',
                header: _t('Port')
            },{
                id: 'ipaddresses',
                dataIndex: 'ipaddresses',
                header: _t('IPs'),
                renderer: function(ips) {
                  return Ext.isEmpty(ips) ? '' : Ext.isArray(ips) ? ips.join(', ') : ips.toString();
                }
            },{
                id: 'description',
                dataIndex: 'description',
                header: _t('Description')
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.IpServicePanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('IpService', _t('IP Service'), _t('IP Services'));


Ext.define("Zenoss.component.OSProcessPanel", {
    alias:['widget.OSProcessPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'OSProcess',
            autoExpandColumn: 'processName',
            fields: [
                {name: 'uid'},
                {name: 'processName'},
                {name: 'status'},
                {name: 'severity'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'processClass'},
                {name: 'processClassName'},
                {name: 'alertOnRestart'},
                {name: 'failSeverity'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'processClass',
                dataIndex: 'processClass',
                header: _t('Process Class'),
                renderer: function(cls, meta, record) {
                    if (cls && cls.uid) {
                        return Zenoss.render.link(cls.uid, null, record.raw.processClassName);
                    } else {
                        return cls;
                    }
                }
            },{
                id: 'processName',
                dataIndex: 'processName',
                header: _t('Process Set')
            },{
                id: 'alertOnRestart',
                dataIndex: 'alertOnRestart',
                renderer: Zenoss.render.checkbox,
                width: 85,
                header: _t('Restart Alert?')
            },{
                id: 'failSeverity',
                dataIndex: 'failSeverity',
                renderer: Zenoss.render.severity,
                width: 70,
                header: _t('Fail Severity')
            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                width: 55,
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.OSProcessPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('OSProcess', _t('OS Process'), _t('OS Processes'));


Ext.define("Zenoss.component.FileSystemPanel", {
    alias:['widget.FileSystemPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            autoExpandColumn: 'mount',
            componentType: 'FileSystem',
            fields: [
                {name: 'uid'},
                {name: 'name'},
                {name: 'status'},
                {name: 'severity'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'},
                {name: 'locking'},
                {name: 'mount'},
                {name: 'storageDevice'},
                {name: 'totalBytes'},
                {name: 'availableBytes'},
                {name: 'usedBytes'},
                {name: 'capacityBytes'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'mount',
                dataIndex: 'mount',
                header: _t('Mount Point')
            },{
                id: 'storageDevice',
                dataIndex: 'storageDevice',
                header: _t('Storage Device')
            },{
                id: 'totalBytes',
                dataIndex: 'totalBytes',
                header: _t('Total Bytes'),
                renderer: Zenoss.render.bytesString
            },{
                id: 'usedBytes',
                dataIndex: 'usedBytes',
                header: _t('Used Bytes'),
                renderer: Zenoss.render.bytesString
            },{
                id: 'availableBytes',
                dataIndex: 'availableBytes',
                header: _t('Free Bytes'),
                renderer: function(n){
                    if (n<0) {
                        return _t('Unknown');
                    } else {
                        return Zenoss.render.bytesString(n);
                    }

                }
            },{
                id: 'capacityBytes',
                dataIndex: 'capacityBytes',
                header: _t('% Util'),
                renderer: function(n) {
                    if (n==='unknown' || n<0) {
                        return _t('Unknown');
                    } else {
                        return n + '%';
                    }
                }

            },{
                id: 'monitored',
                dataIndex: 'monitored',
                header: _t('Monitored'),
                renderer: Zenoss.render.checkbox,
                width: 60
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.FileSystemPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('FileSystem', _t('File System'), _t('File Systems'));


Ext.define("Zenoss.component.CPUPanel", {
    alias:['widget.CPUPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'CPU',
            autoExpandColumn: 'product',
            fields: [
                {name: 'uid'},
                {name: 'socket'},
                {name: 'manufacturer'},
                {name: 'product'},
                {name: 'clockspeed'},
                {name: 'extspeed'},
                {name: 'cacheSizeL1'},
                {name: 'cacheSizeL2'},
                {name: 'voltage'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'socket',
                dataIndex: 'socket',
                header: _t('Socket'),
                width: 45
            },{
                id: 'manufacturer',
                dataIndex: 'manufacturer',
                header: _t('Manufacturer'),
                renderer: render_link
            },{
                id: 'product',
                dataIndex: 'product',
                header: _t('Model'),
                renderer: render_link
            },{
                id: 'clockspeed',
                dataIndex: 'clockspeed',
                header: _t('Speed'),
                width: 70,
                renderer: function(x){ return x + ' MHz';}
            },{
                id: 'extspeed',
                dataIndex: 'extspeed',
                header: _t('Ext Speed'),
                width: 70,
                renderer: function(x){ return x + ' MHz';}
            },{
                id: 'cacheSizeL1',
                dataIndex: 'cacheSizeL1',
                header: _t('L1'),
                width: 70,
                renderer: function(x){ return x + ' KB';}
            },{
                id: 'cacheSizeL2',
                dataIndex: 'cacheSizeL2',
                header: _t('L2'),
                width: 70,
                renderer: function(x){ return x + ' KB';}
            },{
                id: 'voltage',
                dataIndex: 'voltage',
                header: _t('Voltage'),
                width: 70,
                renderer: function(x){ return x + ' mV';}
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.CPUPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('CPU', _t('Processor'), _t('Processors'));


Ext.define("Zenoss.component.ExpansionCardPanel", {
    alias:['widget.ExpansionCardPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'ExpansionCard',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'slot'},
                {name: 'name'},
                {name: 'serialNumber'},
                {name: 'manufacturer'},
                {name: 'product'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'slot',
                dataIndex: 'slot',
                header: _t('Slot'),
                width: 80
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'serialNumber',
                dataIndex: 'serialNumber',
                header: _t('Serial Number'),
                width: 110
            },{
                id: 'manufacturer',
                dataIndex: 'manufacturer',
                header: _t('Manufacturer'),
                renderer: render_link,
                width: 110
            },{
                id: 'product',
                dataIndex: 'product',
                header: _t('Model'),
                renderer: render_link,
                width: 130
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.ExpansionCardPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('ExpansionCard', _t('Card'), _t('Cards'));


Ext.define("Zenoss.component.PowerSupplyPanel", {
    alias:['widget.PowerSupplyPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'PowerSupply',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'watts'},
                {name: 'type'},
                {name: 'state'},
                {name: 'millivolts'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'watts',
                dataIndex: 'watts',
                header: _t('Watts')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'millivolts',
                dataIndex: 'millivolts',
                header: _t('Millivolts')
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.PowerSupplyPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('PowerSupply', _t('Power Supply'), _t('Power Supplies'));


Ext.define("Zenoss.component.TemperatureSensorPanel", {
    alias:['widget.TemperatureSensorPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'TemperatureSensor',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'state'},
                {name: 'temperature'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'temperature',
                dataIndex: 'temperature',
                header: _t('Temperature'),
                renderer: function(x) {
                    if (x === null) {
                        return "";
                    } else {
                        return x + " F";
                    }
                }
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.TemperatureSensorPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('TemperatureSensor', _t('Temperature Sensor'), _t('Temperature Sensors'));


Ext.define("Zenoss.component.FanPanel", {
    alias:['widget.FanPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'Fan',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'state'},
                {name: 'type'},
                {name: 'rpm'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type')
            },{
                id: 'rpm',
                dataIndex: 'rpm',
                header: _t('RPM')
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.FanPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('Fan', _t('Fan'), _t('Fans'));


Ext.define("Zenoss.component.HardDiskPanel", {
    alias:['widget.HardDiskPanel'],
    extend:"Zenoss.component.ComponentGridPanel",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            componentType: 'HardDisk',
            autoExpandColumn: 'name',
            fields: [
                {name: 'uid'},
                {name: 'severity'},
                {name: 'name'},
                {name: 'serialNumber'},
                {name: 'state'},
                {name: 'type'},
                {name: 'rpm'},
                {name: 'locking'},
                {name: 'usesMonitorAttribute'},
                {name: 'monitor'},
                {name: 'monitored'}
            ],
            columns: [{
                id: 'severity',
                dataIndex: 'severity',
                header: _t('Events'),
                renderer: Zenoss.render.severity,
                width: 60
            },{
                id: 'name',
                dataIndex: 'name',
                header: _t('Name')
            },{
                id: 'serialNumber',
                dataIndex: 'serialNumber',
                header: _t('Serial Number')
            },{
                id: 'state',
                dataIndex: 'state',
                header: _t('State')
            },{
                id: 'type',
                dataIndex: 'type',
                header: _t('Type')
            },{
                id: 'rpm',
                dataIndex: 'rpm',
                header: _t('RPM')
            },{
                id: 'locking',
                dataIndex: 'locking',
                header: _t('Locking'),
                renderer: Zenoss.render.locking_icons
            }]
        });
        ZC.HardDiskPanel.superclass.constructor.call(this, config);
    }
});


ZC.registerName('HardDisk', _t('HardDisk'), _t('HardDisks'));


})();
