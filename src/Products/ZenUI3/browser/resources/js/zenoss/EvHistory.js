/* globals _managed_objects: true */
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.ns('Zenoss.ui.EvHistory');

Ext.onReady(function(){
var stateProvider = Ext.state.Manager.getProvider();
// wait until state is ready;
stateProvider.onStateReady(function() {
    Zenoss.ui.EvHistory.Exp = function(type, format){
        var grid = Ext.getCmp('events_grid'),
            state = grid.getState(),
            params = {
                type: type,
                isHistory: true,
                options: {
	                   fmt: format,
	                   datefmt: Zenoss.USER_DATE_FORMAT,
	                   timefmt: Zenoss.USER_TIME_FORMAT,
	                   tz: Zenoss.USER_TIMEZONE
               },
 		params: {
                    fields: Ext.Array.pluck(state.columns, 'id'),
                    sort: state.sort.property,
                    dir: state.sort.direction,
                    params: grid.getExportParameters()
                }
            };
        Ext.get('export_body').dom.value =
        Ext.encode(params);
        Ext.get('exportform').dom.submit();

    };

    // Get references to the panels
    var detail_panel = Ext.getCmp('detail_panel');
    var master_panel = Ext.getCmp('master_panel');

    master_panel.layout = 'border';

    // Make this instance of the detail panel use a unique state ID so
    // it doesn't interfere with the state of other instances of this panel.
    detail_panel.stateId = 'Zenoss.ui.EvHistory.detail_panel';

    // Make the detail panel collapsible
    detail_panel.animCollapse = false;
    detail_panel.collapsible = true;


    // Get the container surrounding master/detail, for adding the toolbar
    var container = Ext.getCmp('center_panel_container');

    // Add a CSS class to scope some styles that affect other parts of the UI
    container.on('render', function(){container.el.addClass('zenui3');});

    function doLastUpdated() {
        var box = Ext.getCmp('lastupdated'),
            dtext = Zenoss.date.renderWithTimeZone(new Date()/1000);
            dtext += " (" + Zenoss.USER_TIMEZONE + ")";
	box.setText(_t('Last updated at ') + dtext);
        }

        // Show filters by default on history console
        // State restoration occurs after render, so this won't persist if unwanted
        // myView.on('render', function(){myView.showFilters();});

        var createBar = function()
        {
        // Add the toolbar to the container
        var tbar = new Zenoss.LargeToolbar({
            region:'north',
            items: [{
                /*
                 * SELECT MENU
                 */
                text: _t('Select'),
                id: 'select-button',
                menu:{
                    xtype: 'menu',
                    items: [{
                        text: 'All',
                        handler: function(){
                            var grid = Ext.getCmp('events_grid'),
                            sm = grid.getSelectionModel();
                            sm.selectEventState('All');
                            sm.setSelectState("All");
                        }
                    },{
                        text: 'None',
                        handler: function(){
                            var grid = Ext.getCmp('events_grid'),
                            sm = grid.getSelectionModel();
                            sm.clearSelections();
                            sm.clearSelectState();
                        }
                    }
                    ]
                }
            },{
                text: _t('Export'),
                //iconCls: 'export',
                handler: function(){

                var dialog = Ext.create('Zenoss.dialog.Form', {
                    title: _t('Export events'),
                    minWidth: 350,
                    submitHandler: function(form) {
                        var values = form.getValues();
                        Zenoss.ui.EvHistory.Exp(values['ftype'], values['ffmt']);
                    },
                    form: {
                        layout: 'anchor',
                        defaults: {
                            xtype: 'displayfield',
                            padding: '0 0 10 0',
                            margin: 0,
                            anchor: '100%'
                        },
                        fieldDefaults: {
                            labelAlign: 'left',
                            labelWidth: 75,
                            labelStyle: 'color:#aaccaa'
                        },
                        items: [{
                            name: 'ftype',
                            fieldLabel: 'File type',
                            value: '',
                            xtype: 'combo',
                            allowBlank: false,
                            displayField:'name',
                            valueField:'id',
                            store: Ext.create('Ext.data.Store',{
                                  fields:['id','name'],
                                  data:[
                                        {id:'xml', name:'XML'},
                                        {id:'csv', name:'CSV'}
                                  ]
                            }),
                            editable: false,
                            disableKeyFilter: false,
                            submitValue: true
                        },{
                            name: 'ffmt',
                            fieldLabel: 'Date/Time format',
                            xtype: 'combo',
                            allowBlank: false,
                            displayField:'name',
                            valueField:'id',
                            store: Ext.create('Ext.data.Store',{
                                       fields:['id','name'],
                                       data:[
                                            {id:'iso',  name:'ISO'},
                                            {id:'unix', name:'Unix'},
                                            {id:'user', name:'User settings'}
                                       ]
                            }),
                            listeners: {'select': function (combo, record){
                                if(record[0].data.id == "unix"){
                                    Ext.getCmp('fexample').setValue(moment.tz(new Date(), Zenoss.USER_TIMEZONE).format("x")).show();
                                } else if(record[0].data.id == "iso"){
                                    Ext.getCmp('fexample').setValue(moment.tz(new Date(), Zenoss.USER_TIMEZONE).format("YYYY-MM-DDTHH:mm:ssZ")).show();
                                } else if(record[0].data.id == "user"){
                                    Ext.getCmp('fexample').setValue(moment.tz(new Date(), Zenoss.USER_TIMEZONE).format(Zenoss.USER_DATE_FORMAT + ' ' + Zenoss.USER_TIME_FORMAT)).show();
                                }
                            }
                        },
                        editable: false,
                        disableKeyFilter: false,
                        submitValue: true
                    },{
                        name: 'example',
                        id: 'fexample',
                        fieldLabel:'Format example',
                        value: '',
                        hidden: true,
                        submitValue: false
                    }
                   ]
                }
            });
            dialog.down('form');
            dialog.show();
            }
            },{
                /*
                 * CONFIGURE MENU
                 */
                text: _t('Configure'),
                id: 'configure-button',
                //iconCls: 'customize',
                menu: {
                    items: [{
                        id: 'rowcolors_checkitem',
                        xtype: 'menucheckitem',
                        text: 'Show severity row colors',
                        handler: function(checkitem) {
                            var checked = checkitem.checked;
                            var grid = Ext.getCmp('events_grid');
                            grid.toggleRowColors(checked);
                        }
                    },{
                        id: 'clearfilters',
                        text: 'Clear filters',
                        listeners: {
                            click: function(){
                                grid.clearFilters();
                            }
                        }
                    },/*{
                        id: 'showfilters',
                        text: 'Show filters',
                        checked: false,
                        listeners: {
                            'checkchange' : function(ob, on) {
                                if(on) grid.showFilters()
                                else grid.hideFilters()
                            }
                        }
                    },*/{
                        text: 'Save this configuration...',
                        handler: function(){
                            var grid = Ext.getCmp('events_grid'),
                                link = grid.getPermalink();
                        new Zenoss.dialog.ErrorDialog({
                            message: Ext.String.format(_t('<div class="dialog-link">' +
                                 'Drag this link to your bookmark bar ' +
                                 '<br/>to return to this configuration later.' +
                                 '<br/><br/><a href="' +
                                 link +
                                 '">Resource Manager: Event Archive</a></div>')),
                            title: _t('Save Configuration')
                            });
                        }
                    },{
                        id: 'adjust_columns_item_selector',
                        text: _t('Adjust columns'),
                        listeners: {
                            click: function(){
                                var grid = Ext.getCmp('events_grid');
                                Zenoss.events.showColumnConfigDialog(grid);
                            }
                        }
                    },{
                        text: "Restore defaults",
                        handler: function(){
                            new Zenoss.dialog.SimpleMessageDialog({
                                message: Ext.String.format(_t('Are you sure you want to restore ' +
                                     'the default configuration? All' +
                                     ' filters, column sizing, and column order ' +
                                     'will be lost.')),
                                title: _t('Confirm Restore'),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        Ext.getCmp('events_grid').resetGrid();
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
                        }
                    }]
                }
            },'-',{
                xtype: 'tbfill'
            },{
                id: 'lastupdated',
                xtype: 'tbtext',
                cls: 'lastupdated',
                text: 'Updating...'
            },{
                xtype: 'button',
                id: 'refresh-button',
                text: _t('Refresh'),
                handler: function() {
                    // Indicating grid updating progress
                    var box = Ext.getCmp('lastupdated');
                    box.setText(_t('<span>Updating... </span><img src="/++resource++zenui/img/ext4/icon/circle_arrows_ani.gif" width=12 height=12>'));
                    var grid = Ext.getCmp('events_grid');
                    grid.refresh();
                }
            }
            ]
        });
        return tbar;
    };

    // Selection model
    var console_selection_model = new Zenoss.EventPanelSelectionModel({
    });

    var createEventHistoryGrid = function ()
    {
        var master_panel = Ext.getCmp('master_panel');
        var tbar = createBar();

        var archive_store = Ext.create('Zenoss.events.Store', {directFn: Zenoss.remote.EventsRouter.queryArchive} );
        if (!Zenoss.settings.enableInfiniteGridForEvents) {
            archive_store.buffered = false;
        }
        var grid = Ext.create('Zenoss.events.Grid', {
            region: 'center',
            tbar: tbar,
            id: 'events_grid',
            stateId: Zenoss.env.EVENTSGRID_STATEID,
            enableDragDrop: false,
            appendGlob: true,
            defaultFilters: {
                severity: [Zenoss.SEVERITY_CRITICAL, Zenoss.SEVERITY_ERROR, Zenoss.SEVERITY_WARNING, Zenoss.SEVERITY_INFO],
                eventState: [Zenoss.STATUS_CLOSED, Zenoss.STATUS_CLEARED, Zenoss.STATUS_AGED],
                // _managed_objects is a global function sent from the server, see ZenUI3/security/security.py
                tags: _managed_objects()
            },
            stateful: true,
            rowSelectorDepth: 5,
            store: archive_store,
            // Zenoss.env.COLUMN_DEFINITIONS comes from the server, and depends on
            // the resultFields associated with the context.
            columns: Zenoss.env.getColumnDefinitionsToRender(Zenoss.env.EVENTSGRID_STATEID),
            enableColumnHide: false,
            // Map some other keys
            keys: [{
                // Enter to pop open the detail panel
                key: Ext.EventObject.ENTER,
                fn: toggleEventDetailContent
            }],
            displayTotal: false,
            selModel: console_selection_model // defined above

        });
        console_selection_model.grid = grid;

        // Add it to the layout
        master_panel.add(grid);

        Zenoss.util.callWhenReady('events_grid', function(){
            Ext.getCmp('events_grid').setContext(Zenoss.env.PARENT_CONTEXT);
        });

        // Hook up the "Last Updated" text
        var store = grid.getStore();
        //store.on('beforeprefetch', doLastUpdated);
        if (store.buffered) {
            store.on('guaranteedrange', doLastUpdated);
        } else {
            store.on('load', doLastUpdated);
        }
        doLastUpdated();

        // Detail pane should pop open when double-click on event
        grid.on("itemdblclick", toggleEventDetailContent);

        grid.on('recreateGrid', function (grid) {
            var container_panel = Ext.getCmp('master_panel');
            container_panel.remove(grid.id, true);
            createEventHistoryGrid();
        });

        hideEventDetail();

        return grid;
    };

    /*
     * THE GRID ITSELF!
     */
    var grid = createEventHistoryGrid();

    /*
     * DETAIL PANEL STUFF
     */
    // Pop open the event detail, depending on the number of rows selected
    function toggleEventDetailContent(){
        var selections = console_selection_model.getSelection();
        if (selections.length) {
            showEventDetail(selections[0]);
        } else {
            wipeEventDetail();
        }
    }

    // Pop open the event detail pane and populate it with the appropriate data
    // and switch triggers (single select repopulates detail, esc to close)
    function showEventDetail(r) {
        Ext.getCmp('dpanelcontainer').load(r.data.evid);
        var grid = Ext.getCmp('events_grid');
        grid.un('itemdblclick', toggleEventDetailContent);
        detail_panel.expand();
        detail_panel.show();
        esckeymap.enable();
    }

    // Wipe event detail values
    function wipeEventDetail() {
        Ext.getCmp('dpanelcontainer').wipe();
    }

    // Collapse the event detail pane and switch triggers (double select
    // repopulates detail, esc no longer closes)
    function hideEventDetail() {
        detail_panel.collapse();
    }

    function eventDetailCollapsed(){
        wipeEventDetail();
        var grid = Ext.getCmp('events_grid');
        grid.on('itemdblclick', toggleEventDetailContent);
        esckeymap.disable();
    }

    // Finally, add the detail panel (have to do it after function defs to hook
    // up the hide callback)
    detail_panel.add({
        xtype:'detailpanel',
        id: 'dpanelcontainer',
        isHistory: true,
        onDetailHide: hideEventDetail
    });
    //  render the detail panel
    detail_panel.show();
    detail_panel.collapse();

    detail_panel.on('expand', function(ob, state) {
        toggleEventDetailContent();
    });

    detail_panel.on('collapse', function(ob, state) {
        eventDetailCollapsed();
    });

    console_selection_model.on("select", function(){
        if(detail_panel.collapsed === false){
            toggleEventDetailContent();
        }
        // if more than one is selected using the ctrl key, collapse the details:
        if(this.getCount() > 1) {
            detail_panel.collapse();
        }
    });
    // When multiple events are selected, detail pane should blank
    console_selection_model.on('rangeselect', function(){
        detail_panel.collapse();
    });

    // Key mapping for ESC to close detail pane
    var esckeymap = new Ext.KeyMap(document, {
        key: Ext.EventObject.ESC,
        fn: hideEventDetail
    });

    // Start disabled since pane is collapsed
    esckeymap.disable();

    // if there is a state apply it now
    if (window.location.search) {
        grid.restoreURLState();
    }
}); // stateProvider.onStateReady
});
