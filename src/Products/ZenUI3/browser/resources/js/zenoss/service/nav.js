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
    * Common Functions
    *
    */

    zs.addClassHandler = function(newId)
    {
        var grid = Ext.getCmp('navGrid'),
            store = grid.getStore(),
            params;
        grid.filterRow.clearFilters();
        params = {
            contextUid: grid.getContext(),
            id: newId,
            posQuery: grid.getFilters()
        };
        var callback = function(p, response) {
            grid.setFilter('name', newId);
            store.on('load', function() {
                store.each(function(record){
                    if (record.get("name") === newId) {
                        grid.getSelectionModel().select(record);
                    }
                }, this);
            }, this, {single: true});
        };
        Zenoss.remote.ServiceRouter.addClass(params, callback);
    };

    zs.addOrganizerHandler = function(newId) {
        var tree = Ext.getCmp('navTree');
        tree.addNode('organizer', newId);
    };

    zs.deleteHandler = function() {
        var grid = Ext.getCmp('navGrid'),
            store = grid.getStore(), callback,
            selected = grid.getSelectionModel().getSelected();
        if (selected) {
            var params = {
                uid: selected.data.uid
            };

            callback = function(p, response){
                var result = response.result;
                if (result.success) {
                    grid.getSelectionModel().clearSelections();
                    store.on('load', function(){
                        grid.filterRow.clearFilters();
                        if(!selected.index) {
                            return false;
                        }
                           try{
                                grid.getSelectionModel().select(selected.index);
                           }catch(e){
                                /* sometimes, there is an index, but it's still out of range */
                                grid.getSelectionModel().select(0);
                           }
                        },
                        store, { single: true });
                    grid.refresh();
                } else {
                    Zenoss.message.error(result.msg);
                }
            };
            Zenoss.remote.ServiceRouter.deleteNode(params, callback);
        } else {
            Zenoss.message.error(_t('Must select an item in the list.'));
        }
    };

    zs.deleteOrganizerHandler = function() {
        var selected, params;
        selected = zs.getSelectedOrganizer();
        if ( ! selected ) {
            Zenoss.message.error(_t('No service organizer is selected.'));
            return;
        }
        params = {uid: selected.data.uid};
        function callback(){
            var tree = Ext.getCmp('navTree');
            tree.refresh();
        }
        Zenoss.remote.ServiceRouter.deleteNode(params, callback);
    };

    zs.dispatcher = function(actionName, value) {
        switch (actionName) {
            case 'addClass': zs.addClassHandler(value); break;
            case 'addOrganizer': zs.addOrganizerHandler(value); break;
            case 'delete': zs.deleteHandler(); break;
            case 'deleteOrganizer': zs.deleteOrganizerHandler(); break;
            default: break;
        }
    };

    var ContextGetter = Ext.extend(Object, {
        getUid: function() {
            var selected = Ext.getCmp('navGrid').getSelectionModel().getSelected();
            if ( ! selected ) {
                Zenoss.message.error(_t('You must select a service.'));
                return null;
            }
            return selected.data.uid;
        },
        hasTwoControls: function() {
            return true;
        },
        getOrganizerUid: function() {
            var selected = zs.getSelectedOrganizer();
            if ( ! selected ) {
                Zenoss.message.error(_t('You must select a service organizer.'));
                return null;
            }
            return selected.data.uid;
        }
    });

    /**********************************************************************
    *
    * Navigation Initializer
    *
    */

    zs.initNav = function(initialContext) {
        var store, fb, navTree, navGrid, p, stateId;

        store = Ext.create('Zenoss.Service.Nav.Store',{});
        stateId = initialContext.split("/").reverse()[0];
        navGrid = Ext.create('Zenoss.Service.Nav.GridPanel', {
            store: store,
            stateId: stateId,
            selModel: new Zenoss.ExtraHooksSelectionModel({
                singleSelect: true,
                listeners: {
                    select: zs.rowselectHandler
                }
            })
        });

        navTree = Ext.create('Zenoss.Service.Nav.ServiceTreePanel', {
            root: {
                id: initialContext.split('/').pop(),
                uid: initialContext
            }
        });

        p = new Ext.Panel({layout: {type:'vbox', align: 'stretch'}});
        p.add(navTree);
        p.add(navGrid);

        Ext.getCmp('center_panel').add(
            new Ext.Panel({
                layout: 'border',
                defaults: {'border':false},
                items: [{
                    id: 'master_panel',
                    region: 'west',
                    layout: 'fit',
                    width: 250,
                    split: true,
                    items: [p]
                },{
                    id: 'detail_panel',
                    region: 'center',
                    layout: 'border',
                    defaults: {'border':false},
                    items: [
                        Zenoss.Service.DetailForm.formConfig, {
                            xtype: 'instancecardpanel',
                            ref: 'detailCardPanel',
                            id: 'detailCardPanel',
                            region: 'south',
                            split: true,
                            height: 300,
                            collapsed: true,
                            listeners: {
                                afterrender: function(panel){
                                    panel.collapse();
                                }
                            },
                            router: Zenoss.remote.ServiceRouter,
                            instancesTitle: 'Service Instances',
                            bufferSize: 100,
                            nearLimit: 20,
                            zPropertyEditListeners: {
                                frameload: function() {
                                    var formPanel = Ext.getCmp('serviceForm');
                                    if (formPanel.contextUid) {
                                        formPanel.setContext(formPanel.contextUid);
                                    }
                                }
                            }
                    }]
                }]
            }
        ));
        Ext.getCmp('center_panel').doLayout();
        // expand the card panel so it can render the toolbar
        Ext.getCmp('detailCardPanel').expand();
        fb = Ext.getCmp('footer_bar');
        fb.on('buttonClick', zs.dispatcher);
        var footerHelperOptions = {
            contextGetter: new ContextGetter(),

            onGetAddDialogItems: function () {
                return [{
                    xtype: 'idfield',
                    name: 'id',
                    anchor: '80%',
                    fieldLabel: _t('Name'),
                    allowBlank: false
                }];
            }
        };
        Zenoss.footerHelper('Service', fb, footerHelperOptions);
    };
})();
